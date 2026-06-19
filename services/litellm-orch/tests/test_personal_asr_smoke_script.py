import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
import wave
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "services/litellm-orch/scripts/personal-asr-whisperkit-smoke.sh"


def _write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes((16).to_bytes(2, "little", signed=True) * 1600)


class TestPersonalAsrSmokeScript(unittest.TestCase):
    def _run_with_fake_curl(
        self,
        mode: str,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audio = tmp_path / "smoke.wav"
            _write_wav(audio)
            curl = tmp_path / "curl"
            curl.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    out=""
                    status="200"
                    auth_value=""
                    while [[ "$#" -gt 0 ]]; do
                      case "$1" in
                        -o) out="$2"; shift 2 ;;
                        -w) shift 2 ;;
                        --connect-timeout|--max-time) shift 2 ;;
                        -H)
                          [[ "$2" == Authorization:* ]] && auth_value="$2"
                          shift 2
                          ;;
                        -F)
                          case "$2" in
                            model=fast*|model=voice-stt*|model=large-v3*) status="401" ;;
                            prompt=*) status="400" ;;
                            file=@*silent*) status="400" ;;
                            file=@*malformed*) status="500" ;;
                          esac
                          shift 2
                          ;;
                        *) shift ;;
                      esac
                    done
                    if [[ "{mode}" == "curlfail" ]]; then
                      echo "connect failed" >&2
                      exit 7
                    fi
                    if [[ -z "$auth_value" ]]; then
                      status="401"
                    elif [[ "$auth_value" == *"invalid-personal-asr-smoke"* ]]; then
                      status="401"
                    fi
                    if [[ "$status" == "200" ]]; then
                      if [[ "{mode}" == "empty" ]]; then
                        printf '{{"text":""}}' >"$out"
                      else
                        printf '{{"text":"Argmax WhisperKit local transcription health check."}}' >"$out"
                      fi
                    else
                      printf '{{"error":"rejected"}}' >"$out"
                    fi
                    printf '%s' "$status"
                    """
                )
            )
            curl.chmod(curl.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{tmp}:{env['PATH']}",
                    "PERSONAL_ASR_LITELLM_KEY": "test-redacted-key",
                    "ASR_SMOKE_AUDIO": str(audio),
                }
            )
            if extra_env:
                env.update(extra_env)
            return subprocess.run(
                [str(SCRIPT)],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_smoke_script_accepts_bounded_expected_transcript(self):
        result = self._run_with_fake_curl("ok")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("happy-path: matched expected text", result.stdout)
        self.assertIn("missing-auth: rejected with HTTP 401", result.stdout)
        self.assertIn("invalid-auth: rejected with HTTP 401", result.stdout)
        self.assertIn("unauthorized-model:fast: rejected with HTTP 401", result.stdout)
        self.assertIn("unauthorized-model:voice-stt: rejected with HTTP 401", result.stdout)
        self.assertIn("unsupported-prompt: rejected with HTTP 400", result.stdout)
        self.assertIn("silent-input: rejected with HTTP 400", result.stdout)
        self.assertIn("malformed-audio: rejected with HTTP 500", result.stdout)
        self.assertIn("personal-asr-whisperkit smoke passed", result.stdout)
        self.assertNotIn("test-redacted-key", result.stdout)
        self.assertNotIn("test-redacted-key", result.stderr)

    def test_smoke_script_rejects_http_success_with_empty_transcript(self):
        result = self._run_with_fake_curl("empty")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("empty transcript text", result.stderr)
        self.assertNotIn("smoke passed", result.stdout)

    def test_smoke_script_rejects_blank_expected_text_before_request(self):
        result = self._run_with_fake_curl(
            "ok",
            {"ASR_SMOKE_EXPECTED_TEXT": "   "},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ASR_SMOKE_EXPECTED_TEXT must be non-empty", result.stderr)
        self.assertNotIn("smoke passed", result.stdout)

    def test_smoke_script_reports_curl_transport_failure(self):
        result = self._run_with_fake_curl("curlfail")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("happy-path: curl failed", result.stderr)
        self.assertIn("connect failed", result.stderr)
        self.assertNotIn("smoke passed", result.stdout)

    def test_smoke_script_uses_selected_model_in_success_label(self):
        result = self._run_with_fake_curl(
            "ok",
            {"ASR_SMOKE_MODEL": "personal-asr-riva"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("personal-asr-riva smoke passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
