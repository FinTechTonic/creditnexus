"""Modal app for CreditNexus stock prediction: GPU inference, market, and training."""

import importlib.util
from pathlib import Path

# Load app.py explicitly to avoid import conflicts
_app_path = Path(__file__).parent / "app.py"
_spec = importlib.util.spec_from_file_location("modal_app", _app_path)
_app_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_app_module)
app = _app_module.app

__all__ = ["app"]
