# NOW — OptiLLM Router Latency (OV Router Service)

## Current focus
1) Baseline OptiLLM router latency vs direct LiteLLM. (done)
2) Design a phased, reversible move to an OpenVINO-backed router classifier. (in progress)
3) Stand up OV router service in isolation and validate latency/accuracy. (next)
4) Add a parallel OptiLLM `router_ov` plugin that calls the OV service. (next)
5) Shadow‑mode comparison, then switch `router` to OV with fallback. (next)

## NEXT UP
Phase 1: Stand up the OpenVINO router service (local-only), validate outputs/latency.

## Out of scope (for now)
- LiteLLM UI access / prompt management
- OptiLLM local inference (Studio)
- New model downloads/conversions (beyond router classifier)
- New registries beyond presets/handles
