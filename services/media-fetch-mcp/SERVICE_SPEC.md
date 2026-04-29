# Service Spec: media-fetch-mcp

## Purpose
Localhost-only MCP backend on the Mini for retrieval-style media tools. The
first tool is `youtube.transcript`, which fetches the full caption transcript
for a supported single-video YouTube URL and returns it as one flat
timestamped text field plus minimal metadata.

## Host & Runtime
- **Host**: Mini
- **Runtime**: Python under systemd
- **Bind**: `127.0.0.1:8012`
- **MCP endpoint**: `http://127.0.0.1:8012/mcp`
- **Transport**: MCP Streamable HTTP

## Tool Surface
- `youtube.transcript`

## `youtube.transcript` contract
- Input:
  - `url`
- Output:
  - `video_id`
  - `transcript_text`
  - `language`
  - `caption_type`

## Behavior
- Accept supported single-video YouTube watch, `youtu.be`, Shorts, and live
  URLs.
- Reject playlist-only, channel, search, and other non-single-video pages.
- Preserve source caption language; no translation in v1.
- Prefer the first manually created transcript YouTube exposes; otherwise use
  the first generated transcript.
- Return the full transcript always.
- Format `transcript_text` as timestamp-prefixed lines.
- Apply light normalization only: collapse whitespace and skip empty/noisy
  segments.

## Error contract
Stable code-prefixed MCP tool errors:
- `invalid_url`
- `unsupported_url`
- `no_transcript`
- `upstream_failure`

## Open WebUI posture
- Intended first client: direct Open WebUI MCP registration
- Current target registration: admin-only
- This service is localhost-only and is not part of the TinyAgents stdio
  registry in this slice.
