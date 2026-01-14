# Architecture: Open WebUI

Open WebUI is the UI layer. Requests flow from the browser to Open WebUI, then to
LiteLLM at `http://127.0.0.1:4000/v1`, which routes to model backends.
