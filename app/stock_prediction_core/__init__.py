"""
Stock prediction core: constants, market status, alpaca data, trading strategies, backtesting.

Vendored from dev/stock-prediction for use by StockPredictionService, routes, and backtesting.
"""

from app.stock_prediction_core.constants import (
    MARKET_CONFIGS,
    MARKET_STATUS_UPDATE_INTERVAL_MINUTES,
    CHRONOS_SELECTABLE_MODELS,
)
from app.stock_prediction_core.market_status import MarketStatus, get_market_status
from app.stock_prediction_core.alpaca_data import (
    ALPACA_DATA_AVAILABLE,
    get_historical_bars_as_dataframe,
    get_stock_bars,
)
from app.stock_prediction_core.trading_strategies import (
    STRATEGIES,
    get_trading_signals,
    get_combined_signals,
    calculate_trend_signals,
    calculate_mean_reversion_signals,
    calculate_momentum_signals,
    calculate_volatility_signals,
    calculate_stat_arb_signals,
)
from app.stock_prediction_core.backtesting import (
    BacktestResult,
    run_backtest,
    run_backtest_from_data_source,
)

__all__ = [
    "MARKET_CONFIGS",
    "MARKET_STATUS_UPDATE_INTERVAL_MINUTES",
    "CHRONOS_SELECTABLE_MODELS",
    "MarketStatus",
    "get_market_status",
    "ALPACA_DATA_AVAILABLE",
    "get_stock_bars",
    "get_historical_bars_as_dataframe",
    "STRATEGIES",
    "get_trading_signals",
    "get_combined_signals",
    "calculate_trend_signals",
    "calculate_mean_reversion_signals",
    "calculate_momentum_signals",
    "calculate_volatility_signals",
    "calculate_stat_arb_signals",
    "BacktestResult",
    "run_backtest",
    "run_backtest_from_data_source",
]
