"""
Site-level runtime patching for OptiLLM Local (Orin).

Goal: prevent scikit-learn imports on Jetson where libgomp TLS errors
break Transformers at runtime. We force Transformers to treat sklearn
as unavailable, without uninstalling packages.
"""

import os


def _disable_sklearn() -> None:
    if os.getenv("OPTILLM_DISABLE_SKLEARN", "1") != "1":
        return
    try:
        import transformers.utils.import_utils as iu

        def _false() -> bool:
            return False

        iu.is_sklearn_available = _false
    except Exception:
        # Do not block startup if transformers is unavailable at import time.
        pass


_disable_sklearn()
