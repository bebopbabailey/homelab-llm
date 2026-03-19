from __future__ import annotations

import json
import time
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response

from voice_gateway.backend import BackendRequestError, NativeSttBackend, SpeachesBackend
from voice_gateway.logging import emit_log
from voice_gateway.models import (
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    ModelItem,
    ModelsResponse,
    OpsModelRequest,
    OpsPreviewRequest,
    OpsPromotionPlanRequest,
    SpeechRequest,
    VoiceItem,
    VoicesResponse,
)
from voice_gateway.ops_registry import OpsRegistryError, load_curated_tts_registry
from voice_gateway.settings import Settings
from voice_gateway.voice_config import VoiceConfigError, load_voice_config, resolve_voice_selection


def _build_tts_backend(settings: Settings) -> SpeachesBackend:
    return SpeachesBackend(
        api_base=settings.backend_api_base,
        timeout_seconds=settings.backend_timeout_seconds,
        api_key=settings.backend_api_key,
        stt_model=settings.backend_stt_model,
        tts_model=settings.backend_tts_model,
    )


def _build_stt_backend(
    settings: Settings, tts_backend: SpeachesBackend
) -> SpeachesBackend | NativeSttBackend:
    if not settings.stt_backend_api_base:
        return tts_backend
    return NativeSttBackend(
        api_base=settings.stt_backend_api_base,
        timeout_seconds=settings.backend_timeout_seconds,
        model=settings.backend_stt_model,
    )


def _error_response(*, status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _require_client_auth(request: Request, settings: Settings) -> JSONResponse | None:
    if not settings.gateway_api_key:
        return None
    authorization = request.headers.get("authorization", "")
    expected = f"Bearer {settings.gateway_api_key}"
    if authorization == expected:
        return None
    return _error_response(status_code=401, code="invalid_api_key", message="missing or invalid bearer token")


def _extract_model_voices(*, models_payload: dict[str, object], model_id: str) -> list[dict[str, object]]:
    models = models_payload.get("data")
    if not isinstance(models, list):
        return []
    for item in models:
        if not isinstance(item, dict):
            continue
        if item.get("id") != model_id:
            continue
        voices = item.get("voices")
        if isinstance(voices, list):
            return [voice for voice in voices if isinstance(voice, dict)]
        return []
    return []


def _build_promotion_plan(body: OpsPromotionPlanRequest) -> str:
    normalized_voice_ids = [voice_id.strip() for voice_id in body.voice_ids if voice_id.strip()]
    if body.include_default_alloy_aliases and normalized_voice_ids:
        alias_entries: list[dict[str, object]] = [
            {"id": "default", "backend_voice": normalized_voice_ids[0], "active": True},
            {"id": "alloy", "backend_voice": normalized_voice_ids[0], "active": True},
        ]
    else:
        alias_entries = []
    alias_entries.extend(
        {"id": voice_id, "backend_voice": voice_id, "active": True} for voice_id in normalized_voice_ids
    )
    voices_json = {
        "default_voice_policy": "configured_default",
        "unknown_voice_policy": body.unknown_voice_policy,
        "fallback_voice_id": body.fallback_voice_id,
        "voices": alias_entries,
    }
    encoded_json = json.dumps(voices_json, indent=2)
    return "\n".join(
        [
            "# 1) set backend TTS model",
            (
                "sudo python3 - <<'PY'\n"
                "from pathlib import Path\n"
                "path = Path('/etc/voice-gateway/voice-gateway.env')\n"
                "lines = path.read_text().splitlines()\n"
                "out = []\n"
                "updated = False\n"
                "for line in lines:\n"
                "    if line.startswith('VOICE_BACKEND_TTS_MODEL='):\n"
                f"        out.append('VOICE_BACKEND_TTS_MODEL={body.backend_tts_model}')\n"
                "        updated = True\n"
                "    else:\n"
                "        out.append(line)\n"
                "if not updated:\n"
                f"    out.append('VOICE_BACKEND_TTS_MODEL={body.backend_tts_model}')\n"
                "path.write_text('\\n'.join(out) + '\\n')\n"
                "print('updated', path)\n"
                "PY"
            ),
            "",
            "# 2) write voice alias config",
            (
                "sudo python3 - <<'PY'\n"
                "from pathlib import Path\n"
                "path = Path('/etc/voice-gateway/voices.json')\n"
                f"path.write_text('''{encoded_json}\\n''')\n"
                "print('updated', path)\n"
                "PY"
            ),
            "",
            "# 3) restart gateway and verify",
            "sudo systemctl restart voice-gateway.service",
            "sudo systemctl is-active voice-gateway.service",
            "",
            "# 4) optional: check readiness and speakers",
            "# export VOICE_GATEWAY_API_KEY=...",
            "# curl -fsS http://192.168.1.93:18080/health/readiness | jq .",
            "# curl -fsS http://192.168.1.93:18080/v1/speakers -H \"Authorization: Bearer ${VOICE_GATEWAY_API_KEY}\" | jq .",
        ]
    )


def _load_curated_payload(settings: Settings) -> dict[str, object]:
    models = load_curated_tts_registry(settings.tts_registry_path)
    return {
        "path": str(settings.tts_registry_path),
        "count": len(models),
        "models": [item.to_dict() for item in models],
    }


def _load_deploy_manifest(settings: Settings) -> dict[str, object] | None:
    path = settings.deploy_manifest_path
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    return raw


OPS_HTML = """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Voice Gateway Ops</title>
<style>
body{font-family:ui-sans-serif,system-ui,sans-serif;margin:1.5rem;background:#f5f7fb;color:#0f172a}h1,h2{margin:.3rem 0}.card{background:#fff;border:1px solid #dbe2ea;border-radius:10px;padding:1rem;margin-bottom:1rem}label{display:block;font-weight:600;margin:.4rem 0 .2rem}input,select,textarea,button{font:inherit;padding:.45rem .6rem;border:1px solid #c8d2dd;border-radius:8px}textarea{width:100%;min-height:130px}button{cursor:pointer;background:#1d4ed8;color:white;border:0}button.secondary{background:#334155}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.8rem}.muted{color:#475569;font-size:.92rem}.row{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center}ul{margin:.2rem 0 0 1rem;padding:0}code{background:#eef2f7;padding:.1rem .3rem;border-radius:4px}
</style></head><body>
<h1>Voice Gateway Ops (MVP)</h1><p class=\"muted\">Model discovery, lifecycle, and TTS audition. Promotion stays manual via generated sudo commands.</p>
<div class=\"card\"><div class=\"grid\"><div><label>Gateway API Key</label><input id=\"apiKey\" placeholder=\"Bearer token\"></div><div><label>Gateway Base URL</label><input id=\"baseUrl\" value=\"\"></div></div><div class=\"row\" style=\"margin-top:.6rem\"><button onclick=\"refreshAll()\">Refresh</button><span id=\"status\" class=\"muted\"></span></div></div>
<div class=\"card\"><h2>State</h2><pre id=\"state\" class=\"muted\"></pre></div>
<div class=\"card\"><h2>Models</h2><div class=\"grid\"><div><label>Curated Registry (repo-canonical)</label><select id=\"curatedModels\" size=\"8\" style=\"width:100%\"></select></div><div><label>Installed Local TTS Models</label><select id=\"localModels\" size=\"8\" style=\"width:100%\"></select></div><div><label>Loaded Models</label><ul id=\"loadedModels\"></ul></div></div><div class=\"row\" style=\"margin-top:.7rem\"><button onclick=\"useCuratedForPreview()\">Use curated model for preview</button><button onclick=\"downloadCurated()\">Download curated</button><button class=\"secondary\" onclick=\"loadCurated()\">Load curated</button><button class=\"secondary\" onclick=\"unloadCurated()\">Unload curated</button><button class=\"secondary\" onclick=\"downloadSelectedLocal()\">Download selected local</button><button class=\"secondary\" onclick=\"loadSelectedLocal()\">Load selected local</button><button class=\"secondary\" onclick=\"unloadSelectedLocal()\">Unload selected local</button></div></div>
<div class=\"card\"><h2>TTS Audition</h2><div class=\"grid\"><div><label>Model</label><input id=\"previewModel\" placeholder=\"speaches-ai/Kokoro-82M-v1.0-ONNX\"></div><div><label>Voice</label><select id=\"previewVoice\"></select></div><div><label>Speed</label><input id=\"previewSpeed\" type=\"number\" value=\"1.0\" step=\"0.05\"></div><div><label>Format</label><select id=\"previewFormat\"><option>wav</option><option>mp3</option></select></div></div><label>Text</label><textarea id=\"previewText\">Is that a Chevy '69? How bizarre... How bizarre, how bizarre.</textarea><div class=\"row\"><button onclick=\"refreshVoices()\">Refresh voices</button><button onclick=\"runPreview()\">Generate preview</button></div><audio id=\"previewAudio\" controls style=\"margin-top:.8rem;width:100%\"></audio></div>
<div class=\"card\"><h2>Manual Promotion Plan</h2><p class=\"muted\">Generates copy/paste commands only. No root writes from dashboard.</p><div class=\"grid\"><div><label>Backend TTS model</label><input id=\"planModel\"></div><div><label>Fallback voice alias</label><input id=\"planFallback\" value=\"default\"></div><div><label>Unknown voice policy</label><select id=\"planPolicy\"><option value=\"reject\">reject</option><option value=\"fallback\">fallback</option></select></div></div><label>Voice IDs (comma-separated)</label><input id=\"planVoiceIds\" placeholder=\"af_heart,af_nova,am_echo\"><div class=\"row\"><button onclick=\"buildPlan()\">Generate commands</button></div><textarea id=\"planOutput\" readonly></textarea></div>
<script>
const stateEl=document.getElementById('state');const statusEl=document.getElementById('status');
document.getElementById('baseUrl').value=window.location.origin;
const headers=()=>{const k=document.getElementById('apiKey').value.trim();return k?{'Authorization':'Bearer '+k}:{};};
const getBase=()=>{const raw=document.getElementById('baseUrl').value.trim();return raw.endsWith('/')?raw.slice(0,-1):raw;};
async function jget(path){const r=await fetch(getBase()+path,{headers:headers()});if(!r.ok)throw new Error(await r.text());return r.json();}
async function jpost(path,body){const r=await fetch(getBase()+path,{method:'POST',headers:{...headers(),'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw new Error(await r.text());return r;}
function setStatus(msg){statusEl.textContent=msg;}
function selectedModel(){const s=document.getElementById('localModels');return s.value;}
function selectedCuratedModel(){const s=document.getElementById('curatedModels');return s.value;}
async function refreshAll(){try{setStatus('loading...');const [state,curated,local,loaded]=await Promise.all([jget('/ops/api/state'),jget('/ops/api/registry/curated'),jget('/ops/api/models/local?task=text-to-speech'),jget('/ops/api/models/loaded')]);stateEl.textContent=JSON.stringify(state,null,2);const curatedSel=document.getElementById('curatedModels');curatedSel.innerHTML='';for(const m of (curated.models||[])){const o=document.createElement('option');o.value=m.model_id;o.textContent=(m.recommended?'* ':'')+m.id+' -> '+m.model_id;curatedSel.appendChild(o);}const localSel=document.getElementById('localModels');localSel.innerHTML='';for(const m of (local.data||[])){const o=document.createElement('option');o.value=m.id;o.textContent=m.id;localSel.appendChild(o);}if(curatedSel.options.length){curatedSel.selectedIndex=0;document.getElementById('previewModel').value=curatedSel.value;document.getElementById('planModel').value=curatedSel.value;}else if(localSel.options.length){localSel.selectedIndex=0;document.getElementById('previewModel').value=localSel.value;document.getElementById('planModel').value=localSel.value;}const ul=document.getElementById('loadedModels');ul.innerHTML='';for(const m of (loaded.models||[])){const li=document.createElement('li');li.textContent=m;ul.appendChild(li);}await refreshVoices();setStatus('ready');}catch(e){setStatus('error: '+e.message);}}
async function refreshVoices(){const model=document.getElementById('previewModel').value.trim()||selectedModel();if(!model)return;const data=await jget('/ops/api/model-voices?model_id='+encodeURIComponent(model));const voiceSel=document.getElementById('previewVoice');voiceSel.innerHTML='';for(const v of (data.voices||[])){const id=v.id||v.name;const o=document.createElement('option');o.value=id;o.textContent=id;voiceSel.appendChild(o);}if(!voiceSel.options.length){const o=document.createElement('option');o.value='default';o.textContent='default';voiceSel.appendChild(o);}}
async function useCuratedForPreview(){const model=selectedCuratedModel();if(!model)return;document.getElementById('previewModel').value=model;document.getElementById('planModel').value=model;await refreshVoices();}
async function downloadCurated(){const model=selectedCuratedModel();if(!model)return;await jpost('/ops/api/models/download',{model_id:model});await refreshAll();}
async function loadCurated(){const model=selectedCuratedModel();if(!model)return;await jpost('/ops/api/models/load',{model_id:model});await refreshAll();}
async function unloadCurated(){const model=selectedCuratedModel();if(!model)return;await jpost('/ops/api/models/unload',{model_id:model});await refreshAll();}
async function downloadSelectedLocal(){const model=selectedModel();if(!model)return;await jpost('/ops/api/models/download',{model_id:model});await refreshAll();}
async function loadSelectedLocal(){const model=selectedModel();if(!model)return;await jpost('/ops/api/models/load',{model_id:model});await refreshAll();}
async function unloadSelectedLocal(){const model=selectedModel();if(!model)return;await jpost('/ops/api/models/unload',{model_id:model});await refreshAll();}
async function runPreview(){const r=await jpost('/ops/api/preview',{model:document.getElementById('previewModel').value.trim(),voice:document.getElementById('previewVoice').value,input:document.getElementById('previewText').value,response_format:document.getElementById('previewFormat').value,speed:parseFloat(document.getElementById('previewSpeed').value||'1')});const b=await r.blob();const url=URL.createObjectURL(b);const audio=document.getElementById('previewAudio');audio.src=url;audio.play();}
async function buildPlan(){const voiceIds=document.getElementById('planVoiceIds').value.split(',').map(v=>v.trim()).filter(Boolean);const r=await (await jpost('/ops/api/promotion/plan',{backend_tts_model:document.getElementById('planModel').value.trim(),fallback_voice_id:document.getElementById('planFallback').value.trim()||'default',unknown_voice_policy:document.getElementById('planPolicy').value,include_default_alloy_aliases:true,voice_ids:voiceIds})).json();document.getElementById('planOutput').value=r.commands;}
refreshAll();
</script></body></html>"""


def create_app(
    *,
    settings: Settings | None = None,
    backend: SpeachesBackend | None = None,
    tts_backend: SpeachesBackend | None = None,
    stt_backend: SpeachesBackend | NativeSttBackend | None = None,
) -> FastAPI:
    active_settings = settings or Settings()
    active_tts_backend = tts_backend or backend or _build_tts_backend(active_settings)
    active_stt_backend = stt_backend or backend or _build_stt_backend(active_settings, active_tts_backend)
    app = FastAPI(title="Voice Gateway", version="0.2.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/health/readiness")
    def readiness() -> JSONResponse:
        request_id = str(uuid4())
        total_start = time.perf_counter()
        try:
            tts_backend_health = active_tts_backend.health()
            if active_stt_backend is active_tts_backend:
                stt_backend_health = tts_backend_health
            else:
                stt_backend_health = active_stt_backend.health()
            config = load_voice_config(active_settings.voice_config_path)
            payload = {
                "status": "ready",
                "tts_backend_status": tts_backend_health.status,
                "stt_backend_status": stt_backend_health.status,
                "tts_backend_api_base": active_settings.backend_api_base,
                "stt_backend_api_base": active_settings.stt_backend_api_base or active_settings.backend_api_base,
                "public_stt_model": active_settings.public_stt_model,
                "public_tts_model": active_settings.public_tts_model,
                "backend_stt_model": active_settings.backend_stt_model,
                "backend_tts_model": active_settings.backend_tts_model,
                "default_voice": config.fallback_voice_id,
                "unknown_voice_policy": config.unknown_voice_policy,
            }
            emit_log(
                event="readiness",
                log_path=active_settings.log_path,
                request_id=request_id,
                route="/health/readiness",
                source="http",
                tts_backend_status=tts_backend_health.status,
                stt_backend_status=stt_backend_health.status,
                tts_backend_api_base=active_settings.backend_api_base,
                stt_backend_api_base=active_settings.stt_backend_api_base or active_settings.backend_api_base,
                tts_backend_upstream_ms=tts_backend_health.upstream_ms,
                stt_backend_upstream_ms=stt_backend_health.upstream_ms,
                total_ms=round((time.perf_counter() - total_start) * 1000, 3),
                status="ready",
                error_code=None,
                exception_class=None,
            )
            return JSONResponse(payload)
        except (BackendRequestError, VoiceConfigError) as exc:
            emit_log(
                event="readiness",
                log_path=active_settings.log_path,
                request_id=request_id,
                route="/health/readiness",
                source="http",
                total_ms=round((time.perf_counter() - total_start) * 1000, 3),
                status="blocked",
                error_code=getattr(exc, "code", "readiness_blocked"),
                exception_class=exc.__class__.__name__,
            )
            return _error_response(
                status_code=getattr(exc, "status_code", 503),
                code=getattr(exc, "code", "readiness_blocked"),
                message=str(exc),
            )

    @app.get("/ops", response_class=HTMLResponse)
    def ops_page() -> HTMLResponse:
        return HTMLResponse(content=OPS_HTML)

    @app.get("/ops/api/state", responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def ops_state(request: Request) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            config = load_voice_config(active_settings.voice_config_path)
            curated_payload = _load_curated_payload(active_settings)
            loaded_payload, loaded_ms = active_tts_backend.list_loaded_models()
            return JSONResponse(
                {
                    "gateway": {
                        "public_tts_model": active_settings.public_tts_model,
                        "backend_tts_model": active_settings.backend_tts_model,
                        "backend_api_base": active_settings.backend_api_base,
                    },
                    "voice_config": {
                        "fallback_voice_id": config.fallback_voice_id,
                        "unknown_voice_policy": config.unknown_voice_policy,
                        "voice_count": len(config.voices),
                    },
                    "curated_registry": {
                        "path": curated_payload["path"],
                        "count": curated_payload["count"],
                    },
                    "deploy_manifest": _load_deploy_manifest(active_settings),
                    "speaches_loaded": loaded_payload,
                    "speaches_loaded_upstream_ms": loaded_ms,
                }
            )
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)
        except VoiceConfigError as exc:
            return _error_response(status_code=400, code="registry_invalid", message=str(exc))
        except OpsRegistryError as exc:
            return _error_response(status_code=500, code="curated_registry_invalid", message=str(exc))

    @app.get("/ops/api/registry/curated", responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
    def ops_curated_registry(request: Request) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            return JSONResponse(_load_curated_payload(active_settings))
        except OpsRegistryError as exc:
            return _error_response(status_code=500, code="curated_registry_invalid", message=str(exc))

    @app.get("/ops/api/models/local", responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def ops_local_models(request: Request, task: str | None = None) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            payload, upstream_ms = active_tts_backend.list_local_models(task=task)
            payload["upstream_ms"] = upstream_ms
            return JSONResponse(payload)
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    @app.get("/ops/api/models/registry", responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def ops_registry_models(request: Request, task: str | None = None) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            payload, upstream_ms = active_tts_backend.list_registry_models(task=task)
            payload["upstream_ms"] = upstream_ms
            return JSONResponse(payload)
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    @app.get("/ops/api/models/loaded", responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def ops_loaded_models(request: Request) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            payload, upstream_ms = active_tts_backend.list_loaded_models()
            payload["upstream_ms"] = upstream_ms
            return JSONResponse(payload)
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    @app.get("/ops/api/model-voices", responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def ops_model_voices(request: Request, model_id: str) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            local_payload, local_upstream_ms = active_tts_backend.list_local_models(task="text-to-speech")
            voices = _extract_model_voices(models_payload=local_payload, model_id=model_id)
            source = "local"
            registry_upstream_ms: float | None = None
            if not voices:
                registry_payload, registry_upstream_ms = active_tts_backend.list_registry_models(task="text-to-speech")
                voices = _extract_model_voices(models_payload=registry_payload, model_id=model_id)
                source = "registry"
            return JSONResponse(
                {
                    "model_id": model_id,
                    "source": source,
                    "voices": voices,
                    "local_upstream_ms": local_upstream_ms,
                    "registry_upstream_ms": registry_upstream_ms,
                }
            )
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    @app.post("/ops/api/models/download", responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def ops_download_model(request: Request, body: OpsModelRequest) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            payload, upstream_ms = active_tts_backend.download_model(model_id=body.model_id)
            payload["upstream_ms"] = upstream_ms
            return JSONResponse(payload)
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    @app.post("/ops/api/models/load", responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def ops_load_model(request: Request, body: OpsModelRequest) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            payload, upstream_ms = active_tts_backend.load_model(model_id=body.model_id)
            payload["upstream_ms"] = upstream_ms
            return JSONResponse(payload)
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    @app.post("/ops/api/models/unload", responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def ops_unload_model(request: Request, body: OpsModelRequest) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            payload, upstream_ms = active_tts_backend.unload_model(model_id=body.model_id)
            payload["upstream_ms"] = upstream_ms
            return JSONResponse(payload)
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    @app.post("/ops/api/preview", response_model=None, responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    def ops_preview(request: Request, body: OpsPreviewRequest) -> Response | JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        if body.response_format not in {"mp3", "wav"}:
            return _error_response(
                status_code=400,
                code="invalid_response_format",
                message="response_format must be mp3 or wav",
            )
        try:
            result = active_tts_backend.synthesize_with_model(
                model_id=body.model,
                text=body.input,
                backend_voice=body.voice,
                response_format=body.response_format,
                speed=body.speed,
            )
            return Response(content=result.content, media_type=result.media_type)
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    @app.post("/ops/api/promotion/plan", responses={401: {"model": ErrorResponse}})
    def ops_promotion_plan(request: Request, body: OpsPromotionPlanRequest) -> JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        if body.unknown_voice_policy not in {"reject", "fallback"}:
            return _error_response(
                status_code=400,
                code="invalid_unknown_voice_policy",
                message="unknown_voice_policy must be reject or fallback",
            )
        return JSONResponse({"commands": _build_promotion_plan(body)})

    @app.get("/v1/models", response_model=ModelsResponse, responses={401: {"model": ErrorResponse}})
    def list_models(request: Request) -> ModelsResponse | JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        return ModelsResponse(
            data=[
                ModelItem(id=active_settings.public_stt_model),
                ModelItem(id=active_settings.public_tts_model),
            ]
        )

    @app.get("/v1/speakers", response_model=VoicesResponse, responses={401: {"model": ErrorResponse}})
    def list_speakers(request: Request) -> VoicesResponse | JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        try:
            config = load_voice_config(active_settings.voice_config_path)
            return VoicesResponse(
                default_voice=config.fallback_voice_id,
                unknown_voice_policy=config.unknown_voice_policy,
                fallback_voice_id=config.fallback_voice_id,
                voices=[
                    VoiceItem(id=alias.voice_id, backend_voice=alias.backend_voice, active=alias.active)
                    for alias in config.voices
                ],
            )
        except VoiceConfigError as exc:
            return _error_response(status_code=400, code="registry_invalid", message=str(exc))

    @app.post(
        "/v1/audio/speech",
        response_model=None,
        responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    def speech(request: Request, body: SpeechRequest) -> Response | JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        request_id = str(uuid4())
        total_start = time.perf_counter()
        if body.model != active_settings.public_tts_model:
            return _error_response(
                status_code=400,
                code="unsupported_model",
                message=f"model must be {active_settings.public_tts_model}",
            )
        if body.response_format not in {"mp3", "wav"}:
            return _error_response(
                status_code=400,
                code="invalid_response_format",
                message="response_format must be mp3 or wav",
            )
        try:
            config = load_voice_config(active_settings.voice_config_path)
            resolution = resolve_voice_selection(requested_voice=body.voice, config=config)
            if resolution.warning:
                emit_log(
                    event="voice_warning",
                    log_path=active_settings.log_path,
                    request_id=request_id,
                    route="/v1/audio/speech",
                    source="http",
                    requested_voice=body.voice,
                    resolved_voice=resolution.resolved_voice,
                    backend_voice=resolution.backend_voice,
                    warning=resolution.warning,
                    status="warn",
                )
            result = active_tts_backend.synthesize(
                text=body.input,
                backend_voice=resolution.backend_voice,
                response_format=body.response_format,
                speed=body.speed,
            )
            total_ms = round((time.perf_counter() - total_start) * 1000, 3)
            emit_log(
                event="speech",
                log_path=active_settings.log_path,
                request_id=request_id,
                route="/v1/audio/speech",
                source="http",
                model=body.model,
                backend_model=result.backend_model,
                voice=body.voice,
                resolved_voice=resolution.resolved_voice,
                backend_voice=result.backend_voice,
                response_format=body.response_format,
                input_chars=len(body.input),
                output_bytes=result.output_bytes,
                backend_upstream_ms=result.upstream_ms,
                total_ms=total_ms,
                status="ok",
                error_code=None,
                exception_class=None,
            )
            return Response(content=result.content, media_type=result.media_type)
        except VoiceConfigError as exc:
            emit_log(
                event="voice_warning",
                log_path=active_settings.log_path,
                request_id=request_id,
                route="/v1/audio/speech",
                source="http",
                requested_voice=body.voice,
                warning=str(exc),
                status="warn",
            )
            return _error_response(status_code=400, code="speaker_not_found", message=str(exc))
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    @app.post(
        "/v1/audio/transcriptions",
        response_model=None,
        responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def transcriptions(
        request: Request,
        file: UploadFile = File(...),
        model: str = Form(...),
        language: str | None = Form(default=None),
        prompt: str | None = Form(default=None),
        response_format: str | None = Form(default=None),
        temperature: float | None = Form(default=None),
        timestamp_granularities: list[str] | None = Form(default=None),
    ) -> Response | JSONResponse:
        auth_error = _require_client_auth(request, active_settings)
        if auth_error is not None:
            return auth_error
        if model != active_settings.public_stt_model:
            return _error_response(
                status_code=400,
                code="unsupported_model",
                message=f"model must be {active_settings.public_stt_model}",
            )
        request_id = str(uuid4())
        total_start = time.perf_counter()
        file_bytes = await file.read()
        if active_settings.stt_backend_api_base and response_format not in {None, "json", "text", "verbose_json"}:
            return _error_response(
                status_code=400,
                code="unsupported_response_format",
                message="response_format must be json, verbose_json, or text for native STT backend",
            )
        try:
            result = active_stt_backend.transcribe(
                file_name=file.filename or "audio.wav",
                file_bytes=file_bytes,
                content_type=file.content_type,
                language=language,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature,
                timestamp_granularities=timestamp_granularities,
            )
            emit_log(
                event="transcription",
                log_path=active_settings.log_path,
                request_id=request_id,
                route="/v1/audio/transcriptions",
                source="http",
                model=model,
                backend_model=result.backend_model,
                input_bytes=len(file_bytes),
                response_format=response_format or "json",
                backend_upstream_ms=result.upstream_ms,
                total_ms=round((time.perf_counter() - total_start) * 1000, 3),
                output_bytes=result.output_bytes,
                timestamp_granularities=timestamp_granularities or [],
                status="ok",
                error_code=None,
                exception_class=None,
            )
            return Response(content=result.content, media_type=result.media_type)
        except BackendRequestError as exc:
            return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)

    return app
