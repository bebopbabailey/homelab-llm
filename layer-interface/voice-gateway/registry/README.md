# Voice Gateway TTS Registry

Purpose:
- keep a curated, repo-canonical shortlist of TTS models for the speech stack
- separate stable operator intent from remote backend discovery noise

File:
- `tts_models.jsonl`

Format:
- one JSON object per line
- required keys:
  - `id` (stable repo handle)
  - `model_id` (exact Speaches backend model id)
  - `family` (`kokoro` or `piper` for current shortlist)
  - `status` (`candidate`, `approved`, `deployed`, `rejected`)
- optional keys:
  - `language_tags`
  - `quality_tier`
  - `recommended`
  - `voice_mode`
  - `notes`

Policy:
- this curated registry is canonical for control-plane operations
- Speaches `/v1/registry` remains a discovery source, not a source of truth
- promotion to live runtime remains explicit through manual apply commands
