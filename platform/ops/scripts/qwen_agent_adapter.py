#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


SERVICE_SRC = Path(__file__).resolve().parents[3] / "experiments" / "qwen-agent-proxy" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from qwen_agent_proxy.adapter_core import (  # noqa: E402,F401
    AdapterFunctionCall,
    AdapterResult,
    QWEN_AGENT_IMPORT_HINT,
    QWEN_AGENT_INSTALL_SPEC,
    QwenAgentAdapter,
    contains_raw_tool_markup,
    convert_openai_tools_to_qwen_functions,
    load_qwen_agent,
    normalize_jsonable,
    parse_json_arguments,
)
