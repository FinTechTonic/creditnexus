"""Constants for stock prediction: market configs, update intervals, and Chronos model selection."""

MARKET_STATUS_UPDATE_INTERVAL_MINUTES = 10

# Chronos model IDs selectable in the UI and via model_id API param. Vendored/default is amazon/chronos-t5-small.
CHRONOS_SELECTABLE_MODELS = [
    "amazon/chronos-t5-small",
    "amazon/chronos-t5-base",
]

MARKET_CONFIGS = {
    "US_STOCKS": {
        "name": "US Stock Market",
        "symbol": "^GSPC",
        "type": "stocks",
        "timezone": "US/Eastern",
        "open_time": "09:30",
        "close_time": "16:00",
        "days": [0, 1, 2, 3, 4],
        "description": "NYSE, NASDAQ, AMEX",
    },
    "US_FUTURES": {
        "name": "US Futures Market",
        "symbol": "ES=F",
        "type": "futures",
        "timezone": "US/Eastern",
        "open_time": "18:00",
        "close_time": "17:00",
        "days": [0, 1, 2, 3, 4, 5, 6],
        "description": "CME, ICE, CBOT",
    },
    "FOREX": {
        "name": "Forex Market",
        "symbol": "EURUSD=X",
        "type": "forex",
        "timezone": "UTC",
        "open_time": "00:00",
        "close_time": "23:59",
        "days": [0, 1, 2, 3, 4, 5, 6],
        "description": "Global Currency Exchange",
    },
    "CRYPTO": {
        "name": "Cryptocurrency Market",
        "symbol": "BTC-USD",
        "type": "crypto",
        "timezone": "UTC",
        "open_time": "00:00",
        "close_time": "23:59",
        "days": [0, 1, 2, 3, 4, 5, 6],
        "description": "Bitcoin, Ethereum, Altcoins",
    },
    "COMMODITIES": {
        "name": "Commodities Market",
        "symbol": "GC=F",
        "type": "commodities",
        "timezone": "US/Eastern",
        "open_time": "18:00",
        "close_time": "17:00",
        "days": [0, 1, 2, 3, 4, 5, 6],
        "description": "Gold, Silver, Oil, Natural Gas",
    },
    "EUROPE": {
        "name": "European Markets",
        "symbol": "^STOXX50E",
        "type": "stocks",
        "timezone": "Europe/London",
        "open_time": "08:00",
        "close_time": "16:30",
        "days": [0, 1, 2, 3, 4],
        "description": "London, Frankfurt, Paris",
    },
    "ASIA": {
        "name": "Asian Markets",
        "symbol": "^N225",
        "type": "stocks",
        "timezone": "Asia/Tokyo",
        "open_time": "09:00",
        "close_time": "15:30",
        "days": [0, 1, 2, 3, 4],
        "description": "Tokyo, Hong Kong, Shanghai",
    },
}
