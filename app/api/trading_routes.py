"""Trading API routes for order management and portfolio operations."""

import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User, Order, OrderStatus, OrderSide, OrderType, ManualHolding, Watchlist, PriceAlert
from app.auth.jwt_auth import get_current_user, require_auth
from app.core.permissions import has_permission, PERMISSION_TRADE_VIEW, PERMISSION_TRADE_EXECUTE
from app.services.order_service import OrderService, OrderValidationError
from app.services.trading_api_service import TradingAPIService, TradingAPIError, MockTradingAPIService, AlpacaTradingAPIService
from app.services.commission_service import CommissionService
from app.services.market_data_service import get_historical_data, is_valid_symbol
from app.core.config import settings
from app.utils.rate_limiter import APIRateLimitManager
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trades", tags=["trading"])

# Rate limiter for OHLCV endpoint to prevent excessive autocomplete queries
# Allow 30 requests per minute per user (reasonable for autocomplete)
OHLCV_RATE_LIMITER = APIRateLimitManager.get_limiter(
    api_name="ohlcv_autocomplete",
    max_requests=30,
    time_window_seconds=60  # 1 minute
)


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
    message: Optional[str] = None  # For UI: rejection_reason or status note
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


class ManualHoldingRequest(BaseModel):
    """Request to add a manual holding."""
    symbol: str = Field(..., description="Symbol (e.g. AAPL)")
    quantity: Decimal = Field(..., gt=0, description="Quantity")
    average_cost: Optional[Decimal] = Field(None, description="Average cost per share")
    currency: str = Field("USD", description="Currency")
    notes: Optional[str] = Field(None, description="Optional notes")


class ManualHoldingResponse(BaseModel):
    """Manual holding response."""
    id: int
    symbol: str
    quantity: float
    average_cost: Optional[float] = None
    currency: str
    notes: Optional[str] = None
    created_at: str
    updated_at: str


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
            k = alpaca_key.get_secret_value() if hasattr(alpaca_key, "get_secret_value") else str(alpaca_key)
            s = alpaca_secret.get_secret_value() if hasattr(alpaca_secret, "get_secret_value") else str(alpaca_secret)
            return AlpacaTradingAPIService(
                api_key=k,
                api_secret=s,
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


def _order_to_response(order) -> OrderResponse:
    """Build OrderResponse from Order with message = rejection_reason for UI."""
    d = order.to_dict()
    d["message"] = order.rejection_reason or ""
    return OrderResponse(**d)


# ============================================================================
# Order Management Endpoints
# ============================================================================

@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    order_service: OrderService = Depends(get_order_service)
):
    """Create a new trading order.
    
    Requires authentication and PERMISSION_TRADE_EXECUTE permission.
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
        return _order_to_response(order)
        
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
        
        return [_order_to_response(order) for order in orders]
        
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
        return _order_to_response(order)
        
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TradingAPIError as e:
        logger.warning(f"Failed to update order status from trading API: {e}")
        # Return order anyway, just without updated status
        order = order_service.get_order(order_id)
        if order:
            return _order_to_response(order)
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
        
        return _order_to_response(order)
        
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

def _manual_to_position(m: ManualHolding) -> Dict[str, Any]:
    q = float(m.quantity)
    ac = float(m.average_cost or 0)
    return {
        "symbol": m.symbol,
        "quantity": q,
        "average_price": ac if ac else None,
        "current_price": None,
        "market_value": q * ac if ac else None,
        "unrealized_pl": None,
    }


@router.post("/manual-holdings", response_model=ManualHoldingResponse)
async def add_manual_holding(
    request: ManualHoldingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a manually entered holding (Phase 0: Manual Asset Entry). Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    try:
        m = ManualHolding(
            user_id=current_user.id,
            symbol=request.symbol.upper().strip(),
            quantity=request.quantity,
            average_cost=request.average_cost,
            currency=(request.currency or "USD").upper()[:3],
            notes=request.notes,
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        return ManualHoldingResponse(
            id=m.id,
            symbol=m.symbol,
            quantity=float(m.quantity),
            average_cost=float(m.average_cost) if m.average_cost else None,
            currency=m.currency,
            notes=m.notes,
            created_at=m.created_at.isoformat() if m.created_at else "",
            updated_at=m.updated_at.isoformat() if m.updated_at else "",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add manual holding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manual-holdings", response_model=List[ManualHoldingResponse])
async def list_manual_holdings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List manually entered holdings. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    rows = db.query(ManualHolding).filter(ManualHolding.user_id == current_user.id).order_by(ManualHolding.symbol).all()
    return [
        ManualHoldingResponse(
            id=m.id,
            symbol=m.symbol,
            quantity=float(m.quantity),
            average_cost=float(m.average_cost) if m.average_cost else None,
            currency=m.currency,
            notes=m.notes,
            created_at=m.created_at.isoformat() if m.created_at else "",
            updated_at=m.updated_at.isoformat() if m.updated_at else "",
        )
        for m in rows
    ]


@router.delete("/manual-holdings/{holding_id}", status_code=204)
async def delete_manual_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a manual holding. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    m = db.query(ManualHolding).filter(ManualHolding.id == holding_id, ManualHolding.user_id == current_user.id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Manual holding not found")
    db.delete(m)
    db.commit()
    return None


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trading_api_service: TradingAPIService = Depends(get_trading_api_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Get user portfolio (positions from trading API + manual holdings, and account info).
    
    Requires PERMISSION_TRADE_VIEW permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    try:
        # Get positions from trading API
        try:
            positions = list(trading_api_service.get_positions())
            account_info = trading_api_service.get_account_info()
        except TradingAPIError:
            positions = []
            account_info = {}

        total_value = float(account_info.get("portfolio_value") or 0.0)

        # Add manual holdings as positions and to total value
        manual = db.query(ManualHolding).filter(ManualHolding.user_id == current_user.id).all()
        for m in manual:
            pos = _manual_to_position(m)
            positions.append(pos)
            if pos.get("market_value"):
                total_value += pos["market_value"]

        # Calculate P&L
        total_pnl = 0.0
        unrealized_pnl = 0.0
        for pos in positions:
            if pos.get("unrealized_pl") is not None:
                unrealized_pnl += pos["unrealized_pl"]

        total_pnl = unrealized_pnl
        filled_orders = order_service.get_user_orders(
            user_id=current_user.id,
            status=OrderStatus.FILLED.value,
            limit=1000
        )
        realized_pnl = 0.0

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get market data in dashboard shape (prices, orderBook, recentTrades).

    Supports GET /api/trades/market-data with optional ?symbol= for client compatibility.
    Requires PERMISSION_TRADE_VIEW permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    try:
        data = trading_api_service.get_market_data(symbol.upper(), db=db)
        bid = float(data.get("bid_price") or 0)
        ask = float(data.get("ask_price") or 0)
        price = (bid + ask) / 2 if (bid or ask) else 0.0
        return {
            "prices": [{
                "symbol": data.get("symbol", symbol),
                "price": price,
                "bid": bid if bid > 0 else 0,
                "ask": ask if ask > 0 else 0,
                "change": 0,
                "change_percent": 0,
                "volume": 0,
                "timestamp": data.get("timestamp") or "",
            }],
            "orderBook": [],
            "recentTrades": [],
        }
    except Exception as e:
        logger.warning(f"Failed to get market data for {symbol}: {e}")
        # Return empty data instead of mock data
        return {"prices": [], "orderBook": [], "recentTrades": []}


@router.get("/market-data/{symbol}", response_model=MarketDataResponse)
async def get_market_data(
    symbol: str,
    trading_api_service: TradingAPIService = Depends(get_trading_api_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get market data for a symbol.
    
    Requires PERMISSION_TRADE_VIEW permission.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    try:
        market_data = trading_api_service.get_market_data(symbol.upper(), db=db)
        
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


# ============================================================================
# Watchlists (Trading Phase 4)
# ============================================================================

class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    symbols: List[str] = Field(default_factory=list, description="List of symbols e.g. ['AAPL','MSFT']")


class WatchlistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    symbols: Optional[List[str]] = None


class WatchlistResponse(BaseModel):
    id: int
    name: str
    symbols: List[str]
    created_at: str
    updated_at: str


@router.get("/watchlists", response_model=List[WatchlistResponse])
async def list_watchlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List watchlists for the current user. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    rows = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).order_by(Watchlist.name).all()
    return [
        WatchlistResponse(
            id=w.id,
            name=w.name,
            symbols=w.symbols if isinstance(w.symbols, list) else [],
            created_at=w.created_at.isoformat() if w.created_at else "",
            updated_at=w.updated_at.isoformat() if w.updated_at else "",
        )
        for w in rows
    ]


@router.post("/watchlists", response_model=WatchlistResponse)
async def create_watchlist(
    body: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a watchlist. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    symbols = [s.strip().upper() for s in (body.symbols or []) if s and isinstance(s, str)][:200]
    w = Watchlist(user_id=current_user.id, name=body.name.strip(), symbols=symbols)
    db.add(w)
    db.commit()
    db.refresh(w)
    return WatchlistResponse(
        id=w.id,
        name=w.name,
        symbols=w.symbols or [],
        created_at=w.created_at.isoformat() if w.created_at else "",
        updated_at=w.updated_at.isoformat() if w.updated_at else "",
    )


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
async def get_watchlist(
    watchlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a watchlist by id. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    w = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return WatchlistResponse(
        id=w.id,
        name=w.name,
        symbols=w.symbols or [],
        created_at=w.created_at.isoformat() if w.created_at else "",
        updated_at=w.updated_at.isoformat() if w.updated_at else "",
    )


@router.put("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: int,
    body: WatchlistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a watchlist. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    w = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    if body.name is not None:
        w.name = body.name.strip()
    if body.symbols is not None:
        w.symbols = [s.strip().upper() for s in body.symbols if s and isinstance(s, str)][:200]
    db.commit()
    db.refresh(w)
    return WatchlistResponse(
        id=w.id,
        name=w.name,
        symbols=w.symbols or [],
        created_at=w.created_at.isoformat() if w.created_at else "",
        updated_at=w.updated_at.isoformat() if w.updated_at else "",
    )


@router.delete("/watchlists/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a watchlist. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    w = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    db.delete(w)
    db.commit()
    return None


# ============================================================================
# Price Alerts
# ============================================================================

class PriceAlertCreate(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., 'AAPL')")
    alert_type: str = Field(..., description="Alert type: 'above', 'below', or 'change_percent'")
    target_price: Optional[Decimal] = Field(None, description="Target price for above/below alerts")
    change_percent: Optional[Decimal] = Field(None, description="Percentage change for change_percent alerts")
    notify_email: bool = Field(False, description="Send email notification when triggered")
    notify_in_app: bool = Field(True, description="Show in-app notification when triggered")


class PriceAlertResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    alert_type: str
    target_price: Optional[float] = None
    change_percent: Optional[float] = None
    is_active: bool
    triggered_at: Optional[str] = None
    triggered_price: Optional[float] = None
    notify_email: bool
    notify_in_app: bool
    created_at: str
    updated_at: str


@router.get("/price-alerts", response_model=List[PriceAlertResponse])
async def list_price_alerts(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List price alerts for the current user. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    query = db.query(PriceAlert).filter(PriceAlert.user_id == current_user.id)
    
    if is_active is not None:
        query = query.filter(PriceAlert.is_active == is_active)
    if symbol:
        query = query.filter(PriceAlert.symbol == symbol.upper())
    
    alerts = query.order_by(PriceAlert.created_at.desc()).all()
    
    return [
        PriceAlertResponse(
            id=a.id,
            user_id=a.user_id,
            symbol=a.symbol,
            alert_type=a.alert_type,
            target_price=float(a.target_price) if a.target_price else None,
            change_percent=float(a.change_percent) if a.change_percent else None,
            is_active=a.is_active,
            triggered_at=a.triggered_at.isoformat() if a.triggered_at else None,
            triggered_price=float(a.triggered_price) if a.triggered_price else None,
            notify_email=a.notify_email,
            notify_in_app=a.notify_in_app,
            created_at=a.created_at.isoformat() if a.created_at else "",
            updated_at=a.updated_at.isoformat() if a.updated_at else "",
        )
        for a in alerts
    ]


@router.post("/price-alerts", response_model=PriceAlertResponse)
async def create_price_alert(
    body: PriceAlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a price alert. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    # Validate alert type and required fields
    if body.alert_type not in ["above", "below", "change_percent"]:
        raise HTTPException(status_code=400, detail="alert_type must be 'above', 'below', or 'change_percent'")
    
    if body.alert_type in ["above", "below"] and not body.target_price:
        raise HTTPException(status_code=400, detail="target_price is required for above/below alerts")
    
    if body.alert_type == "change_percent" and not body.change_percent:
        raise HTTPException(status_code=400, detail="change_percent is required for change_percent alerts")
    
    alert = PriceAlert(
        user_id=current_user.id,
        symbol=body.symbol.upper().strip(),
        alert_type=body.alert_type,
        target_price=body.target_price,
        change_percent=body.change_percent,
        notify_email=body.notify_email,
        notify_in_app=body.notify_in_app,
        is_active=True,
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return PriceAlertResponse(
        id=alert.id,
        user_id=alert.user_id,
        symbol=alert.symbol,
        alert_type=alert.alert_type,
        target_price=float(alert.target_price) if alert.target_price else None,
        change_percent=float(alert.change_percent) if alert.change_percent else None,
        is_active=alert.is_active,
        triggered_at=alert.triggered_at.isoformat() if alert.triggered_at else None,
        triggered_price=float(alert.triggered_price) if alert.triggered_price else None,
        notify_email=alert.notify_email,
        notify_in_app=alert.notify_in_app,
        created_at=alert.created_at.isoformat() if alert.created_at else "",
        updated_at=alert.updated_at.isoformat() if alert.updated_at else "",
    )


@router.delete("/price-alerts/{alert_id}", status_code=204)
async def delete_price_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a price alert. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Price alert not found")
    
    db.delete(alert)
    db.commit()
    return None


@router.put("/price-alerts/{alert_id}/toggle", response_model=PriceAlertResponse)
async def toggle_price_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle price alert active status. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Price alert not found")
    
    alert.is_active = not alert.is_active
    db.commit()
    db.refresh(alert)
    
    return PriceAlertResponse(
        id=alert.id,
        user_id=alert.user_id,
        symbol=alert.symbol,
        alert_type=alert.alert_type,
        target_price=float(alert.target_price) if alert.target_price else None,
        change_percent=float(alert.change_percent) if alert.change_percent else None,
        is_active=alert.is_active,
        triggered_at=alert.triggered_at.isoformat() if alert.triggered_at else None,
        triggered_price=float(alert.triggered_price) if alert.triggered_price else None,
        notify_email=alert.notify_email,
        notify_in_app=alert.notify_in_app,
        created_at=alert.created_at.isoformat() if alert.created_at else "",
        updated_at=alert.updated_at.isoformat() if alert.updated_at else "",
    )


@router.get("/ohlcv/{symbol}")
async def get_ohlcv_data(
    symbol: str,
    timeframe: str = Query("1D", description="Timeframe: 1D, 1H, 15Min"),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get OHLCV (candlestick) data for a symbol.
    
    Requires PERMISSION_TRADE_VIEW permission.
    Returns array of {timestamp, open, high, low, close, volume}.
    
    Rate limited to 30 requests per minute to prevent excessive autocomplete queries.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view trades")
    
    # Rate limiting: Check if request can proceed
    if not OHLCV_RATE_LIMITER.acquire(timeout=0):
        wait_time = OHLCV_RATE_LIMITER.get_wait_time()
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please wait {wait_time:.1f} seconds before trying again."
        )
    
    # Validate symbol early to avoid unnecessary processing
    if not is_valid_symbol(symbol):
        logger.debug("Invalid symbol format in OHLCV request: %s", symbol)
        return {"data": [], "symbol": symbol, "timeframe": timeframe, "error": "Invalid symbol format"}
    
    # Normalize symbol (is_valid_symbol already checks format, but we normalize here for consistency)
    symbol = symbol.strip().upper()
    
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        
        df = get_historical_data(symbol, start, end, timeframe, db=db)
        
        if df is None or df.empty:
            return {"data": [], "symbol": symbol, "timeframe": timeframe}
        
        # Convert DataFrame to array format
        data = []
        for idx, row in df.iterrows():
            timestamp = idx
            if hasattr(timestamp, 'to_pydatetime'):
                timestamp = timestamp.to_pydatetime()
            elif hasattr(timestamp, 'timestamp'):
                timestamp = datetime.fromtimestamp(timestamp.timestamp(), tz=timezone.utc)
            
            data.append({
                "timestamp": timestamp.isoformat(),
                "open": float(row.get("Open", 0)),
                "high": float(row.get("High", 0)),
                "low": float(row.get("Low", 0)),
                "close": float(row.get("Close", 0)),
                "volume": float(row.get("Volume", 0)),
            })
        
        return {"data": data, "symbol": symbol, "timeframe": timeframe}
        
    except Exception as e:
        logger.error(f"Failed to get OHLCV data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch OHLCV data: {str(e)}")
