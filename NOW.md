# NOW — OptiLLM Router POC (OV Encoder + NumPy Head)

## Current focus
1) Draft a minimal POC plan to run ModernBERT encoder in OpenVINO and keep the router head in NumPy. (done)
2) Export ModernBERT base + router checkpoint encoders to OpenVINO IR. (done)
3) Build a local script to run OV encoder + NumPy head and return an approach. (done)
4) Parity test vs current OptiLLM router for a small input set. (done)
5) Confirm FP32 parity stability for the router checkpoint encoder. (done)
6) Decide whether to integrate via a local router service or defer. (next)

## NEXT UP
Decision: wrap the FP32 router POC as a local service or defer integration.

## Out of scope (for now)
- OptiLLM router integration (only after parity + latency wins)
- LiteLLM UI access / prompt management
- OptiLLM local inference (Studio)
- New model downloads/conversions
- New registries beyond presets/handles
