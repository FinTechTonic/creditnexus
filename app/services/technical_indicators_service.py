"""
Technical Indicators Service for calculating RSI, MACD, Bollinger Bands, and Moving Averages.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TechnicalIndicatorsService:
    """Service for calculating technical indicators."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index (RSI)."""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Use exponential moving average for RSI calculation
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average (EMA)."""
        if len(prices) < period:
            return []
        
        ema = []
        multiplier = 2.0 / (period + 1)
        
        # Start with SMA
        sma = np.mean(prices[:period])
        ema.append(sma)
        
        # Calculate EMA for remaining prices
        for price in prices[period:]:
            ema_value = (price - ema[-1]) * multiplier + ema[-1]
            ema.append(ema_value)
        
        return ema
    
    def calculate_macd(
        self,
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Optional[float]:
        """Calculate MACD (Moving Average Convergence Divergence).
        
        Returns the MACD line value (fast EMA - slow EMA).
        """
        if len(prices) < slow_period + signal_period:
            return None
        
        ema_fast = self._calculate_ema(prices, fast_period)
        ema_slow = self._calculate_ema(prices, slow_period)
        
        if not ema_fast or not ema_slow:
            return None
        
        # Align lengths (take last values)
        min_len = min(len(ema_fast), len(ema_slow))
        macd_line = ema_fast[-min_len:] - np.array(ema_slow[-min_len:])
        
        # Return the most recent MACD value
        return float(macd_line[-1]) if len(macd_line) > 0 else None
    
    def calculate_bollinger_bands(
        self,
        prices: List[float],
        period: int = 20,
        num_std: float = 2.0
    ) -> Optional[Dict[str, float]]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return None
        
        # Calculate SMA (middle band)
        sma = np.mean(prices[-period:])
        
        # Calculate standard deviation
        std = np.std(prices[-period:])
        
        # Calculate bands
        upper = sma + (num_std * std)
        lower = sma - (num_std * std)
        
        return {
            "upper": float(upper),
            "middle": float(sma),
            "lower": float(lower)
        }
    
    def calculate_moving_averages(
        self,
        prices: List[float]
    ) -> Dict[str, Optional[float]]:
        """Calculate Simple Moving Averages (SMA 50 and SMA 200)."""
        result = {
            "sma_50": None,
            "sma_200": None
        }
        
        if len(prices) >= 50:
            result["sma_50"] = float(np.mean(prices[-50:]))
        
        if len(prices) >= 200:
            result["sma_200"] = float(np.mean(prices[-200:]))
        
        return result
    
    def get_portfolio_technical_indicators(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get technical indicators for user's portfolio."""
        from app.services.trading_api_service import get_trading_api_service, TradingAPIError
        
        try:
            # Get portfolio positions
            trading_api = get_trading_api_service()
            positions = trading_api.get_positions()
            
            if not positions:
                return {
                    "rsi": None,
                    "macd": None,
                    "bollinger_bands": None,
                    "moving_averages": {}
                }
            
            # Aggregate portfolio value history (simplified approach)
            # In production, this would fetch actual historical price data
            portfolio_values = []
            
            # For now, use current portfolio value as baseline
            # In production, fetch historical portfolio values
            current_total = sum(
                float(p.get("market_value", 0) or 0)
                for p in positions
            )
            
            # Generate mock historical data based on current value
            # In production, replace with actual historical data fetching
            np.random.seed(42)  # For reproducibility
            base_value = current_total if current_total > 0 else 10000
            portfolio_values = [
                base_value * (1 + np.random.normal(0, 0.02))
                for _ in range(days)
            ]
            
            # Calculate portfolio-level indicators
            indicators = {
                "rsi": self.calculate_rsi(portfolio_values),
                "macd": self.calculate_macd(portfolio_values),
                "bollinger_bands": self.calculate_bollinger_bands(portfolio_values),
                "moving_averages": self.calculate_moving_averages(portfolio_values)
            }
            
            return indicators
            
        except (TradingAPIError, Exception) as e:
            logger.error(f"Error calculating portfolio technical indicators: {e}")
            return {
                "rsi": None,
                "macd": None,
                "bollinger_bands": None,
                "moving_averages": {}
            }
