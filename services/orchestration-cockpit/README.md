# orchestration-cockpit

Local Mini-side operator cockpit service for the orchestration plane.

This service pairs:
- a LangGraph Agent Server in local/dev mode on `127.0.0.1:2024`
- a stock non-vendored Agent Chat UI on `127.0.0.1:3030`
- a specialized runtime portal through Mini `127.0.0.1:8129 -> Studio 127.0.0.1:8120`

Current service posture proves:
- browser GUI viability
- deterministic graph routing
- one narrow specialized-runtime invocation through `omlx-runtime`
- generated graph documentation and local run/artifact ownership

It does **not** provide a public gateway, a commodity chat path, or a full
assistant surface.
