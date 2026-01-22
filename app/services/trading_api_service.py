"""Trading API service abstraction for multiple trading APIs (Alpaca, Polygon, etc.)."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime

from app.core import data_cache as dc
from app.utils.json_serializer import serialize_cdm_data

logger = logging.getLogger(__name__)


class TradingAPIError(Exception):
    """Base exception for trading API errors."""
    pass


class TradingAPIService(ABC):
    """Abstract base class for trading API services."""
    
    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """Submit an order to the trading API.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            side: "buy" or "sell"
            order_type: "market", "limit", "stop", "stop_limit"
            quantity: Number of shares/units
            price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            time_in_force: "day", "gtc", "ioc", "fok"
            
        Returns:
            Dictionary with order_id, status, and other order details
            
        Raises:
            TradingAPIError: If order submission fails
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get the status of an order.
        
        Args:
            order_id: Order ID from trading API
            
        Returns:
            Dictionary with order status, filled_quantity, average_fill_price, etc.
            
        Raises:
            TradingAPIError: If order lookup fails
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order.
        
        Args:
            order_id: Order ID from trading API
            
        Returns:
            Dictionary with cancellation status
            
        Raises:
            TradingAPIError: If cancellation fails
        """
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information (balance, buying power, etc.).
        
        Returns:
            Dictionary with account details
            
        Raises:
            TradingAPIError: If account lookup fails
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions.
        
        Returns:
            List of position dictionaries with symbol, quantity, avg_price, etc.
            
        Raises:
            TradingAPIError: If positions lookup fails
        """
        pass
    
    @abstractmethod
    def get_market_data(self, symbol: str, db: Optional[Any] = None) -> Dict[str, Any]:
        """Get market data for a symbol (price, volume, etc.).
        
        Args:
            symbol: Stock symbol
            db: Optional DB session for DataCache (Alpaca impl caches with TTL_TRADING_QUOTE).
            
        Returns:
            Dictionary with current price, bid, ask, volume, etc.
            
        Raises:
            TradingAPIError: If market data lookup fails
        """
        pass


class AlpacaTradingAPIService(TradingAPIService):
    """Alpaca trading API service implementation."""
    
    def __init__(self, api_key: str, api_secret: str, base_url: Optional[str] = None):
        """Initialize Alpaca API service.
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: Base URL (defaults to paper trading URL)
        """
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest
            from alpaca.trading.enums import OrderSide as AlpacaOrderSide, OrderType as AlpacaOrderType, TimeInForce
        except ImportError:
            raise TradingAPIError("alpaca-py package not installed. Install with: pip install alpaca-py")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url or "https://paper-api.alpaca.markets"
        
        self.client = TradingClient(
            api_key=api_key,
            secret_key=api_secret,
            paper=True if "paper" in self.base_url else False
        )
        
        self._order_side_map = {
            "buy": AlpacaOrderSide.BUY,
            "sell": AlpacaOrderSide.SELL
        }
        
        self._time_in_force_map = {
            "day": TimeInForce.DAY,
            "gtc": TimeInForce.GTC,
            "ioc": TimeInForce.IOC,
            "fok": TimeInForce.FOK
        }
    
    def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """Submit an order to Alpaca."""
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest
        from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce
        
        try:
            alpaca_side = self._order_side_map[side.lower()]
            alpaca_tif = self._time_in_force_map.get(time_in_force.lower(), TimeInForce.DAY)
            qty = float(quantity)
            
            if order_type == "market":
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=alpaca_side,
                    time_in_force=alpaca_tif
                )
            elif order_type == "limit":
                if not price:
                    raise TradingAPIError("Limit price required for limit orders")
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=alpaca_side,
                    limit_price=float(price),
                    time_in_force=alpaca_tif
                )
            elif order_type == "stop":
                if not stop_price:
                    raise TradingAPIError("Stop price required for stop orders")
                order_request = StopOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=alpaca_side,
                    stop_price=float(stop_price),
                    time_in_force=alpaca_tif
                )
            elif order_type == "stop_limit":
                if not price or not stop_price:
                    raise TradingAPIError("Limit price and stop price required for stop_limit orders")
                order_request = StopLimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=alpaca_side,
                    limit_price=float(price),
                    stop_price=float(stop_price),
                    time_in_force=alpaca_tif
                )
            else:
                raise TradingAPIError(f"Unsupported order type: {order_type}")
            
            order = self.client.submit_order(order_request)
            
            # Serialize order.dict() to ensure UUIDs and other non-JSON types are converted
            raw_response = order.dict() if hasattr(order, 'dict') else {}
            # Convert any UUIDs in the raw response to strings
            serialized_response = serialize_cdm_data(raw_response)
            
            return {
                "order_id": str(order.id),
                "status": order.status.value.lower(),
                "symbol": order.symbol,
                "side": order.side.value.lower(),
                "order_type": order.order_type.value.lower(),
                "quantity": float(order.qty),
                "filled_quantity": float(order.filled_qty) if order.filled_qty else 0,
                "average_fill_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "raw_response": serialized_response
            }
            
        except Exception as e:
            logger.error(f"Alpaca order submission failed: {e}", exc_info=True)
            raise TradingAPIError(f"Failed to submit order: {str(e)}")
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status from Alpaca."""
        try:
            order = self.client.get_order_by_id(order_id)
            
            return {
                "order_id": str(order.id),
                "status": order.status.value.lower(),
                "symbol": order.symbol,
                "side": order.side.value.lower(),
                "order_type": order.order_type.value.lower(),
                "quantity": float(order.qty),
                "filled_quantity": float(order.filled_qty) if order.filled_qty else 0,
                "average_fill_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "price": float(order.limit_price) if order.limit_price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "cancelled_at": order.canceled_at.isoformat() if order.canceled_at else None,
                "raw_response": order.dict()
            }
            
        except Exception as e:
            logger.error(f"Alpaca order status lookup failed: {e}", exc_info=True)
            raise TradingAPIError(f"Failed to get order status: {str(e)}")
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order in Alpaca."""
        try:
            self.client.cancel_order_by_id(order_id)
            
            return {
                "order_id": order_id,
                "status": "cancelled"
            }
            
        except Exception as e:
            logger.error(f"Alpaca order cancellation failed: {e}", exc_info=True)
            raise TradingAPIError(f"Failed to cancel order: {str(e)}")
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information from Alpaca."""
        try:
            account = self.client.get_account()
            
            return {
                "account_number": account.account_number,
                "buying_power": float(account.buying_power) if account.buying_power else 0,
                "cash": float(account.cash) if account.cash else 0,
                "equity": float(account.equity) if account.equity else 0,
                "portfolio_value": float(account.portfolio_value) if account.portfolio_value else 0,
                "currency": account.currency,
                "raw_response": account.dict()
            }
            
        except Exception as e:
            logger.error(f"Alpaca account info lookup failed: {e}", exc_info=True)
            raise TradingAPIError(f"Failed to get account info: {str(e)}")
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get positions from Alpaca."""
        try:
            positions = self.client.get_all_positions()
            
            return [
                {
                    "symbol": pos.symbol,
                    "quantity": float(pos.qty),
                    "average_price": float(pos.avg_entry_price) if pos.avg_entry_price else None,
                    "current_price": float(pos.current_price) if pos.current_price else None,
                    "market_value": float(pos.market_value) if pos.market_value else None,
                    "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else None,
                    "raw_response": pos.dict()
                }
                for pos in positions
            ]
            
        except Exception as e:
            logger.error(f"Alpaca positions lookup failed: {e}", exc_info=True)
            raise TradingAPIError(f"Failed to get positions: {str(e)}")
    
    def get_market_data(self, symbol: str, db: Optional[Any] = None) -> Dict[str, Any]:
        """Get market data from Alpaca. Cached with TTL_TRADING_QUOTE when db is provided."""
        cache_key = dc.make_key("trading_quote", symbol)
        cached = dc.get(cache_key, db)
        if cached is not None:
            return cached
        try:
            # Try multiple approaches to get market data
            out = None
            
            # Approach 1: Try StockDataClient for real-time data (if available in newer alpaca-py)
            try:
                from alpaca.data import StockDataClient
                from alpaca.data.requests import StockLatestQuoteRequest
                
                data_client = StockDataClient(
                    api_key=self.api_key,
                    secret_key=self.api_secret
                )
                
                # Try get_latest_quotes (plural) or get_latest_quote
                if hasattr(data_client, 'get_latest_quotes'):
                    quote = data_client.get_latest_quotes(
                        StockLatestQuoteRequest(symbol_or_symbols=[symbol])
                    )
                elif hasattr(data_client, 'get_latest_quote'):
                    quote = data_client.get_latest_quote(
                        StockLatestQuoteRequest(symbol_or_symbols=[symbol])
                    )
                else:
                    raise AttributeError("No get_latest_quote method found")
                
                if symbol not in quote:
                    raise TradingAPIError(f"No market data found for symbol: {symbol}")
                
                q = quote[symbol]
                
                out = {
                    "symbol": symbol,
                    "bid_price": float(q.bp) if q.bp else None,
                    "ask_price": float(q.ap) if q.ap else None,
                    "bid_size": int(q.bs) if q.bs else None,
                    "ask_size": int(q.as_) if q.as_ else None,
                    "timestamp": q.timestamp.isoformat() if q.timestamp else None,
                    "raw_response": serialize_cdm_data(q.dict() if hasattr(q, 'dict') else {})
                }
            except (ImportError, AttributeError) as e1:
                logger.debug(f"StockDataClient approach failed: {e1}")
                
                # Approach 2: Try using historical data client with recent bars
                try:
                    from alpaca.data.historical import StockHistoricalDataClient
                    from alpaca.data.requests import StockBarsRequest
                    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
                    from alpaca.data.enums import Sort
                    from datetime import timedelta
                    
                    data_client = StockHistoricalDataClient(
                        api_key=self.api_key,
                        secret_key=self.api_secret
                    )
                    
                    # Get the most recent bar (last 1 minute)
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(minutes=5)
                    
                    bars_request = StockBarsRequest(
                        symbol_or_symbols=[symbol],
                        timeframe=TimeFrame(1, TimeFrameUnit.Minute),
                        start=start_time,
                        end=end_time,
                        limit=1,
                        sort=Sort.Desc
                    )
                    
                    bars = data_client.get_stock_bars(bars_request)
                    
                    if bars and symbol in bars and len(bars[symbol]) > 0:
                        latest_bar = bars[symbol][0]
                        close_price = float(latest_bar.close) if latest_bar.close else None
                        
                        out = {
                            "symbol": symbol,
                            "bid_price": close_price,
                            "ask_price": close_price,
                            "bid_size": None,
                            "ask_size": None,
                            "timestamp": latest_bar.timestamp.isoformat() if latest_bar.timestamp else datetime.utcnow().isoformat(),
                            "raw_response": serialize_cdm_data({
                                "source": "historical_bars",
                                "close": close_price,
                                "open": float(latest_bar.open) if latest_bar.open else None,
                                "high": float(latest_bar.high) if latest_bar.high else None,
                                "low": float(latest_bar.low) if latest_bar.low else None,
                                "volume": int(latest_bar.volume) if latest_bar.volume else None
                            })
                        }
                except Exception as e2:
                    logger.debug(f"Historical bars approach failed: {e2}")
                    
                    # Approach 3: Fallback to TradingClient (limited - only if user has positions)
                    try:
                        from alpaca.trading.client import TradingClient
                        
                        trading_client = TradingClient(
                            api_key=self.api_key,
                            secret_key=self.api_secret
                        )
                        
                        # Try to get position to infer price (limited approach)
                        positions = trading_client.get_all_positions()
                        position = next((p for p in positions if p.symbol == symbol), None)
                        if position:
                            # Use position's current price as estimate
                            current_price = float(position.current_price) if position.current_price else None
                            out = {
                                "symbol": symbol,
                                "bid_price": current_price,
                                "ask_price": current_price,
                                "bid_size": None,
                                "ask_size": None,
                                "timestamp": datetime.utcnow().isoformat(),
                                "raw_response": serialize_cdm_data({"source": "position_data", "price": current_price})
                            }
                    except Exception as e3:
                        logger.debug(f"TradingClient fallback failed: {e3}")
            
            # If all approaches failed, return None values
            if out is None:
                logger.warning(f"All market data approaches failed for {symbol}, returning None values")
                out = {
                    "symbol": symbol,
                    "bid_price": None,
                    "ask_price": None,
                    "bid_size": None,
                    "ask_size": None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "raw_response": serialize_cdm_data({"source": "unavailable", "note": "Market data not available"})
                }
            
            dc.set(cache_key, out, dc.TTL_TRADING_QUOTE, dc.SOURCE_TRADING, dc.KIND_PUNCTUAL, db)
            return out
            
        except Exception as e:
            logger.error(f"Alpaca market data lookup failed: {e}", exc_info=True)
            raise TradingAPIError(f"Failed to get market data: {str(e)}")


class MockTradingAPIService(TradingAPIService):
    """Mock trading API service for testing/development."""
    
    def __init__(self):
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.positions: List[Dict[str, Any]] = []
        self.account_info = {
            "buying_power": 100000.0,
            "cash": 50000.0,
            "equity": 100000.0,
            "portfolio_value": 100000.0,
            "currency": "USD"
        }
    
    def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """Mock order submission."""
        import uuid
        
        order_id = str(uuid.uuid4())
        order = {
            "order_id": order_id,
            "status": "submitted",
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "quantity": float(quantity),
            "filled_quantity": 0.0,
            "average_fill_price": None,
            "price": float(price) if price else None,
            "stop_price": float(stop_price) if stop_price else None,
            "submitted_at": datetime.utcnow().isoformat()
        }
        
        self.orders[order_id] = order
        
        # Simulate immediate fill for market orders
        if order_type == "market":
            order["status"] = "filled"
            order["filled_quantity"] = float(quantity)
            order["average_fill_price"] = 100.0  # Mock price
            order["filled_at"] = datetime.utcnow().isoformat()
        
        return order
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Mock order status."""
        if order_id not in self.orders:
            raise TradingAPIError(f"Order not found: {order_id}")
        return self.orders[order_id]
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Mock order cancellation."""
        if order_id not in self.orders:
            raise TradingAPIError(f"Order not found: {order_id}")
        self.orders[order_id]["status"] = "cancelled"
        self.orders[order_id]["cancelled_at"] = datetime.utcnow().isoformat()
        return {"order_id": order_id, "status": "cancelled"}
    
    def get_account_info(self) -> Dict[str, Any]:
        """Mock account info."""
        return self.account_info
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Mock positions."""
        return self.positions
    
    def get_market_data(self, symbol: str, db: Optional[Any] = None) -> Dict[str, Any]:
        """Mock market data. db is accepted for interface compatibility; no caching."""
        return {
            "symbol": symbol,
            "bid_price": 99.50,
            "ask_price": 100.50,
            "bid_size": 1000,
            "ask_size": 1000,
            "timestamp": datetime.utcnow().isoformat()
        }
