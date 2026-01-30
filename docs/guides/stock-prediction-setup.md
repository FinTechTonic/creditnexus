# Stock Prediction, Chronos, Backtesting, and Market Data

Stock prediction provides daily, hourly, and 15‑minute forecasts (Chronos or technical strategies), backtesting over OHLCV, order recommendations, and market-status. It depends on **market data** (Alpaca or yahooquery) and optionally **Chronos** via Modal or locally. Rolling credits (`stock_prediction_daily`, `stock_prediction_hourly`, `stock_prediction_15min`) apply when `RollingCreditsService` is used.

---

## 1. Overview

| Component | Role |
|-----------|------|
| **StockPredictionService** | `predict_daily`, `predict_hourly`, `predict_15min` — Chronos or technical; uses `ChronosModelManager`, `MarketDataService`, credits |
| **ChronosModelManager** | Chronos inference: Modal `chronos_inference` or local `chronos-bolt` when `STOCK_PREDICTION_USE_LOCAL=true` |
| **MarketDataService** | OHLCV: Alpaca (if `ALPACA_DATA_ENABLED`) or **yahooquery** (fallback). Used by prediction and backtesting |
| **Backtesting** | `run_backtest_from_data_source` in `app.stock_prediction_core.backtesting`; strategies: trend, mean_reversion, momentum, volatility, stat_arb, combined |
| **Modal** | `chronos_inference`, `chronos_train` (stub), `market_status` — optional when not using local Chronos |

**Code**: `app/services/stock_prediction_service.py`, `app/services/chronos_model_manager.py`, `app/services/market_data_service.py`, `app/stock_prediction_core/backtesting.py`, `chronos_modal/app.py`, `app/api/stock_prediction_routes.py`

---

## 2. Configuration

### 2.1 Feature and Lookback

| Variable | Description | Default |
|----------|-------------|---------|
| `STOCK_PREDICTION_ENABLED` | Enable prediction APIs (daily, hourly, 15min, backtest, recommend-order, models, market-status). If `false`, all return 403. | `false` |
| `STOCK_PREDICTION_DEFAULT_LOOKBACK_DAILY` | Default lookback bars for daily | `252` |
| `STOCK_PREDICTION_DEFAULT_LOOKBACK_HOURLY` | Default lookback bars for hourly | `504` |
| `STOCK_PREDICTION_DEFAULT_LOOKBACK_15MIN` | Default lookback bars for 15min | `96` |

### 2.2 Market Data (OHLCV for Prediction and Backtesting)

Market data is provided by **MarketDataService**: Alpaca first (when enabled), then **yahooquery**.

| Source | When used | Requirements |
|--------|-----------|--------------|
| **Alpaca** | `ALPACA_DATA_ENABLED=true` and `ALPACA_API_KEY` / `ALPACA_API_SECRET` set | `alpaca-py` installed; keys from [Alpaca](https://alpaca.markets/). See [Alpaca Trading Setup](alpaca-trading-setup.md). |
| **yahooquery** | Fallback when Alpaca is off or returns no data | `pip install yahooquery` |

**Config (Alpaca as data source):**

| Variable | Description | Default |
|----------|-------------|---------|
| `ALPACA_DATA_ENABLED` | Use Alpaca for historical bars in stock prediction and backtesting | `false` |
| `ALPACA_API_KEY` | Alpaca API key | — |
| `ALPACA_API_SECRET` | Alpaca API secret | — |

Same keys are used for **trading** (place/cancel orders, portfolio). Base URL: `ALPACA_BASE_URL` (e.g. `https://paper-api.alpaca.markets` for paper).

### 2.3 Chronos: Modal vs Local

| Variable | Description | Default |
|----------|-------------|---------|
| `STOCK_PREDICTION_USE_LOCAL` | `true`: run Chronos locally with `chronos-bolt`; `false`: use Modal `chronos_inference` | `false` |
| `CHRONOS_MODEL_ID` | Model id (e.g. `amazon/chronos-t5-small`, `amazon/chronos-t5-base`). Selectable in Predictions tab and via `model_id` query. | `amazon/chronos-t5-small` |
| `CHRONOS_DEVICE` | Device for Chronos: `cpu`, `cuda`, `cuda:0`. Used by Modal and when running locally. | `cpu` |

**Local Chronos** (`STOCK_PREDICTION_USE_LOCAL=true`):

```bash
pip install chronos-bolt torch
```

**Modal** (`STOCK_PREDICTION_USE_LOCAL=false`):

| Variable | Description | Default |
|----------|-------------|---------|
| `MODAL_APP_NAME` | Modal app name | `creditnexus-stock-prediction` |
| `MODAL_TOKEN_ID` | Modal token ID for server-side client (optional) | — |
| `MODAL_TOKEN_SECRET` | Modal token secret | — |
| `MODAL_USE_GPU` | **Env at run/deploy time.** `1`, `true`, or `yes`: Modal `chronos_inference` and `chronos_train` use GPU (T4). Set when running: `MODAL_USE_GPU=1 modal run chronos_modal/app.py` or `MODAL_USE_GPU=1 modal deploy` | — |

Modal image: `modal/image.py` (`chronos-bolt`, `torch`, `alpaca-py`, `pandas`, etc.).

---

## 3. APIs and UI

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stock-prediction/daily` | GET | Daily prediction; `symbol`, `lookback`, `horizon`, `strategy`, `model_id` |
| `/api/stock-prediction/hourly` | GET | Hourly prediction |
| `/api/stock-prediction/15min` | GET | 15‑minute prediction |
| `/api/stock-prediction/backtest` | POST | Backtest; body: `symbol`, `start`, `end`, `strategy`, `timeframe`, `initial_capital`; returns `equity_curve`, `trades` |
| `/api/stock-prediction/models` | GET | Selectable Chronos model ids |
| `/api/stock-prediction/market-status` | GET | Market status (`market=US_STOCKS`, etc.) |
| `/api/stock-prediction/recommend-order` | POST | Order recommendation; requires auth |

**UI:** Trading Dashboard → **Predictions** (run prediction, Chronos model dropdown, chart, order recommendation), **Backtest** (form, equity curve, trades table).

---

## 4. Backtesting

- **Strategies:** `combined`, `trend`, `mean_reversion`, `momentum`, `volatility`, `stat_arb`
- **Timeframes:** `1d`, `1h`, `15m` (mapped to 1D, 1H, 15Min for data)
- **Data:** `MarketDataService.get_historical_data` (Alpaca or yahooquery). Requires ≥130 bars; for 1d, typically ≥6 months of history.
- **Request:** `symbol`, `start`, `end` (YYYY‑MM‑DD), `strategy`, `timeframe`, `initial_capital` (default 100_000)
- **Response:** `total_return`, `sharpe_ratio`, `max_drawdown`, `win_rate`, `n_trades`, `equity_curve`, `trades`, `metadata`

---

## 5. Rolling Credits (Stock Prediction)

When `RollingCreditsService` is used, `stock_prediction_daily`, `stock_prediction_hourly`, `stock_prediction_15min` are deducted. Tier allocation is in [Rolling Credits Setup](rolling-credits-setup.md). If the user has no balance, prediction may be refused depending on service wiring.

---

## 6. Quick Start

1. Set `STOCK_PREDICTION_ENABLED=true`.
2. **Market data:** either
   - `ALPACA_DATA_ENABLED=true` and `ALPACA_API_KEY`, `ALPACA_API_SECRET` (and `ALPACA_BASE_URL` for trading), or
   - Rely on **yahooquery** (`pip install yahooquery`).
3. **Chronos:**
   - **Modal:** `pip install modal`, `modal token new`; deploy/run with `MODAL_USE_GPU=1` if you want GPU. Set `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET` only if the server needs to spawn Modal runs.
   - **Local:** `STOCK_PREDICTION_USE_LOCAL=true`, `pip install chronos-bolt torch`, set `CHRONOS_DEVICE` (e.g. `cuda` if GPU).
4. Open Trading → Predictions and Backtest.

---

## 7. Troubleshooting

| Issue | Check |
|-------|-------|
| 403 on prediction/backtest | `STOCK_PREDICTION_ENABLED=true` |
| “Insufficient data” in backtest | Date range and symbol; need ≥130 bars. For 1d, use ~6+ months. yahooquery/Alpaca must return OHLCV. |
| Chronos “chronos/torch not installed” | Local: `pip install chronos-bolt torch` |
| Modal inference fails | `modal run chronos_modal/app.py` or `modal deploy`; `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET` if the app invokes Modal. `MODAL_USE_GPU=1` when deploying for GPU. |
| No market data | `yahooquery` installed; or Alpaca with `ALPACA_DATA_ENABLED`, valid keys, and `ALPACA_BASE_URL` when also trading. |
