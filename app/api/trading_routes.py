"""Trading API routes for order management and portfolio operations."""

import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User, Order, OrderStatus, OrderSide, OrderType
from app.auth.jwt_auth import get_current_user
from app.core.permissions import has_permission, PERMISSION_TRADE_VIEW, PERMISSION_TRADE_EXECUTE
from app.services.order_service import OrderService, OrderValidationError
from app.services.trading_api_service import TradingAPIService, TradingAPIError, MockTradingAPIService, AlpacaTradingAPIService
from app.services.commission_service import CommissionService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trades", tags=["trading"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateOrderRequest(BaseModel):
    """Request model for creating an order."""
    symbol: str = Field(..., description="Stock symbol (e.g., 'AAPL')")
    side: str = Field(..., description="Order side: 'buy' or 'sell'")
    order_type: str = Field(..., description="Order type: 'market', 'limit', 'stop', 'stop_limit'")
    quantity: Decimal = Field(..., gt=0, description="Number of shares/units")
    price: Optional[Decimal] = Field(None, description="Limit price (required for limit orders)")
    stop_price: Optional[Decimal] = Field(None, description="Stop price (required for stop orders)")
    time_in_force: str = Field("day", description="Time in force: 'day', 'gtc', 'ioc', 'fok'")
    expires_at: Optional[datetime] = Field(None, description="Expiration time for GTC orders")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class OrderResponse(BaseModel):
    """Response model for order details."""
    id: int
    order_id: str
    user_id: int
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: str
    filled_quantity: float
    average_fill_price: Optional[float] = None
    commission: Optional[float] = None
    commission_currency: str
    trading_api: Optional[str] = None
    trading_api_order_id: Optional[str] = None
    time_in_force: str
    expires_at: Optional[str] = None
    submitted_at: Optional[str] = None
    filled_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: str
    updated_at: str


class PortfolioPosition(BaseModel):
    """Portfolio position model."""
    symbol: str
    quantity: float
    average_price: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pl: Optional[float] = None


class PortfolioResponse(BaseModel):
    """Portfolio response model."""
    total_value: float
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    positions: List[PortfolioPosition]
    account_info: Optional[Dict[str, Any]] = None


class MarketDataResponse(BaseModel):
    """Market data response model."""
    symbol: str
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    timestamp: Optional[str] = None


# ============================================================================
# Service Dependencies
# ============================================================================

def get_trading_api_service() -> TradingAPIService:
    """Get trading API service instance."""
    # Check if Alpaca credentials are configured
    alpaca_key = getattr(settings, "ALPACA_API_KEY", None)
    alpaca_secret = getattr(settings, "ALPACA_API_SECRET", None)
    alpaca_base_url = getattr(settings, "ALPACA_BASE_URL", None)
    
    if alpaca_key and alpaca_secret:
        try:
            return AlpacaTradingAPIService(
                api_key=str(alpaca_key),
                api_secret=str(alpaca_secret),
                base_url=alpaca_base_url
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Alpaca API service: {e}. Using mock service.")
            return MockTradingAPIService()
    else:
        logger.info("Alpaca credentials not configured. Using mock trading API service.")
        return MockTradingAPIService()


def get_order_service(
    db: Session = Depends(get_db),
    trading_api_service: TradingAPIService = Depends(get_trading_api_service)
) -> OrderService:
    """Get order service instance."""
    commission_service = CommissionService(db)
    return OrderService(db, trading_api_service, commission_service)


# ============================================================================
# Order Management Endpoints
# ============================================================================

@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service)
):
    """Create a new trading order.
    
    Requires PERMISSION_TRADE_EXECUTE permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_EXECUTE):
        raise HTTPException(status_code=403, detail="Insufficient permissions to execute trades")
    
    try:
        # Create order
        order = order_service.create_order(
            user_id=current_user.id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            time_in_force=request.time_in_force,
            expires_at=request.expires_at,
            metadata=request.metadata
        )
        
        # Submit order to trading API
        order = order_service.submit_order(order.order_id)
        
        return OrderResponse(**order.to_dict())
        
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TradingAPIError as e:
        raise HTTPException(status_code=502, detail=f"Trading API error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


@router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service)
):
    """List orders for the current user.
    
    Requires PERMISSION_TRADE_VIEW permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    try:
        orders = order_service.get_user_orders(
            user_id=current_user.id,
            status=status,
            symbol=symbol,
            limit=limit,
            offset=offset
        )
        
        return [OrderResponse(**order.to_dict()) for order in orders]
        
    except Exception as e:
        logger.error(f"Failed to list orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list orders: {str(e)}")


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service)
):
    """Get order details by ID.
    
    Requires PERMISSION_TRADE_VIEW permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    try:
        order = order_service.get_order(order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check ownership
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update status from trading API
        order = order_service.update_order_status(order_id)
        
        return OrderResponse(**order.to_dict())
        
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TradingAPIError as e:
        logger.warning(f"Failed to update order status from trading API: {e}")
        # Return order anyway, just without updated status
        order = order_service.get_order(order_id)
        if order:
            return OrderResponse(**order.to_dict())
        raise HTTPException(status_code=404, detail="Order not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get order: {str(e)}")


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service)
):
    """Cancel an order.
    
    Requires PERMISSION_TRADE_EXECUTE permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_EXECUTE):
        raise HTTPException(status_code=403, detail="Insufficient permissions to execute trades")
    
    try:
        order = order_service.get_order(order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check ownership
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Cancel order
        order = order_service.cancel_order(order_id)
        
        return OrderResponse(**order.to_dict())
        
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TradingAPIError as e:
        raise HTTPException(status_code=502, detail=f"Trading API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")


# ============================================================================
# Portfolio Endpoints
# ============================================================================

@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trading_api_service: TradingAPIService = Depends(get_trading_api_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Get user portfolio (positions and account info).
    
    Requires PERMISSION_TRADE_VIEW permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    try:
        # Get positions from trading API
        positions = trading_api_service.get_positions()
        
        # Get account info
        account_info = trading_api_service.get_account_info()
        
        # Calculate totals
        total_value = account_info.get("portfolio_value", 0.0)
        cash = account_info.get("cash", 0.0)
        
        # Calculate P&L
        total_pnl = 0.0
        unrealized_pnl = 0.0
        
        for pos in positions:
            if pos.get("unrealized_pl"):
                unrealized_pnl += pos["unrealized_pl"]
        
        total_pnl = unrealized_pnl  # For now, assume no realized P&L
        
        # Get filled orders to calculate realized P&L
        filled_orders = order_service.get_user_orders(
            user_id=current_user.id,
            status=OrderStatus.FILLED.value,
            limit=1000
        )
        
        realized_pnl = 0.0
        # TODO: Calculate realized P&L from filled orders
        
        return PortfolioResponse(
            total_value=total_value,
            total_pnl=total_pnl,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            positions=[PortfolioPosition(**pos) for pos in positions],
            account_info=account_info
        )
        
    except TradingAPIError as e:
        raise HTTPException(status_code=502, detail=f"Trading API error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get portfolio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio: {str(e)}")


# ============================================================================
# Market Data Endpoints
# ============================================================================

@router.get("/market-data")
async def get_market_data_dashboard(
    symbol: str = Query("SPY", description="Symbol for dashboard (default SPY)"),
    trading_api_service: TradingAPIService = Depends(get_trading_api_service),
    current_user: User = Depends(get_current_user)
):
    """Get market data in dashboard shape (prices, orderBook, recentTrades).

    Supports GET /api/trades/market-data with optional ?symbol= for client compatibility.
    Requires PERMISSION_TRADE_VIEW permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    try:
        data = trading_api_service.get_market_data(symbol.upper())
        bid = float(data.get("bid_price") or 0)
        ask = float(data.get("ask_price") or 0)
        price = (bid + ask) / 2 if (bid or ask) else 0.0
        return {
            "prices": [{
                "symbol": data.get("symbol", symbol),
                "price": price,
                "bid": bid or None,
                "ask": ask or None,
                "change": 0,
                "change_percent": 0,
                "volume": 0,
                "timestamp": data.get("timestamp") or "",
            }],
            "orderBook": [],
            "recentTrades": [],
        }
    except Exception:
        return {"prices": [], "orderBook": [], "recentTrades": []}


@router.get("/market-data/{symbol}", response_model=MarketDataResponse)
async def get_market_data(
    symbol: str,
    trading_api_service: TradingAPIService = Depends(get_trading_api_service),
    current_user: User = Depends(get_current_user)
):
    """Get market data for a symbol.
    
    Requires PERMISSION_TRADE_VIEW permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    try:
        market_data = trading_api_service.get_market_data(symbol.upper())
        
        return MarketDataResponse(**market_data)
        
    except TradingAPIError as e:
        raise HTTPException(status_code=502, detail=f"Trading API error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get market data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get market data: {str(e)}")


# ============================================================================
# Order History Endpoint (alias for list_orders)
# ============================================================================

@router.get("/orders/history", response_model=List[OrderResponse])
async def get_order_history(
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service)
):
    """Get order history for the current user.
    
    Alias for GET /api/trades/orders with default filters for completed orders.
    Requires PERMISSION_TRADE_VIEW permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    # Default to showing filled/cancelled orders if no status specified
    if not status:
        # Get all orders and filter client-side, or use a default filter
        pass
    
    return await list_orders(
        status=status,
        symbol=symbol,
        limit=limit,
        offset=offset,
        db=db,
        current_user=current_user,
        order_service=order_service
    )
