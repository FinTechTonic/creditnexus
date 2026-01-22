"""Modal App for CreditNexus stock prediction (Chronos inference, market, training)."""

import os
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import modal

# Load image.py explicitly to avoid import conflicts with modal package
_image_path = Path(__file__).parent / "image.py"
_spec = importlib.util.spec_from_file_location("modal_image", _image_path)
_image_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_image_module)
chronos_image = _image_module.chronos_image

# Config from env: MODAL_USE_GPU (1/true/yes) and CHRONOS_DEVICE (cpu, cuda, cuda:0).
# Set when running: modal run modal/app.py or modal deploy, e.g. MODAL_USE_GPU=1 modal deploy
_MODAL_USE_GPU = os.getenv("MODAL_USE_GPU", "").lower() in ("1", "true", "yes")
_CHRONOS_DEVICE = os.getenv("CHRONOS_DEVICE", "cpu")

app = modal.App(os.getenv("MODAL_APP_NAME", "creditnexus-stock-prediction"))


@app.function(image=chronos_image, gpu="T4" if _MODAL_USE_GPU else None)
def chronos_inference(
    symbol: str,
    context: List[float],
    horizon: int = 30,
    model_id: str = "amazon/chronos-t5-small",
    device: str = "",
) -> Dict[str, Any]:
    """
    Run Chronos inference for a symbol. context = past values (e.g. close prices), horizon = steps to forecast.
    device: override for CHRONOS_DEVICE (e.g. cpu, cuda, cuda:0). Default uses env CHRONOS_DEVICE.
    """
    dev = device or _CHRONOS_DEVICE
    try:
        from chronos import ChronosPipeline
        import torch

        pipe = ChronosPipeline.from_pretrained(model_id, device_map=dev, torch_dtype=torch.float32)
        # context: [batch, length] or [length]; we have [length]
        t = torch.tensor([context], dtype=torch.float32)
        forecast = pipe.predict(context=t, prediction_length=horizon, num_samples=20)
        # forecast: [batch, num_samples, horizon]; take median over samples
        med = forecast.median(dim=1).values
        out = med[0].tolist()
        return {"forecast": out, "model_id": model_id, "symbol": symbol, "horizon": horizon}
    except Exception as e:
        return {"forecast": [], "model_id": model_id, "symbol": symbol, "error": str(e)}


@app.function(image=chronos_image)
def market_status(market: str = "US_STOCKS") -> Dict[str, Any]:
    """
    US market status: is_open, next_trading_day, time_until_open, time_until_close (US/Eastern).
    """
    import pytz

    et = pytz.timezone("US/Eastern")
    now = datetime.now(et)
    # US stocks: Mon–Fri 9:30–16:00 ET
    if now.weekday() >= 5:
        next_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        while next_open.weekday() >= 5 or next_open <= now:
            next_open += timedelta(days=1)
        return {
            "is_open": False,
            "market": market,
            "next_trading_day": next_open.strftime("%Y-%m-%d"),
            "current_time_et": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "status_text": "Market closed",
        }
    open_ = now.replace(hour=9, minute=30, second=0, microsecond=0)
    close_ = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if now < open_:
        return {"is_open": False, "market": market, "next_trading_day": now.strftime("%Y-%m-%d"), "current_time_et": now.strftime("%Y-%m-%d %H:%M:%S %Z"), "status_text": "Pre-market"}
    if now >= close_:
        return {"is_open": False, "market": market, "next_trading_day": (now + timedelta(days=1)).strftime("%Y-%m-%d"), "current_time_et": now.strftime("%Y-%m-%d %H:%M:%S %Z"), "status_text": "After-hours"}
    return {"is_open": True, "market": market, "next_trading_day": now.strftime("%Y-%m-%d"), "current_time_et": now.strftime("%Y-%m-%d %H:%M:%S %Z"), "status_text": "Market open"}


@app.function(image=chronos_image, gpu="T4" if _MODAL_USE_GPU else None)
def chronos_train(
    model_id: str = "amazon/chronos-t5-small",
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Placeholder for Chronos training. Creates no durable state; for full training
    trigger from API and persist TrainingJob via DB. Model and GPU are selectable
    via CHRONOS_DEVICE and MODAL_USE_GPU.
    """
    return {
        "status": "ok",
        "message": "Training placeholder; wire to TrainingJob and data pipeline for production.",
        "model_id": model_id,
        "config": config or {},
    }
