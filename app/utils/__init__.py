"""Utility functions and helpers"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_debug_log_path() -> Path:
    """Get the debug log path, creating directory if needed."""
    base_path = os.environ.get("DEBUG_LOG_PATH", str(Path.home() / "creditnexus" / ".cursor"))
    debug_path = Path(base_path)
    try:
        debug_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create debug log directory: {e}")
        # Fallback to temp directory
        debug_path = Path(os.environ.get("TEMP", "/tmp"))
    return debug_path / "debug.log"


def append_debug_log(data: dict) -> None:
    """Append data to debug log file."""
    import json

    try:
        debug_path = get_debug_log_path()
        with open(debug_path, "a") as f:
            f.write(json.dumps(data) + "\n")
    except Exception as e:
        logger.debug(f"Failed to write debug log: {e}")
