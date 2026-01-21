"""
Trading signal strategies for backtesting and order recommendation.

Works on OHLCV DataFrames with columns Open/High/Low/Close/Volume or open/high/low/close/volume.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

STRATEGIES = ("trend", "mean_reversion", "momentum", "volatility", "stat_arb", "combined")


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    m = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    for u, l in m.items():
        if u in d.columns and l not in d.columns:
            d[l] = d[u]
    return d


def _calculate_ema(data: pd.Series, period: int) -> pd.Series:
    return data.ewm(span=period, adjust=False).mean()


def _calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm.abs()), 0)
    minus_dm = minus_dm.abs().where((minus_dm < 0) & (plus_dm < minus_dm.abs()), 0)
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.rolling(period).mean()


def _calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    for i in range(period, len(delta)):
        if i < len(avg_gain) and i < len(avg_loss):
            avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"].shift(1)
    tr1, tr2, tr3 = high - low, abs(high - close), abs(low - close)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def _rank_normalize(series: pd.Series) -> pd.Series:
    return series.rank(pct=True)


def _calculate_hurst_exponent(time_series: pd.Series, max_lag: int = 20) -> float:
    lags = range(2, max_lag)
    tau = [np.sqrt(np.std(np.subtract(time_series[lag:].values, time_series[:-lag].values))) for lag in lags]
    reg = np.polyfit(np.log(list(lags)), np.log(tau), 1)
    return reg[0]


def calculate_trend_signals(df: pd.DataFrame) -> Dict[str, Any]:
    df = _normalize_ohlcv(df)
    if df.empty:
        return {"strategy": "Trend Following", "signal": "neutral", "confidence": 0, "error": "No data"}
    df = df.copy()
    df["ema8"] = _calculate_ema(df["close"], 8)
    df["ema21"] = _calculate_ema(df["close"], 21)
    df["ema55"] = _calculate_ema(df["close"], 55)
    df["ema200"] = _calculate_ema(df["close"], 200)
    df["adx"] = _calculate_adx(df)
    df["short_trend"] = np.where(df["ema8"] > df["ema21"], 1, -1)
    df["medium_trend"] = np.where(df["ema21"] > df["ema55"], 1, -1)
    df["long_trend"] = np.where(df["close"] > df["ema200"], 1, -1)
    latest = df.iloc[-1]
    adx_val = latest["adx"]
    adx_threshold = 20
    if latest["short_trend"] == 1 and latest["medium_trend"] == 1 and adx_val >= adx_threshold:
        signal = "bullish"
    elif latest["short_trend"] == -1 and latest["medium_trend"] == -1 and adx_val >= adx_threshold:
        signal = "bearish"
    else:
        signal = "neutral"
    confidence = 0 if pd.isna(adx_val) else min(2 + (adx_val - 40) / 20, 3) if adx_val >= 40 else (1 + (adx_val - 20) / 20) if adx_val >= 20 else adx_val / 20
    return {"strategy": "Trend Following", "signal": signal, "confidence": round(confidence, 2), "metrics": {"ema8": round(latest["ema8"], 2), "ema21": round(latest["ema21"], 2), "adx": round(adx_val if not pd.isna(adx_val) else 0, 2)}}


def calculate_mean_reversion_signals(df: pd.DataFrame) -> Dict[str, Any]:
    df = _normalize_ohlcv(df)
    if df.empty:
        return {"strategy": "Mean Reversion", "signal": "neutral", "confidence": 0, "error": "No data"}
    df = df.copy()
    df["sma50"] = df["close"].rolling(50).mean()
    df["std50"] = df["close"].rolling(50).std()
    df["zscore"] = (df["close"] - df["sma50"]) / df["std50"]
    df["sma20"] = df["close"].rolling(20).mean()
    df["std20"] = df["close"].rolling(20).std()
    df["upper_band"] = df["sma20"] + 2 * df["std20"]
    df["lower_band"] = df["sma20"] - 2 * df["std20"]
    df["rsi14"] = _calculate_rsi(df["close"], 14)
    latest = df.iloc[-1]
    signal, confidence = "neutral", 0
    if latest["zscore"] < -1.5 and latest["close"] <= latest["lower_band"] and latest["rsi14"] < 30:
        signal, confidence = "bullish", min(abs(latest["zscore"]) / 1.5, 3)
    elif latest["zscore"] > 1.5 and latest["close"] >= latest["upper_band"] and latest["rsi14"] > 70:
        signal, confidence = "bearish", min(abs(latest["zscore"]) / 1.5, 3)
    return {"strategy": "Mean Reversion", "signal": signal, "confidence": round(confidence, 2), "metrics": {"z_score": round(latest["zscore"], 2) if not pd.isna(latest["zscore"]) else 0, "rsi14": round(latest["rsi14"], 2) if not pd.isna(latest["rsi14"]) else 0}}


def calculate_momentum_signals(df: pd.DataFrame) -> Dict[str, Any]:
    df = _normalize_ohlcv(df)
    if df.empty or len(df) < 126:
        return {"strategy": "Momentum", "signal": "neutral", "confidence": 0, "error": "Insufficient data"}
    df = df.copy()
    df["mom_1m"] = df["close"].pct_change(21)
    df["mom_3m"] = df["close"].pct_change(63)
    df["mom_6m"] = df["close"].pct_change(126)
    df["mom_1m_rank"] = _rank_normalize(df["mom_1m"])
    df["mom_3m_rank"] = _rank_normalize(df["mom_3m"])
    df["mom_6m_rank"] = _rank_normalize(df["mom_6m"])
    df["vol_ma21"] = df["volume"].rolling(21).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma21"]
    df["momentum_score"] = (0.5 * df["mom_1m_rank"] + 0.3 * df["mom_3m_rank"] + 0.2 * df["mom_6m_rank"])
    df["momentum_score"] = (df["momentum_score"] - 0.5) * 2
    latest = df.iloc[-1]
    if latest["momentum_score"] > 0.2 and latest["vol_ratio"] > 1.0:
        signal, confidence = "bullish", min(abs(latest["momentum_score"]) * 3, 3)
    elif latest["momentum_score"] < -0.2 and latest["vol_ratio"] > 1.0:
        signal, confidence = "bearish", min(abs(latest["momentum_score"]) * 3, 3)
    else:
        signal, confidence = "neutral", 0
    return {"strategy": "Momentum", "signal": signal, "confidence": round(confidence, 2), "metrics": {"momentum_score": round(latest["momentum_score"], 2) if not pd.isna(latest["momentum_score"]) else 0}}


def calculate_volatility_signals(df: pd.DataFrame) -> Dict[str, Any]:
    df = _normalize_ohlcv(df)
    if df.empty or len(df) < 84:
        return {"strategy": "Volatility", "signal": "neutral", "confidence": 0, "error": "Insufficient data"}
    df = df.copy()
    df["returns"] = df["close"].pct_change()
    df["volatility_21d"] = df["returns"].rolling(21).std() * np.sqrt(252)
    df["volatility_63d_avg"] = df["volatility_21d"].rolling(63).mean()
    df["volatility_std"] = df["volatility_21d"].rolling(63).std()
    df["volatility_zscore"] = (df["volatility_21d"] - df["volatility_63d_avg"]) / df["volatility_std"]
    df["atr"] = _calculate_atr(df, 14)
    latest = df.iloc[-1]
    signal, confidence = "neutral", 0
    if not pd.isna(latest.get("volatility_zscore")) and latest["volatility_zscore"] < -1.5:
        signal, confidence = "bullish", min(abs(latest["volatility_zscore"]) / 1.5, 3)
    elif not pd.isna(latest.get("volatility_zscore")) and latest["volatility_zscore"] > 1.5:
        signal, confidence = "bearish", min(abs(latest["volatility_zscore"]) / 1.5, 3)
    return {"strategy": "Volatility", "signal": signal, "confidence": round(confidence, 2), "metrics": {"volatility_zscore": round(latest["volatility_zscore"], 2) if not pd.isna(latest.get("volatility_zscore")) else 0}}


def calculate_stat_arb_signals(df: pd.DataFrame) -> Dict[str, Any]:
    df = _normalize_ohlcv(df)
    if df.empty or len(df) < 126:
        return {"strategy": "Statistical Arbitrage", "signal": "neutral", "confidence": 0, "error": "Insufficient data"}
    df = df.copy()
    df["returns"] = df["close"].pct_change()
    df["annualized_returns"] = df["returns"] * np.sqrt(252)
    df["skew_63d"] = df["annualized_returns"].rolling(63).skew()
    df["kurt_63d"] = df["annualized_returns"].rolling(63).kurt()
    latest_returns = df["returns"].dropna()
    hurst = _calculate_hurst_exponent(latest_returns) if len(latest_returns) >= 20 else 0.5
    latest = df.iloc[-1]
    signal, confidence = "neutral", 0
    if hurst < 0.4:
        if latest["skew_63d"] > 0.5:
            signal, confidence = "bullish", (0.5 - hurst) * 10
        elif latest["skew_63d"] < -0.5:
            signal, confidence = "bearish", (0.5 - hurst) * 10
    confidence = min(confidence, 3)
    return {"strategy": "Statistical Arbitrage", "signal": signal, "confidence": round(confidence, 2), "metrics": {"hurst_exponent": round(hurst, 2), "skewness": round(latest["skew_63d"], 2) if not pd.isna(latest["skew_63d"]) else 0}}


def get_combined_signals(df: pd.DataFrame) -> Dict[str, Any]:
    trend = calculate_trend_signals(df)
    mean_rev = calculate_mean_reversion_signals(df)
    mom = calculate_momentum_signals(df)
    vol = calculate_volatility_signals(df)
    stat = calculate_stat_arb_signals(df)
    all_s = [trend, mean_rev, mom, vol, stat]
    bullish_score = sum(s["confidence"] for s in all_s if s["signal"] == "bullish")
    bearish_score = sum(s["confidence"] for s in all_s if s["signal"] == "bearish")
    if bullish_score > bearish_score:
        consensus_signal, consensus_conf = "bullish", min(bullish_score / 15, 1.0)
    elif bearish_score > bullish_score:
        consensus_signal, consensus_conf = "bearish", min(bearish_score / 15, 1.0)
    else:
        consensus_signal, consensus_conf = "neutral", 0.0
    return {"strategies": {"trend_following": trend, "mean_reversion": mean_rev, "momentum": mom, "volatility": vol, "statistical_arbitrage": stat}, "consensus": {"signal": consensus_signal, "confidence": round(consensus_conf, 2), "bullish_score": round(bullish_score, 2), "bearish_score": round(bearish_score, 2)}}


def get_trading_signals(df: pd.DataFrame, strategy: str = "combined") -> Dict[str, Any]:
    if strategy == "trend":
        return calculate_trend_signals(df)
    if strategy == "mean_reversion":
        return calculate_mean_reversion_signals(df)
    if strategy == "momentum":
        return calculate_momentum_signals(df)
    if strategy == "volatility":
        return calculate_volatility_signals(df)
    if strategy == "stat_arb":
        return calculate_stat_arb_signals(df)
    return get_combined_signals(df)
