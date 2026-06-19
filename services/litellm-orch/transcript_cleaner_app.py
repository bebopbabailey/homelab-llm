from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse


DEFAULT_CHUNK_CHARS = 12_000
DEFAULT_MAX_OUTPUT_TOKENS = 8_192
DEFAULT_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
JOB_ID_RE = re.compile(r"^[a-f0-9]{32}$")


@dataclass(frozen=True)
class CleanerConfig:
    job_dir: Path
    litellm_base_url: str
    api_key: str
    chunk_chars: int = DEFAULT_CHUNK_CHARS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES

    @classmethod
    def from_env(cls) -> "CleanerConfig":
        api_key = os.environ.get("LITELLM_MASTER_KEY") or os.environ.get("LITELLM_API_KEY") or ""
        if not api_key:
            raise RuntimeError("LITELLM_MASTER_KEY or LITELLM_API_KEY is required")
        return cls(
            job_dir=Path(os.environ.get("TRANSCRIPT_CLEAN_JOB_DIR", "/tmp/transcript-cleaner")),
            litellm_base_url=os.environ.get("TRANSCRIPT_CLEAN_LITELLM_BASE_URL", "http://127.0.0.1:4000/v1").rstrip("/"),
            api_key=api_key,
            chunk_chars=_env_int("TRANSCRIPT_CLEAN_CHUNK_CHARS", DEFAULT_CHUNK_CHARS),
            max_output_tokens=_env_int("TRANSCRIPT_CLEAN_MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS),
            max_upload_bytes=_env_int("TRANSCRIPT_CLEAN_MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES),
        )


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


def chunk_text(text: str, chunk_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be greater than zero")
    return [text[index : index + chunk_chars] for index in range(0, len(text), chunk_chars)]


def extract_response_text(payload: dict[str, Any]) -> str:
    direct = _flatten_text(payload.get("output_text"))
    if direct.strip():
        return direct.strip()
    output = _flatten_text(payload.get("output"))
    if output.strip():
        return output.strip()
    return ""


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        if isinstance(value.get("value"), str):
            return value["value"]
        if "content" in value:
            return _flatten_text(value["content"])
        if "output" in value:
            return _flatten_text(value["output"])
    return ""


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_job_path(config: CleanerConfig, job_id: str) -> Path:
    if not JOB_ID_RE.fullmatch(job_id):
        raise HTTPException(status_code=404, detail="job not found")
    path = config.job_dir / job_id
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="job not found")
    return path


def _status_path(job_path: Path) -> Path:
    return job_path / "status.json"


def _public_status(status: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": status["job_id"],
        "state": status["state"],
        "filename": status.get("filename") or "transcript.txt",
        "total_chunks": status.get("total_chunks", 0),
        "processed_chunks": status.get("processed_chunks", 0),
        "error": status.get("error"),
    }


async def call_task_transcribe(config: CleanerConfig, text: str) -> str:
    payload = {
        "model": "task-transcribe",
        "input": [{"role": "user", "content": text}],
        "max_output_tokens": config.max_output_tokens,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(f"{config.litellm_base_url}/responses", headers=headers, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"LiteLLM returned HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    text_out = extract_response_text(data)
    if not text_out:
        raise RuntimeError("LiteLLM response did not contain output text")
    return text_out


async def run_job(job_id: str) -> None:
    config = get_config()
    job_path = config.job_dir / job_id
    status_path = _status_path(job_path)
    try:
        input_text = (job_path / "input.txt").read_text(encoding="utf-8")
        chunks = chunk_text(input_text, config.chunk_chars)
        chunks_dir = job_path / "chunks"
        cleaned_dir = job_path / "cleaned_chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        cleaned_dir.mkdir(parents=True, exist_ok=True)

        status = _read_json(status_path)
        status.update({"state": "running", "total_chunks": len(chunks), "processed_chunks": 0, "error": None})
        _write_json(status_path, status)

        for index, chunk in enumerate(chunks, start=1):
            chunk_path = chunks_dir / f"{index:04d}.txt"
            cleaned_path = cleaned_dir / f"{index:04d}.txt"
            if not chunk_path.exists():
                chunk_path.write_text(chunk, encoding="utf-8")
            if not cleaned_path.exists():
                cleaned = await call_task_transcribe(config, chunk)
                cleaned_path.write_text(cleaned, encoding="utf-8")
            status = _read_json(status_path)
            status["processed_chunks"] = index
            _write_json(status_path, status)

        output = "\n\n".join(path.read_text(encoding="utf-8").strip() for path in sorted(cleaned_dir.glob("*.txt")))
        (job_path / "output.txt").write_text(output + "\n", encoding="utf-8")
        status = _read_json(status_path)
        status.update({"state": "done", "processed_chunks": len(chunks), "error": None})
        _write_json(status_path, status)
    except Exception as exc:
        status = _read_json(status_path) if status_path.exists() else {"job_id": job_id}
        status.update({"state": "error", "error": str(exc)})
        _write_json(status_path, status)


_config: CleanerConfig | None = None


def get_config() -> CleanerConfig:
    global _config
    if _config is None:
        _config = CleanerConfig.from_env()
    return _config


def set_config_for_tests(config: CleanerConfig | None) -> None:
    global _config
    _config = config


app = FastAPI(title="Transcript Cleaner", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    get_config()
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.post("/jobs")
async def create_job(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    config = get_config()
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="expected JSON body") from exc
    text = str(payload.get("text") or "")
    filename = str(payload.get("filename") or "transcript.txt")
    if not text.strip():
        raise HTTPException(status_code=400, detail="transcript text is required")
    if len(text.encode("utf-8")) > config.max_upload_bytes:
        raise HTTPException(status_code=413, detail="transcript is too large")
    if filename and not filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="only .txt uploads are accepted")

    job_id = uuid.uuid4().hex
    job_path = config.job_dir / job_id
    job_path.mkdir(parents=True, exist_ok=False)
    (job_path / "input.txt").write_text(text, encoding="utf-8")
    status = {
        "job_id": job_id,
        "state": "pending",
        "filename": filename,
        "total_chunks": 0,
        "processed_chunks": 0,
        "error": None,
        "created_at": int(time.time()),
    }
    _write_json(_status_path(job_path), status)
    background_tasks.add_task(run_job, job_id)
    return JSONResponse(_public_status(status), status_code=202)


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    config = get_config()
    job_path = _safe_job_path(config, job_id)
    return _public_status(_read_json(_status_path(job_path)))


@app.get("/jobs/{job_id}/output")
async def get_output(job_id: str) -> FileResponse:
    config = get_config()
    job_path = _safe_job_path(config, job_id)
    status = _read_json(_status_path(job_path))
    if status.get("state") != "done":
        raise HTTPException(status_code=409, detail="job is not done")
    filename = str(status.get("filename") or "transcript.txt")
    stem = filename[:-4] if filename.lower().endswith(".txt") else filename
    return FileResponse(
        job_path / "output.txt",
        media_type="text/plain; charset=utf-8",
        filename=f"{stem}.cleaned.txt",
    )


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transcript Cleaner</title>
  <style>
    :root { color-scheme: light dark; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: Canvas; color: CanvasText; }
    main { max-width: 880px; margin: 0 auto; padding: 24px 16px 40px; }
    h1 { font-size: 28px; margin: 0 0 18px; letter-spacing: 0; }
    textarea { box-sizing: border-box; width: 100%; min-height: 48vh; padding: 14px; border: 1px solid color-mix(in srgb, CanvasText 25%, transparent); border-radius: 6px; font: 16px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }
    .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 14px 0; }
    input[type="file"] { max-width: 100%; }
    button, a.button { appearance: none; border: 0; border-radius: 6px; background: #0f766e; color: white; padding: 10px 14px; font: 600 16px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-decoration: none; }
    button:disabled { opacity: 0.55; }
    progress { width: 100%; height: 18px; }
    .status { min-height: 24px; font-size: 15px; }
  </style>
</head>
<body>
  <main>
    <h1>Transcript Cleaner</h1>
    <div class="row">
      <input id="file" type="file" accept=".txt,text/plain">
      <button id="clean">Clean</button>
      <a id="download" class="button" hidden>Download</a>
    </div>
    <textarea id="text" placeholder="Paste transcript text here"></textarea>
    <div class="row">
      <progress id="progress" value="0" max="1"></progress>
    </div>
    <div id="status" class="status"></div>
  </main>
  <script>
    const fileEl = document.getElementById("file");
    const textEl = document.getElementById("text");
    const cleanEl = document.getElementById("clean");
    const downloadEl = document.getElementById("download");
    const progressEl = document.getElementById("progress");
    const statusEl = document.getElementById("status");
    let filename = "transcript.txt";

    fileEl.addEventListener("change", async () => {
      const file = fileEl.files[0];
      if (!file) return;
      filename = file.name || "transcript.txt";
      textEl.value = await file.text();
    });

    cleanEl.addEventListener("click", async () => {
      cleanEl.disabled = true;
      downloadEl.hidden = true;
      statusEl.textContent = "Starting...";
      progressEl.value = 0;
      try {
        const response = await fetch("/jobs", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({text: textEl.value, filename})
        });
        if (!response.ok) throw new Error(await response.text());
        const job = await response.json();
        poll(job.job_id);
      } catch (error) {
        cleanEl.disabled = false;
        statusEl.textContent = String(error);
      }
    });

    async function poll(jobId) {
      const response = await fetch(`/jobs/${jobId}`);
      const job = await response.json();
      const total = Math.max(job.total_chunks || 1, 1);
      progressEl.max = total;
      progressEl.value = job.processed_chunks || 0;
      statusEl.textContent = `${job.state}: ${job.processed_chunks || 0}/${job.total_chunks || 0}`;
      if (job.state === "done") {
        cleanEl.disabled = false;
        downloadEl.href = `/jobs/${jobId}/output`;
        downloadEl.hidden = false;
        statusEl.textContent = "Done.";
        return;
      }
      if (job.state === "error") {
        cleanEl.disabled = false;
        statusEl.textContent = `Error: ${job.error || "unknown error"}`;
        return;
      }
      setTimeout(() => poll(jobId), 1000);
    }
  </script>
</body>
</html>
"""
