"""Order service for order validation, execution, and status tracking."""

import logging
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import Order, OrderStatus, OrderSide, OrderType, User
from app.services.trading_api_service import TradingAPIService, TradingAPIError
from app.services.commission_service import CommissionService
from app.utils.audit import log_audit_action
from app.db.models import AuditAction
from app.utils.json_serializer import serialize_cdm_data

logger = logging.getLogger(__name__)


class OrderValidationError(Exception):
    """Exception raised when order validation fails."""
    pass


class OrderService:
    """Service for managing trading orders."""
    
    def __init__(
        self,
        db: Session,
        trading_api_service: TradingAPIService,
        commission_service: Optional[CommissionService] = None
    ):
        """Initialize order service.
        
        Args:
            db: Database session
            trading_api_service: Trading API service instance
            commission_service: Commission service (optional)
        """
        self.db = db
        self.trading_api_service = trading_api_service
        self.commission_service = commission_service
    
    def validate_order(
        self,
        user_id: int,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """Validate an order before submission.
        
        Args:
            user_id: User ID placing the order
            symbol: Stock symbol
            side: "buy" or "sell"
            order_type: "market", "limit", "stop", "stop_limit"
            quantity: Number of shares/units
            price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            time_in_force: "day", "gtc", "ioc", "fok"
            
        Returns:
            Dictionary with validation result
            
        Raises:
            OrderValidationError: If validation fails
        """
        errors = []
        
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            errors.append("User not found")
        
        # Validate symbol
        if not symbol or len(symbol.strip()) == 0:
            errors.append("Symbol is required")
        
        # Validate side
        if side.lower() not in [OrderSide.BUY.value, OrderSide.SELL.value]:
            errors.append(f"Invalid side: {side}. Must be 'buy' or 'sell'")
        
        # Validate order type
        valid_order_types = [OrderType.MARKET.value, OrderType.LIMIT.value, OrderType.STOP.value, OrderType.STOP_LIMIT.value]
        if order_type.lower() not in valid_order_types:
            errors.append(f"Invalid order type: {order_type}. Must be one of {valid_order_types}")
        
        # Validate quantity
        if quantity <= 0:
            errors.append("Quantity must be greater than 0")
        
        # Validate price for limit orders
        if order_type.lower() in [OrderType.LIMIT.value, OrderType.STOP_LIMIT.value]:
            if not price or price <= 0:
                errors.append(f"Price is required and must be greater than 0 for {order_type} orders")
        
        # Validate stop price for stop orders
        if order_type.lower() in [OrderType.STOP.value, OrderType.STOP_LIMIT.value]:
            if not stop_price or stop_price <= 0:
                errors.append(f"Stop price is required and must be greater than 0 for {order_type} orders")
        
        # Validate time in force
        valid_tif = ["day", "gtc", "ioc", "fok"]
        if time_in_force.lower() not in valid_tif:
            errors.append(f"Invalid time in force: {time_in_force}. Must be one of {valid_tif}")
        
        if errors:
            raise OrderValidationError(f"Order validation failed: {', '.join(errors)}")
        
        return {
            "valid": True,
            "message": "Order validation passed"
        }
    
    def create_order(
        self,
        user_id: int,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "day",
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Order:
        """Create a new order in the database.
        
        Args:
            user_id: User ID placing the order
            symbol: Stock symbol
            side: "buy" or "sell"
            order_type: "market", "limit", "stop", "stop_limit"
            quantity: Number of shares/units
            price: Limit price (optional)
            stop_price: Stop price (optional)
            time_in_force: "day", "gtc", "ioc", "fok"
            expires_at: Expiration time for GTC orders
            metadata: Additional metadata
            
        Returns:
            Created Order object
        """
        # Validate order first
        self.validate_order(
            user_id=user_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force
        )
        
        # Generate unique order ID
        order_id = f"ORD-{uuid.uuid4().hex[:12].upper()}"
        
        # Determine trading API name
        trading_api = "alpaca"  # Default, can be made configurable
        
        # Create order
        order = Order(
            order_id=order_id,
            user_id=user_id,
            symbol=symbol.upper(),
            side=side.lower(),
            order_type=order_type.lower(),
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.PENDING.value,
            time_in_force=time_in_force.lower(),
            expires_at=expires_at,
            trading_api=trading_api,
            order_metadata=metadata or {}
        )
        
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        # Log audit action
        log_audit_action(
            db=self.db,
            action=AuditAction.CREATE,
            target_type="order",
            target_id=order.id,
            user_id=user_id,
            metadata={"order_id": order_id, "symbol": symbol, "side": side, "order_type": order_type}
        )
        
        logger.info(f"Created order {order_id} for user {user_id}: {side} {quantity} {symbol}")
        
        return order
    
    def submit_order(self, order_id: str) -> Order:
        """Submit an order to the trading API.
        
        Args:
            order_id: Internal order ID
            
        Returns:
            Updated Order object
            
        Raises:
            OrderValidationError: If order cannot be submitted
            TradingAPIError: If trading API call fails
        """
        order = self.db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise OrderValidationError(f"Order not found: {order_id}")
        
        if order.status != OrderStatus.PENDING.value:
            raise OrderValidationError(f"Order {order_id} is not in pending status (current: {order.status})")
        
        try:
            # Submit to trading API
            api_response = self.trading_api_service.submit_order(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                stop_price=order.stop_price,
                time_in_force=order.time_in_force
            )
            
            # Update order with API response
            order.trading_api_order_id = api_response.get("order_id")
            order.status = api_response.get("status", OrderStatus.SUBMITTED.value)
            order.filled_quantity = Decimal(str(api_response.get("filled_quantity", 0)))
            # Handle average_fill_price safely - may be None for pending orders
            avg_fill_price = api_response.get("average_fill_price")
            order.average_fill_price = Decimal(str(avg_fill_price)) if avg_fill_price is not None else None
            order.submitted_at = datetime.utcnow()
            # Serialize API response to ensure all UUIDs and other non-JSON types are converted
            order.trading_api_response = serialize_cdm_data(api_response)
            
            # Calculate commission if service available
            if self.commission_service and order.average_fill_price:
                order_value = order.filled_quantity * order.average_fill_price
                commission_result = self.commission_service.calculate_commission(
                    transaction_type="trade_execution",
                    transaction_amount=order_value,
                    transaction_metadata={
                        "symbol": order.symbol,
                        "side": order.side,
                        "order_type": order.order_type,
                        "quantity": float(order.quantity)
                    }
                )
                order.commission = commission_result.get("commission")
                order.commission_currency = commission_result.get("currency", "USD")
            
            # Update status based on fill
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED.value
                order.filled_at = datetime.utcnow()
            elif order.filled_quantity > 0:
                order.status = OrderStatus.PARTIALLY_FILLED.value
            
            self.db.commit()
            self.db.refresh(order)
            
            # Log audit action
            log_audit_action(
                db=self.db,
                action=AuditAction.CREATE,
                target_type="order",
                target_id=order.id,
                user_id=order.user_id,
                metadata={
                    "order_id": order.order_id,
                    "trading_api_order_id": order.trading_api_order_id,
                    "status": order.status,
                    "action": "submitted"
                }
            )
            
            logger.info(f"Submitted order {order_id} to trading API: {order.trading_api_order_id}")
            
            return order
            
        except TradingAPIError as e:
            # Update order with rejection
            order.status = OrderStatus.REJECTED.value
            order.rejection_reason = str(e)
            self.db.commit()
            
            logger.error(f"Order {order_id} rejected by trading API: {e}")
            raise
    
    def update_order_status(self, order_id: str) -> Order:
        """Update order status from trading API.
        
        Args:
            order_id: Internal order ID
            
        Returns:
            Updated Order object
        """
        order = self.db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise OrderValidationError(f"Order not found: {order_id}")
        
        if not order.trading_api_order_id:
            raise OrderValidationError(f"Order {order_id} has not been submitted to trading API")
        
        try:
            # Get status from trading API
            api_status = self.trading_api_service.get_order_status(order.trading_api_order_id)
            
            # Update order fields
            order.status = api_status.get("status", order.status)
            order.filled_quantity = Decimal(str(api_status.get("filled_quantity", 0)))
            order.average_fill_price = Decimal(str(api_status["average_fill_price"])) if api_status.get("average_fill_price") else order.average_fill_price
            
            if api_status.get("filled_at"):
                order.filled_at = datetime.fromisoformat(api_status["filled_at"].replace("Z", "+00:00"))
            if api_status.get("cancelled_at"):
                order.cancelled_at = datetime.fromisoformat(api_status["cancelled_at"].replace("Z", "+00:00"))
            
            # Update status based on fill
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED.value
                if not order.filled_at:
                    order.filled_at = datetime.utcnow()
            elif order.filled_quantity > 0 and order.status == OrderStatus.SUBMITTED.value:
                order.status = OrderStatus.PARTIALLY_FILLED.value
            
            self.db.commit()
            self.db.refresh(order)
            
            logger.debug(f"Updated order {order_id} status: {order.status}")
            
            return order
            
        except TradingAPIError as e:
            logger.error(f"Failed to update order {order_id} status: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> Order:
        """Cancel an order.
        
        Args:
            order_id: Internal order ID
            
        Returns:
            Updated Order object
        """
        order = self.db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise OrderValidationError(f"Order not found: {order_id}")
        
        # Check if order can be cancelled
        cancellable_statuses = [OrderStatus.PENDING.value, OrderStatus.SUBMITTED.value, OrderStatus.PARTIALLY_FILLED.value]
        if order.status not in cancellable_statuses:
            raise OrderValidationError(f"Order {order_id} cannot be cancelled (status: {order.status})")
        
        try:
            # Cancel in trading API if already submitted
            if order.trading_api_order_id:
                self.trading_api_service.cancel_order(order.trading_api_order_id)
            
            # Update order
            order.status = OrderStatus.CANCELLED.value
            order.cancelled_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(order)
            
            # Log audit action
            log_audit_action(
                db=self.db,
                action=AuditAction.DELETE,
                target_type="order",
                target_id=order.id,
                user_id=order.user_id,
                metadata={"order_id": order.order_id, "action": "cancelled"}
            )
            
            logger.info(f"Cancelled order {order_id}")
            
            return order
            
        except TradingAPIError as e:
            logger.error(f"Failed to cancel order {order_id} in trading API: {e}")
            # Still mark as cancelled locally
            order.status = OrderStatus.CANCELLED.value
            order.cancelled_at = datetime.utcnow()
            order.rejection_reason = f"Failed to cancel in trading API: {str(e)}"
            self.db.commit()
            return order
    
    def get_user_orders(
        self,
        user_id: int,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """Get orders for a user.
        
        Args:
            user_id: User ID
            status: Filter by status (optional)
            symbol: Filter by symbol (optional)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of Order objects
        """
        query = self.db.query(Order).filter(Order.user_id == user_id)
        
        if status:
            query = query.filter(Order.status == status.lower())
        
        if symbol:
            query = query.filter(Order.symbol == symbol.upper())
        
        query = query.order_by(Order.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID.
        
        Args:
            order_id: Internal order ID
            
        Returns:
            Order object or None
        """
        return self.db.query(Order).filter(Order.order_id == order_id).first()
