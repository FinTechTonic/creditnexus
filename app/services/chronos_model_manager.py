"""Chronos model manager: runs Chronos inference via Modal or locally (STOCK_PREDICTION_USE_LOCAL)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _run_local_chronos(
    model_id: str, context: List[float], horizon: int, device: str
) -> Dict[str, Any]:
    """Run Chronos locally. Returns dict with forecast or error."""
    try:
        from chronos import ChronosPipeline
        import torch

        pipe = ChronosPipeline.from_pretrained(model_id, device_map=device, torch_dtype=torch.float32)
        t = torch.tensor([context], dtype=torch.float32)
        forecast = pipe.predict(context=t, prediction_length=horizon, num_samples=20)
        med = forecast.median(dim=1).values
        return {"forecast": med[0].tolist(), "model_id": model_id}
    except ImportError as e:
        return {"forecast": [], "model_id": model_id, "error": f"chronos/torch not installed: {e}"}
    except Exception as e:
        return {"forecast": [], "model_id": model_id, "error": str(e)}


class ChronosModelManager:
    """Run Chronos time-series inference via Modal or locally (STOCK_PREDICTION_USE_LOCAL)."""

    def __init__(self) -> None:
        self._model_id = getattr(settings, "CHRONOS_MODEL_ID", None) or "amazon/chronos-t5-small"
        self._app_name = getattr(settings, "MODAL_APP_NAME", None) or "creditnexus-stock-prediction"
        self._device = getattr(settings, "CHRONOS_DEVICE", None) or "cpu"
        self._use_local = getattr(settings, "STOCK_PREDICTION_USE_LOCAL", False)

    def run_inference(
        self,
        symbol: str,
        context: List[float],
        horizon: int,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run Chronos inference. context = past values (e.g. Close prices), horizon = steps to forecast.

        When STOCK_PREDICTION_USE_LOCAL is True: runs Chronos locally with CHRONOS_DEVICE.
        Otherwise: calls Modal chronos_inference (uses MODAL_USE_GPU and CHRONOS_DEVICE in Modal app).
        On failure returns {"forecast": [], "model_id": ..., "error": str}.
        """
        mid = model_id or self._model_id
        if not context or horizon <= 0:
            return {"forecast": [], "model_id": mid, "symbol": symbol, "error": "invalid context or horizon"}

        if self._use_local:
            out = _run_local_chronos(mid, context, horizon, self._device)
            out.setdefault("symbol", symbol)
            out.setdefault("horizon", horizon)
            return out

        try:
            import modal

            fn = modal.Function.from_name(self._app_name, "chronos_inference")
            out = fn.remote(
                symbol=symbol,
                context=context,
                horizon=horizon,
                model_id=mid,
                device=self._device,
            )
            if isinstance(out, dict) and "error" in out:
                return {"forecast": [], "model_id": mid, "symbol": symbol, "error": out["error"]}
            return out if isinstance(out, dict) else {"forecast": [], "model_id": mid, "error": "invalid response"}
        except Exception as e:
            logger.warning("Chronos Modal inference failed for %s: %s", symbol, e)
            return {"forecast": [], "model_id": mid, "symbol": symbol, "error": str(e)}
