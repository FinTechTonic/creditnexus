# Trading Dashboard & Structured Products Integration Plan: CreditNexus
## Complete Implementation with Bank APIs, Alpaca Markets, and Structured Financial Products

**Status**: Comprehensive Implementation Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 20-24 weeks (expanded for multi-platform aggregation)  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This document provides a **complete implementation plan** for integrating a comprehensive **Universal Portfolio Aggregation Dashboard** into CreditNexus that solves the critical problem of fragmented investments across multiple platforms. The system aggregates investments from banks, trading platforms (Alpaca, Renta Quattro, XTB, Rent A Four), fixed income products, real estate, physical assets (gold, silver), and interest-bearing accounts into a single unified view with real-time price updates, manual asset entry, amortization alerts, and premium risk analysis.

**Key Integration Points:**
- **Multi-Platform Investment Aggregation**: Plaid (banks), Alpaca Markets, Renta Quattro, XTB, Rent A Four, and manual entry for non-listed assets
- **Real-Time Price Updates**: Automatic price updates for listed assets (stocks, gold, ETFs, etc.) via market data APIs
- **Manual Asset Entry**: Support for fixed income products, real estate, physical assets (precious metals), and interest-bearing accounts
- **Amortization & Reminder System**: Automated alerts for fixed income maturity dates, bond amortization schedules, and investment milestones
- **Premium Risk Analysis**: Portfolio diversification analysis, sector/country exposure reporting, and risk recommendations (paid feature)
- **Trading Dashboard**: Real-time portfolio view combining all investment sources with unified P&L tracking
- **Structured Products Engine**: Allow traders to design, price, and issue structured financial products (equity-linked notes, barrier options, etc.)
- **Subscription Tiers**: Free (basic aggregation), Pro (risk analysis), Premium (advanced analytics + structured products)

---

## 1. Bank API Integration Analysis

### 1.1 Available Bank APIs & Aggregators

#### Capital One Direct APIs
**Capabilities:**
- **Account Lookup API**: Retrieve account information for authenticated users
- **Partner Account Summary API**: Provides balances, pending transactions, account summaries
- **Retrieve Consumer Bank Products API**: Fetch available bank products (credit cards, checking, savings)
- **Application Data Sharing API**: OAuth-based transaction and account data sharing (used by Clarity Money)
- **Shop with Rewards API**: Point-of-sale integration for credit card rewards

**Limitations:**
- Primarily read-only (no direct payment initiation)
- Requires OAuth consent flows
- Rate limits and data retention policies vary
- Limited to Capital One customers

**Code Reference Pattern**: Similar to `app/services/x402_payment_service.py` (lines 19-55)

#### Third-Party Aggregators

**Plaid** (Recommended Primary)
- **Coverage**: 12,000+ financial institutions in US, Canada, UK
- **APIs**: 
  - `/link/token/create` - Initialize Link flow
  - `/accounts/get` - Retrieve account balances
  - `/transactions/get` - Fetch transaction history
  - `/identity/get` - Identity verification
  - `/investments/holdings/get` - Investment account data
- **Authentication**: OAuth redirect flow (no credential sharing)
- **Rate Limits**: Tiered (Starter: 100 accounts/month, Growth: 5,000/month)
- **Cost**: Pay-per-account or subscription model

**Yodlee** (Enterprise Alternative)
- **Coverage**: 17,000+ institutions globally
- **APIs**: Similar to Plaid but with enterprise features
- **US Open Banking**: Supports Capital One via Open Banking program
- **Authentication**: OAuth or credential-based (legacy)
- **Rate Limits**: Custom based on contract

**Finicity** (Mastercard)
- **Coverage**: 10,000+ institutions
- **APIs**: Account aggregation, transaction history, identity verification
- **Capital One Partnership**: Direct data sharing agreement
- **Authentication**: Token-based OAuth

**Akoya** (Bank-Direct Alternative)
- **Coverage**: 200+ institutions via direct bank partnerships
- **APIs**: Open Banking compliant (FDX standard)
- **Authentication**: OAuth 2.0 with bank consent screens
- **Advantage**: No credential sharing, direct bank relationships

### 1.2 Bank API Data Model

**Account Data:**
- Account ID, type (checking, savings, credit card, investment)
- Balance (current, available)
- Account holder information
- Institution details

**Transaction Data:**
- Transaction ID, date, amount, description
- Merchant/counterparty information
- Category (food, transportation, etc.)
- Status (pending, posted, cancelled)

**Investment Data (if available):**
- Holdings (stocks, bonds, mutual funds)
- Positions and quantities
- Market values
- Cost basis

### 1.3 Implementation Architecture

**Service Layer Pattern** (following `app/services/x402_payment_service.py`):
```python
# app/services/bank_integration_service.py
class BankIntegrationService:
    """
    Service layer for bank API integration.
    
    Supports multiple aggregators (Plaid, Yodlee, Finicity, Akoya)
    and direct bank APIs (Capital One).
    Uses verified implementations system for user connections.
    """
    
    def __init__(
        self,
        db: Session,
        user_id: Optional[int] = None,
        provider: str = "plaid"  # Default, but will use user's verified implementation
    ):
        self.db = db
        self.user_id = user_id
        self.provider = provider
        self.client = None  # Will be initialized from user connection
    
    def _get_user_connection(self, provider_name: str) -> Dict[str, Any]:
        """Get user's bank connection from verified implementations."""
        from app.db.models import UserImplementationConnection, VerifiedImplementation
        
        if not self.user_id:
            raise ValueError("User ID required for bank connection")
        
        impl = self.db.query(VerifiedImplementation).filter(
            VerifiedImplementation.name == provider_name
        ).first()
        
        if not impl:
            raise ValueError(f"{provider_name} implementation not configured")
        
        connection = self.db.query(UserImplementationConnection).filter(
            UserImplementationConnection.user_id == self.user_id,
            UserImplementationConnection.implementation_id == impl.id,
            UserImplementationConnection.is_active == True
        ).first()
        
        if not connection:
            raise ValueError(f"User has not connected {provider_name} account")
        
        return connection.connection_data
    
    async def create_link_token(self, user_id: int) -> Dict[str, Any]:
        """Create Plaid Link token for OAuth flow."""
        pass
    
    async def exchange_public_token(self, public_token: str) -> str:
        """Exchange public token for access token."""
        pass
    
    async def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Retrieve all accounts for user."""
        pass
    
    async def get_transactions(
        self,
        access_token: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Fetch transaction history."""
        pass
    
    async def get_balances(self, access_token: str) -> List[Dict[str, Any]]:
        """Get current account balances."""
        pass
```

**Database Models** (following `app/db/models.py` patterns):
```python
# app/db/models.py (additions)
class BankConnection(Base):
    """User's bank account connection via aggregator."""
    __tablename__ = "bank_connections"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # "plaid", "yodlee", etc.
    access_token = Column(EncryptedString(500), nullable=False)  # Encrypted
    institution_id = Column(String(255), nullable=False)
    institution_name = Column(String(255), nullable=False)
    accounts = Column(JSONB, nullable=False)  # Array of account metadata
    last_synced_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="bank_connections")

class BankTransaction(Base):
    """Bank transaction records."""
    __tablename__ = "bank_transactions"
    
    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("bank_connections.id"), nullable=False)
    transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    account_id = Column(String(255), nullable=False)
    date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(19, 4), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    merchant = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False)  # "pending", "posted"
    raw_data = Column(JSONB, nullable=True)  # Full provider response
    created_at = Column(DateTime, default=datetime.utcnow)
    
    connection = relationship("BankConnection", back_populates="transactions")
```

---

## 2. Alpaca Markets API Integration

### 2.1 Alpaca API Capabilities

#### Trading API (REST + WebSocket)
**Features:**
- **Order Management**: Market, limit, stop, stop-limit, bracket orders
- **Asset Classes**: Stocks, options (multi-leg strategies), crypto
- **Order Types**: 
  - Single-leg: Buy/sell stocks, options, crypto
  - Multi-leg: Spreads, straddles, condors, iron condors
  - Fractional shares: Trade partial shares
- **Margin & Shorting**: Margin accounts, short selling, stock lending
- **Paper Trading**: Sandbox environment for testing

**Endpoints:**
- `GET /v2/account` - Account information (buying power, equity, positions)
- `GET /v2/positions` - Current positions
- `GET /v2/orders` - Order history and status
- `POST /v2/orders` - Create new order
- `DELETE /v2/orders/{order_id}` - Cancel order
- `GET /v2/positions/{symbol}` - Position for specific symbol
- `GET /v2/assets` - Available assets (stocks, options, crypto)

**WebSocket Streams:**
- `trade_updates` - Real-time order fills, status changes
- `account_updates` - Account balance, buying power changes

#### Market Data API (REST + WebSocket)
**Features:**
- **Real-Time Data**: Live quotes, trades, bars (candles)
- **Historical Data**: Bars, trades, quotes with multiple timeframes
- **Data Tiers**:
  - **Basic (Free)**: IEX exchange only, 15-minute delayed
  - **Algo Trader Plus (Paid)**: All exchanges, real-time, up to 10,000 API calls/min
- **Timeframes**: 1min, 5min, 15min, 1hour, 1day
- **Corporate Actions**: Splits, dividends, mergers

**Endpoints:**
- `GET /v2/stocks/{symbol}/bars` - Historical bars (candles)
- `GET /v2/stocks/{symbol}/trades` - Recent trades
- `GET /v2/stocks/{symbol}/quotes` - Recent quotes
- `GET /v2/stocks/snapshots` - Current snapshots (price, volume)
- `GET /v2/stocks/{symbol}/snapshot` - Snapshot for single symbol

**WebSocket Streams:**
- `bars.{symbol}` - Real-time bar updates
- `trades.{symbol}` - Real-time trade updates
- `quotes.{symbol}` - Real-time quote updates

#### Broker API (For Embedded Brokerage)
**Features:**
- **Account Management**: Create sub-accounts, omnibus accounting
- **Onboarding**: KYC/CIP (Know Your Customer, Customer Identification Program)
- **Funding**: ACH transfers, wire transfers, Plaid integration
- **Statements**: Account statements, trade confirmations
- **Compliance**: Regulatory reporting, tax documents (1099s)

**Use Case**: If CreditNexus wants to offer embedded brokerage services (users trade through CreditNexus, not directly with Alpaca)

#### Connect API (OAuth Integration)
**Features:**
- **OAuth Flow**: Users connect existing Alpaca accounts
- **Scopes**: Read-only, trading, account management
- **Token Management**: Refresh tokens, token revocation

**Use Case**: Users who already have Alpaca accounts can connect them to CreditNexus

### 2.2 Alpaca SDKs & Reference Code

**Official SDKs:**
- **Python**: `alpaca-py` (official), `py-alpaca-api` (community wrapper)
- **Node.js**: `@alpacahq/alpaca-trade-api`
- **Go**: `github.com/alpacahq/alpaca-trade-api-go`
- **C#**: `Alpaca.Markets`

**Reference Implementations:**
- **Open-Source Dashboard**: Django + React trading dashboard with real-time WebSocket updates
- **Alpaca Dashboard (React Native)**: Mobile trading app skeleton
- **Community Projects**: Reddit threads show multi-leg options trading examples

### 2.3 Implementation Architecture

**Service Layer Pattern**:
```python
# app/services/alpaca_service.py
class AlpacaService:
    """
    Service layer for Alpaca Markets API integration.
    
    Handles trading, market data, and account management.
    Uses verified implementations system for user connections.
    """
    
    def __init__(
        self,
        db: Session,
        user_id: Optional[int] = None
    ):
        self.db = db
        self.user_id = user_id
        self.base_url = "https://api.alpaca.markets"  # or paper: https://paper-api.alpaca.markets
        self.data_base_url = "https://data.alpaca.markets"
        self.client = None  # Will be initialized from user connection
    
    def _get_user_connection(self) -> Dict[str, Any]:
        """Get user's Alpaca connection from verified implementations."""
        from app.db.models import UserImplementationConnection, VerifiedImplementation
        
        if not self.user_id:
            raise ValueError("User ID required for Alpaca connection")
        
        impl = self.db.query(VerifiedImplementation).filter(
            VerifiedImplementation.name == "alpaca"
        ).first()
        
        if not impl:
            raise ValueError("Alpaca implementation not configured")
        
        connection = self.db.query(UserImplementationConnection).filter(
            UserImplementationConnection.user_id == self.user_id,
            UserImplementationConnection.implementation_id == impl.id,
            UserImplementationConnection.is_active == True
        ).first()
        
        if not connection:
            raise ValueError("User has not connected Alpaca account")
        
        return connection.connection_data
    
    def _initialize_client(self):
        """Initialize HTTP client from user connection data."""
        if self.client:
            return
        
        connection_data = self._get_user_connection()
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "APCA-API-KEY-ID": connection_data.get("api_key"),
                "APCA-API-SECRET-KEY": connection_data.get("secret_key")
            }
        )
    
    async def get_account(self) -> Dict[str, Any]:
        """Get account information."""
        response = await self.client.get(f"{self.base_url}/v2/account")
        response.raise_for_status()
        return response.json()
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions."""
        response = await self.client.get(f"{self.base_url}/v2/positions")
        response.raise_for_status()
        return response.json()
    
    async def create_order(
        self,
        symbol: str,
        qty: Optional[float] = None,
        notional: Optional[float] = None,  # For fractional shares
        side: str = "buy",  # "buy" or "sell"
        type: str = "market",  # "market", "limit", "stop", "stop_limit"
        time_in_force: str = "day",  # "day", "gtc", "ioc", "fok"
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        order_class: Optional[str] = None,  # "simple", "bracket", "oco", "oto"
        take_profit: Optional[Dict[str, Any]] = None,
        stop_loss: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a trading order."""
        self._initialize_client()
        
        order_data = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "time_in_force": time_in_force
        }
        if qty:
            order_data["qty"] = qty
        if notional:
            order_data["notional"] = notional
        if limit_price:
            order_data["limit_price"] = limit_price
        if stop_price:
            order_data["stop_price"] = stop_price
        if order_class:
            order_data["order_class"] = order_class
        if take_profit:
            order_data["take_profit"] = take_profit
        if stop_loss:
            order_data["stop_loss"] = stop_loss
        
        response = await self.client.post(
            f"{self.base_url}/v2/orders",
            json=order_data
        )
        response.raise_for_status()
        order_result = response.json()
        
        # Apply commission for trade execution
        from app.services.commission_service import CommissionService
        from decimal import Decimal
        
        commission_service = CommissionService(self.db)
        current_price = order_result.get("filled_avg_price") or limit_price or 0
        transaction_amount = Decimal(str(notional or (qty * current_price) if qty else 0))
        
        commission_service.apply_commission(
            transaction_id=order_result.get("id"),
            transaction_type="trade_execution",
            transaction_amount=transaction_amount,
            payer_id=self.user_id,
            transaction_metadata={
                "symbol": symbol,
                "order_type": type,
                "side": side
            }
        )
        
        return order_result
    
    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "1Day",  # "1Min", "5Min", "15Min", "1Hour", "1Day"
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical market data (bars/candles)."""
        params = {
            "timeframe": timeframe,
            "limit": limit
        }
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()
        
        response = await self.client.get(
            f"{self.data_base_url}/v2/stocks/{symbol}/bars",
            params=params
        )
        response.raise_for_status()
        return response.json().get("bars", [])
    
    async def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        """Get current market snapshot (price, volume, etc.)."""
        response = await self.client.get(
            f"{self.data_base_url}/v2/stocks/{symbol}/snapshot"
        )
        response.raise_for_status()
        return response.json()
```

**Database Models**:
```python
# app/db/models.py (additions)
class AlpacaConnection(Base):
    """User's Alpaca account connection."""
    __tablename__ = "alpaca_connections"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(String(255), unique=True, nullable=False, index=True)
    account_type = Column(String(20), nullable=False)  # "paper" or "live"
    access_token = Column(EncryptedString(500), nullable=False)  # Encrypted
    refresh_token = Column(EncryptedString(500), nullable=True)  # For OAuth
    is_active = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="alpaca_connections")
    positions = relationship("TradingPosition", back_populates="connection")
    orders = relationship("TradingOrder", back_populates="connection")

class TradingPosition(Base):
    """Trading positions (stocks, options, crypto)."""
    __tablename__ = "trading_positions"
    
    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("alpaca_connections.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)  # "stock", "option", "crypto"
    qty = Column(Numeric(19, 4), nullable=False)
    avg_entry_price = Column(Numeric(19, 4), nullable=False)
    current_price = Column(Numeric(19, 4), nullable=True)
    market_value = Column(Numeric(19, 4), nullable=True)
    cost_basis = Column(Numeric(19, 4), nullable=False)
    unrealized_pl = Column(Numeric(19, 4), nullable=True)
    unrealized_plpc = Column(Numeric(10, 4), nullable=True)  # P&L percentage
    side = Column(String(10), nullable=False)  # "long" or "short"
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    connection = relationship("AlpacaConnection", back_populates="positions")

class TradingOrder(Base):
    """Trading orders (pending, filled, cancelled)."""
    __tablename__ = "trading_orders"
    
    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("alpaca_connections.id"), nullable=False)
    order_id = Column(String(255), unique=True, nullable=False, index=True)  # Alpaca order ID
    symbol = Column(String(20), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # "buy" or "sell"
    order_type = Column(String(20), nullable=False)  # "market", "limit", "stop", etc.
    qty = Column(Numeric(19, 4), nullable=False)
    filled_qty = Column(Numeric(19, 4), default=0)
    limit_price = Column(Numeric(19, 4), nullable=True)
    stop_price = Column(Numeric(19, 4), nullable=True)
    status = Column(String(20), nullable=False)  # "new", "filled", "partially_filled", "cancelled", "expired"
    time_in_force = Column(String(10), nullable=False)  # "day", "gtc", "ioc", "fok"
    submitted_at = Column(DateTime, nullable=False)
    filled_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    raw_data = Column(JSONB, nullable=True)  # Full Alpaca response
    created_at = Column(DateTime, default=datetime.utcnow)
    
    connection = relationship("AlpacaConnection", back_populates="orders")
```

---

## 3. Multi-Platform Investment Aggregation

### 3.1 Problem Statement

Investors typically have investments spread across multiple platforms:
- **Renta Quattro**: Shares/stocks
- **XTB**: Gold derivatives, CFDs, forex
- **Rent A Four**: Mutual funds, ETFs
- **Fixed Income Platforms**: Bonds, certificates of deposit (CDs), structured notes
- **Real Estate**: Property investments, REITs
- **Physical Assets**: Gold, silver, collectibles
- **Interest-Bearing Accounts**: High-yield savings, money market accounts

**Solution**: Universal portfolio aggregation that connects to all platforms and allows manual entry for non-listed assets.

### 3.2 Supported Investment Platforms

#### Renta Quattro Integration
**Platform Type**: Stock trading platform
**Integration Method**: 
- **Option A**: API integration (if available)
- **Option B**: CSV import (manual export/import)
- **Option C**: Screen scraping (last resort, requires user credentials)

**Data to Sync**:
- Stock positions (symbol, quantity, purchase price)
- Current market prices
- Transaction history
- Dividends received

**Implementation**:
```python
# app/services/renta_quattro_service.py
class RentaQuattroService:
    """Service for Renta Quattro integration."""
    
    async def sync_positions(self, user_id: int, credentials: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Sync stock positions from Renta Quattro."""
        # If API available: use API
        # If CSV import: parse CSV file
        # If screen scraping: use Selenium/Playwright
        pass
```

#### XTB Integration
**Platform Type**: CFD/Forex/Gold derivatives broker
**Integration Method**: 
- **XTB API**: Official API for account data (if available)
- **CSV Export**: Manual export of positions and transactions

**Data to Sync**:
- Gold derivative positions
- Forex positions
- CFD positions
- Account balance
- P&L history

#### Rent A Four Integration
**Platform Type**: Mutual funds, ETFs platform
**Integration Method**:
- **API Integration**: If available
- **CSV Import**: Fund holdings export

**Data to Sync**:
- Fund positions (fund name, ISIN, units)
- NAV (Net Asset Value) updates
- Distribution history

### 3.3 Manual Asset Entry System

**Use Case**: For assets that cannot be automatically synced (fixed income, real estate, physical assets, interest-bearing accounts).

**Asset Types**:
1. **Fixed Income Products**: Bonds, CDs, structured notes
2. **Real Estate**: Properties, REITs
3. **Physical Assets**: Gold, silver, collectibles
4. **Interest-Bearing Accounts**: Savings accounts, money market accounts

**Database Models**:
```python
# app/db/models.py (additions)
class ManualAsset(Base):
    """Manually entered investment asset."""
    __tablename__ = "manual_assets"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False)  # "fixed_income", "real_estate", "physical", "interest_account"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Valuation
    purchase_price = Column(Numeric(19, 4), nullable=False)
    current_value = Column(Numeric(19, 4), nullable=True)  # For manual updates
    quantity = Column(Numeric(19, 4), nullable=True)  # For physical assets (e.g., ounces of gold)
    unit = Column(String(20), nullable=True)  # "oz", "kg", "shares", etc.
    
    # Fixed Income Specific
    maturity_date = Column(Date, nullable=True)  # For bonds, CDs
    interest_rate = Column(Numeric(10, 4), nullable=True)  # Annual interest rate
    payment_frequency = Column(String(20), nullable=True)  # "monthly", "quarterly", "annually", "at_maturity"
    amortization_schedule = Column(JSONB, nullable=True)  # Payment schedule
    
    # Real Estate Specific
    property_address = Column(String(500), nullable=True)
    property_type = Column(String(50), nullable=True)  # "residential", "commercial", "land"
    rental_income = Column(Numeric(19, 4), nullable=True)  # Monthly/annual rental income
    
    # Physical Asset Specific
    asset_category = Column(String(50), nullable=True)  # "precious_metal", "collectible", "art"
    storage_location = Column(String(255), nullable=True)
    
    # Interest Account Specific
    account_number = Column(EncryptedString(255), nullable=True)  # Encrypted
    institution_name = Column(String(255), nullable=True)
    interest_rate_apy = Column(Numeric(10, 4), nullable=True)
    
    # Metadata
    purchase_date = Column(Date, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True)  # For categorization
    
    # Price Updates
    auto_update_price = Column(Boolean, default=False)  # For assets with market prices (e.g., gold)
    price_source = Column(String(50), nullable=True)  # "market_data", "manual", "appraisal"
    last_price_update = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="manual_assets")
    price_history = relationship("AssetPriceHistory", back_populates="asset")
    alerts = relationship("AssetAlert", back_populates="asset")

class AssetPriceHistory(Base):
    """Historical price data for manual assets."""
    __tablename__ = "asset_price_history"
    
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("manual_assets.id"), nullable=False)
    price = Column(Numeric(19, 4), nullable=False)
    date = Column(Date, nullable=False, index=True)
    source = Column(String(50), nullable=False)  # "market_data", "manual", "appraisal"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    asset = relationship("ManualAsset", back_populates="price_history")

class AssetAlert(Base):
    """Alerts for manual assets (maturity dates, price thresholds, etc.)."""
    __tablename__ = "asset_alerts"
    
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("manual_assets.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # "maturity", "price_threshold", "amortization_payment"
    trigger_date = Column(Date, nullable=True)  # For date-based alerts
    trigger_price = Column(Numeric(19, 4), nullable=True)  # For price-based alerts
    message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notified = Column(Boolean, default=False, nullable=False)
    notified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    asset = relationship("ManualAsset", back_populates="alerts")
```

### 3.4 Real-Time Price Updates for Manual Assets

**Supported Assets with Market Prices**:
- **Gold/Silver**: Fetch from commodity APIs (e.g., Alpha Vantage, Yahoo Finance, Metals API)
- **REITs**: Fetch stock prices if publicly traded
- **ETFs**: Fetch NAV from fund provider APIs

**Implementation**:
```python
# app/services/asset_price_service.py
class AssetPriceService:
    """Service for fetching real-time prices for manual assets."""
    
    async def update_gold_price(self, asset: ManualAsset) -> Decimal:
        """Fetch current gold price from commodity API."""
        # Use Alpha Vantage, Yahoo Finance, or Metals API
        # Update asset.current_value and asset.last_price_update
        pass
    
    async def update_silver_price(self, asset: ManualAsset) -> Decimal:
        """Fetch current silver price."""
        pass
    
    async def update_reit_price(self, asset: ManualAsset) -> Decimal:
        """Fetch REIT stock price if publicly traded."""
        pass
    
    async def update_all_auto_update_assets(self, user_id: int) -> Dict[str, Any]:
        """Update all assets with auto_update_price=True."""
        pass
```

### 3.5 Amortization & Reminder System

**Use Case**: Fixed income products (bonds, CDs) have maturity dates and periodic interest payments. Users need alerts for:
- Approaching maturity dates
- Upcoming interest payments
- Amortization schedule milestones

**Implementation Pattern** (following `app/services/filing_notification_service.py`):
```python
# app/services/asset_amortization_service.py
class AssetAmortizationService:
    """Service for managing amortization schedules and alerts."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_amortization_schedule(
        self,
        principal: Decimal,
        interest_rate: Decimal,
        maturity_date: date,
        payment_frequency: str
    ) -> List[Dict[str, Any]]:
        """Generate amortization schedule for fixed income product."""
        # Calculate payment dates and amounts
        # Return list of {date, principal_payment, interest_payment, remaining_balance}
        pass
    
    def check_upcoming_payments(
        self,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Check for upcoming interest payments and maturity dates."""
        # Query ManualAsset for fixed_income assets
        # Check amortization_schedule for upcoming payments
        # Return alerts for payments due within days_ahead
        pass
    
    def send_maturity_alert(
        self,
        asset: ManualAsset,
        days_until: int
    ) -> Dict[str, Any]:
        """Send alert for approaching maturity date."""
        # Similar to FilingNotificationService.send_deadline_alert()
        # Send email/in-app notification
        pass
```

**Background Task** (following `app/services/background_tasks.py` pattern):
```python
# app/services/background_tasks.py (additions)
async def monitor_asset_amortization() -> Dict[str, Any]:
    """Background task to monitor asset amortization schedules."""
    from app.services.asset_amortization_service import AssetAmortizationService
    from app.db import get_db
    
    db = next(get_db())
    service = AssetAmortizationService(db)
    
    # Check for upcoming payments (7 days, 3 days, 1 day before)
    alerts = service.check_upcoming_payments(days_ahead=7)
    
    # Send notifications
    for alert in alerts:
        service.send_maturity_alert(alert['asset'], alert['days_until'])
    
    return {"status": "success", "alerts_sent": len(alerts)}
```

---

## 4. Premium Risk Analysis Engine

### 4.1 Portfolio Diversification Analysis

**Premium Feature**: Available to Pro and Premium subscription tiers.

**Analysis Dimensions**:
1. **Asset Class Diversification**: Stocks, bonds, real estate, commodities, cash
2. **Sector Exposure**: Technology, healthcare, finance, energy, etc.
3. **Geographic Exposure**: US, Europe, Asia, Emerging Markets
4. **Currency Exposure**: USD, EUR, GBP, etc.
5. **Risk Metrics**: Sharpe ratio, beta, VaR (Value at Risk), correlation analysis

**Implementation**:
```python
# app/services/portfolio_risk_service.py
class PortfolioRiskService:
    """Service for portfolio risk and diversification analysis."""
    
    def __init__(self, db: Session):
        self.db = db
        self.alpaca_service = AlpacaService(...)
        self.asset_price_service = AssetPriceService()
    
    def analyze_diversification(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Analyze portfolio diversification across multiple dimensions.
        
        Returns:
        {
            "asset_class_allocation": {
                "stocks": 0.60,
                "bonds": 0.20,
                "real_estate": 0.10,
                "commodities": 0.05,
                "cash": 0.05
            },
            "sector_exposure": {
                "technology": 0.35,
                "healthcare": 0.15,
                "finance": 0.20,
                ...
            },
            "country_exposure": {
                "US": 0.70,
                "UK": 0.15,
                "Germany": 0.10,
                ...
            },
            "currency_exposure": {
                "USD": 0.75,
                "EUR": 0.20,
                "GBP": 0.05
            },
            "risk_metrics": {
                "sharpe_ratio": 1.2,
                "beta": 0.95,
                "var_95": 0.05,
                "max_drawdown": 0.15
            },
            "recommendations": [
                {
                    "type": "overexposure",
                    "dimension": "country",
                    "value": "US",
                    "current_allocation": 0.70,
                    "recommended_max": 0.50,
                    "message": "High exposure to US market. Consider diversifying to international markets."
                },
                {
                    "type": "underexposure",
                    "dimension": "asset_class",
                    "value": "bonds",
                    "current_allocation": 0.20,
                    "recommended_min": 0.30,
                    "message": "Low bond allocation. Consider increasing fixed income for stability."
                }
            ]
        }
        """
        # Aggregate all investments (bank, trading, manual assets)
        portfolio = self._aggregate_portfolio(user_id)
        
        # Calculate allocations
        asset_class_allocation = self._calculate_asset_class_allocation(portfolio)
        sector_exposure = self._calculate_sector_exposure(portfolio)
        country_exposure = self._calculate_country_exposure(portfolio)
        currency_exposure = self._calculate_currency_exposure(portfolio)
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(portfolio)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            asset_class_allocation,
            sector_exposure,
            country_exposure,
            currency_exposure
        )
        
        return {
            "asset_class_allocation": asset_class_allocation,
            "sector_exposure": sector_exposure,
            "country_exposure": country_exposure,
            "currency_exposure": currency_exposure,
            "risk_metrics": risk_metrics,
            "recommendations": recommendations
        }
    
    def _calculate_sector_exposure(
        self,
        portfolio: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate sector exposure from stock positions."""
        # For each stock position:
        # 1. Fetch sector from market data API (Alpaca, Yahoo Finance)
        # 2. Calculate sector allocation as % of total portfolio
        pass
    
    def _calculate_country_exposure(
        self,
        portfolio: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate country exposure."""
        # For stocks: Use company headquarters country
        # For bonds: Use issuer country
        # For real estate: Use property location
        # For funds: Use fund domicile or underlying asset countries
        pass
    
    def _generate_recommendations(
        self,
        asset_class_allocation: Dict[str, float],
        sector_exposure: Dict[str, float],
        country_exposure: Dict[str, float],
        currency_exposure: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Generate diversification recommendations."""
        recommendations = []
        
        # Check for overexposure (e.g., >50% in single country)
        for country, allocation in country_exposure.items():
            if allocation > 0.50:
                recommendations.append({
                    "type": "overexposure",
                    "dimension": "country",
                    "value": country,
                    "current_allocation": allocation,
                    "recommended_max": 0.50,
                    "message": f"High exposure to {country} market ({allocation*100:.1f}%). Consider diversifying to international markets."
                })
        
        # Check for sector concentration
        for sector, allocation in sector_exposure.items():
            if allocation > 0.30:
                recommendations.append({
                    "type": "overexposure",
                    "dimension": "sector",
                    "value": sector,
                    "current_allocation": allocation,
                    "recommended_max": 0.30,
                    "message": f"High concentration in {sector} sector ({allocation*100:.1f}%). Consider diversifying across sectors."
                })
        
        # Check for asset class imbalance
        if asset_class_allocation.get("stocks", 0) > 0.70:
            recommendations.append({
                "type": "overexposure",
                "dimension": "asset_class",
                "value": "stocks",
                "current_allocation": asset_class_allocation["stocks"],
                "recommended_max": 0.70,
                "message": "High equity allocation. Consider adding bonds for stability."
            })
        
        return recommendations
```

### 4.2 Subscription Tiers

**Free Tier**:
- Basic portfolio aggregation (view all investments)
- Manual asset entry
- Real-time price updates (where available)
- Basic amortization alerts (maturity dates)

**Pro Tier** ($9.99/month):
- All Free features
- **Portfolio Risk Analysis**: Diversification analysis, sector/country exposure
- **Risk Recommendations**: Automated suggestions for portfolio improvement
- **Advanced Alerts**: Price thresholds, custom reminders
- **Export Reports**: PDF/CSV export of portfolio analysis

**Premium Tier** ($29.99/month):
- All Pro features
- **Advanced Risk Metrics**: Sharpe ratio, beta, VaR, correlation analysis
- **Structured Products Access**: Create and issue structured products
- **Backtesting Tools**: Test investment strategies
- **Priority Support**: Email/chat support
- **API Access**: Programmatic access to portfolio data

**Implementation** (see `ELECTRON_REFACTORING_PLAN.md` for full implementation):
```python
# app/services/subscription_service.py
class SubscriptionService:
    """Service for managing subscription tiers."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_tier(self, user_id: int) -> str:
        """Get user's current subscription tier."""
        # Implementation in ELECTRON_REFACTORING_PLAN.md
        # Supports: free, pro (pay-as-you-go), premium, lifetime
        pass
    
    def check_feature_access(self, user_id: int, feature: str) -> bool:
        """Check if user has access to premium feature."""
        tier = self.get_user_tier(user_id)
        
        feature_tiers = {
            "trading": ["pro", "premium", "lifetime"],
            "risk_analysis": ["pro", "premium", "lifetime"],
            "advanced_risk_metrics": ["premium", "lifetime"],
            "structured_products": ["premium", "lifetime"],
            "backtesting": ["premium", "lifetime"],
            "api_access": ["premium", "lifetime"]
        }
        
        required_tiers = feature_tiers.get(feature, [])
        return tier in required_tiers
```

**Note**: Risk analysis endpoints must check subscription tier. Example:
```python
@router.get("/risk-analysis")
async def get_risk_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    tier = subscription_service.get_user_tier(current_user.id)
    if tier not in ['pro', 'premium', 'lifetime']:
        raise HTTPException(
            status_code=403,
            detail="Pro subscription required for risk analysis"
        )
    # ... risk analysis implementation
```

---

## 5. Trading Dashboard Implementation

### 3.1 Dashboard Architecture

**Frontend Components** (integrated into UnifiedDashboard):
- **TradingDashboard**: Trading interface with order entry, positions, watchlists
  - Location: `client/src/components/dashboard-tabs/TradingDashboard.tsx`
  - Tab ID: `trading`
  - Required Permission: `PERMISSION_TRADING_VIEW`
  - Subscription Tier: `pro` (Pro tier required)
- **PortfolioDashboard**: Portfolio aggregation view
  - Location: `client/src/components/dashboard-tabs/PortfolioDashboard.tsx`
  - Tab ID: `portfolio`
  - Required Permission: `PERMISSION_PORTFOLIO_VIEW`
  - Subscription Tier: `free` (Free tier can view basic portfolio)
- **Market Data Charts**: Real-time price charts using TradingView or Recharts
- **Order Entry Panel**: Create and manage orders
- **Position Monitor**: Real-time position tracking with P&L
- **Watchlists**: Custom symbol lists with price alerts
- **Transaction History**: Bank transactions + trading history

**Note**: Both components are integrated into UnifiedDashboard. See `PLAN_INTEGRATION_ADDENDUM.md` for integration details.

**Backend APIs** (following `app/api/routes.py` patterns):
- `/api/trading/account` - Get account summary
- `/api/trading/positions` - Get all positions
- `/api/trading/orders` - List/create/cancel orders
- `/api/trading/market-data/{symbol}` - Get market data
- `/api/banking/accounts` - Get bank accounts
- `/api/banking/transactions` - Get transactions
- `/api/portfolio/overview` - Combined portfolio view

### 3.2 Real-Time Data Streaming

**WebSocket Integration** (following `app/api/websocket_routes.py`):
- Market data streams (prices, trades, quotes)
- Order status updates (fills, cancellations)
- Account updates (buying power, equity changes)
- Position updates (P&L changes)

**Implementation Pattern**:
```python
# app/api/trading_websocket_routes.py
from fastapi import WebSocket, WebSocketDisconnect
from app.services.alpaca_service import AlpacaService

@router.websocket("/ws/trading/{user_id}")
async def trading_websocket(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time trading data."""
    await websocket.accept()
    
    # Subscribe to Alpaca WebSocket streams
    alpaca_ws = await connect_alpaca_websocket(user_id)
    
    try:
        while True:
            # Forward Alpaca updates to client
            data = await alpaca_ws.receive()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        await alpaca_ws.close()
```

### 3.3 Frontend Dashboard Component

**File**: `client/src/components/dashboard-tabs/TradingDashboard.tsx`

**Note**: This component is integrated into the UnifiedDashboard as a tab. See `ELECTRON_REFACTORING_PLAN.md` for unified dashboard architecture.

```typescript
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth, fetchWithAuth } from '@/context/AuthContext';
import { useFDC3 } from '@/hooks/useFDC3';
import { TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react';

interface PortfolioOverview {
  total_equity: number;
  bank_balances: number;
  trading_equity: number;
  unrealized_pl: number;
  realized_pl: number;
  buying_power: number;
}

interface Position {
  symbol: string;
  qty: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_plpc: number;
}

export function TradingDashboard() {
  const { user } = useAuth();
  const { broadcast } = useFDC3();
  const [portfolio, setPortfolio] = useState<PortfolioOverview | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [portfolioRes, positionsRes] = await Promise.all([
          fetchWithAuth('/api/portfolio/overview'),
          fetchWithAuth('/api/trading/positions')
        ]);
        
        const portfolioData = await portfolioRes.json();
        const positionsData = await positionsRes.json();
        
        setPortfolio(portfolioData);
        setPositions(positionsData.positions || []);
      } catch (error) {
        console.error('Error fetching portfolio:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
    
    // Set up WebSocket for real-time updates
    const ws = new WebSocket(`ws://localhost:8000/ws/trading/${user?.id}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Update positions/portfolio in real-time
      handleRealtimeUpdate(data);
    };
    
    return () => ws.close();
  }, [user]);
  
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Trading Dashboard</h1>
      
      {/* Portfolio Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Total Equity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${portfolio?.total_equity.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Unrealized P&L</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              (portfolio?.unrealized_pl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              ${portfolio?.unrealized_pl.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Buying Power</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${portfolio?.buying_power.toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Positions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Quantity</th>
                <th>Avg Price</th>
                <th>Current Price</th>
                <th>Market Value</th>
                <th>P&L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map(pos => (
                <tr key={pos.symbol}>
                  <td>{pos.symbol}</td>
                  <td>{pos.qty}</td>
                  <td>${pos.avg_price.toFixed(2)}</td>
                  <td>${pos.current_price.toFixed(2)}</td>
                  <td>${pos.market_value.toLocaleString()}</td>
                  <td className={pos.unrealized_pl >= 0 ? 'text-green-600' : 'text-red-600'}>
                    ${pos.unrealized_pl.toFixed(2)} ({pos.unrealized_plpc.toFixed(2)}%)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## 4. Structured Financial Products Engine

### 4.1 Structured Products Overview

**What are Structured Products?**
- Hybrid securities combining traditional assets (stocks, bonds) with derivatives (options, swaps)
- Custom payoff profiles: barrier options, buffer notes, principal-protected notes, range accruals
- Used for: yield enhancement, principal protection, market participation with downside protection

**CreditNexus Use Case:**
- Equities traders design structured products using underlying stocks/indices
- Products can be:
  - **Equity-Linked Notes**: Bond + call option on stock/index
  - **Barrier Options**: Knock-in/knock-out options
  - **Buffer Notes**: Principal protection with capped upside
  - **Range Accruals**: Payoff based on asset staying in range

### 4.2 Structured Products Architecture

**Product Definition Engine**:
```python
# app/services/structured_products_service.py
class StructuredProductsService:
    """
    Service for creating, pricing, and managing structured financial products.
    """
    
    def __init__(self, db: Session, alpaca_service: AlpacaService):
        self.db = db
        self.alpaca_service = alpaca_service
    
    def create_product_template(
        self,
        name: str,
        product_type: str,  # "equity_linked_note", "barrier_option", "buffer_note"
        underlying_symbol: str,
        payoff_formula: Dict[str, Any],  # JSON structure defining payoff
        maturity_days: int,
        principal: Decimal,
        fees: Decimal
    ) -> Dict[str, Any]:
        """Create a structured product template."""
        pass
    
    def price_product(
        self,
        product_template_id: int,
        current_market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Price a structured product using:
        - Black-Scholes for options components
        - Monte Carlo simulation for complex payoffs
        - Market data from Alpaca
        """
        pass
    
    def replicate_product(
        self,
        product_id: int,
        quantity: int
    ) -> Dict[str, Any]:
        """
        Replicate structured product using underlying trades.
        
        Example: Equity-linked note = Buy bond + Buy call option
        Executes trades via Alpaca API.
        """
        pass
    
    def issue_product(
        self,
        product_template_id: int,
        issuer_user_id: int,
        investor_user_ids: List[int],
        total_notional: Decimal
    ) -> Dict[str, Any]:
        """
        Issue structured product to investors.
        
        Steps:
        1. Create product instance
        2. Collect subscriptions from investors
        3. Replicate product via Alpaca trades
        4. Manage lifecycle (monitoring, settlement)
        """
        pass
```

**Database Models**:
```python
# app/db/models.py (additions)
class StructuredProductTemplate(Base):
    """Template for structured financial products."""
    __tablename__ = "structured_product_templates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    product_type = Column(String(50), nullable=False)
    underlying_symbol = Column(String(20), nullable=False)
    payoff_formula = Column(JSONB, nullable=False)  # Payoff definition
    maturity_days = Column(Integer, nullable=False)
    principal = Column(Numeric(19, 4), nullable=False)
    fees = Column(Numeric(19, 4), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    creator = relationship("User")
    instances = relationship("StructuredProductInstance", back_populates="template")

class StructuredProductInstance(Base):
    """Issued instance of a structured product."""
    __tablename__ = "structured_product_instances"
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("structured_product_templates.id"), nullable=False)
    issuer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_notional = Column(Numeric(19, 4), nullable=False)
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False)  # "active", "matured", "cancelled"
    replication_trades = Column(JSONB, nullable=True)  # Alpaca order IDs
    current_value = Column(Numeric(19, 4), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    template = relationship("StructuredProductTemplate", back_populates="instances")
    issuer = relationship("User", foreign_keys=[issuer_user_id])
    subscriptions = relationship("ProductSubscription", back_populates="instance")

class ProductSubscription(Base):
    """Investor subscription to structured product."""
    __tablename__ = "product_subscriptions"
    
    id = Column(Integer, primary_key=True)
    instance_id = Column(Integer, ForeignKey("structured_product_instances.id"), nullable=False)
    investor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notional = Column(Numeric(19, 4), nullable=False)
    subscription_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False)  # "pending", "confirmed", "settled"
    payout = Column(Numeric(19, 4), nullable=True)  # Final payout at maturity
    created_at = Column(DateTime, default=datetime.utcnow)
    
    instance = relationship("StructuredProductInstance", back_populates="subscriptions")
    investor = relationship("User", foreign_keys=[investor_user_id])
```

### 4.3 Pricing Engine

**Pricing Methods**:
- **Black-Scholes**: For vanilla options components
- **Monte Carlo Simulation**: For complex payoffs (barriers, path-dependent)
- **Binomial Tree**: For American-style options
- **Numerical Methods**: Finite difference, PDE solvers

**Integration with Market Data**:
- Fetch current prices from Alpaca Market Data API
- Fetch implied volatilities (if available)
- Fetch risk-free rate (from Treasury data or config)

**Implementation**:
```python
# app/services/pricing_engine.py
class PricingEngine:
    """
    Pricing engine for structured products.
    
    Uses quantitative finance libraries (QuantLib, scipy, numpy)
    for option pricing and Monte Carlo simulation.
    """
    
    def price_equity_linked_note(
        self,
        underlying_price: float,
        strike: float,
        volatility: float,
        risk_free_rate: float,
        time_to_maturity: float,
        principal: float
    ) -> float:
        """Price equity-linked note = Bond + Call Option."""
        # Bond component (discounted principal)
        bond_value = principal * math.exp(-risk_free_rate * time_to_maturity)
        
        # Call option component (Black-Scholes)
        call_value = self.black_scholes_call(
            underlying_price, strike, volatility, risk_free_rate, time_to_maturity
        )
        
        return bond_value + call_value
    
    def price_barrier_option(
        self,
        underlying_price: float,
        strike: float,
        barrier: float,
        volatility: float,
        risk_free_rate: float,
        time_to_maturity: float,
        barrier_type: str  # "knock_in" or "knock_out"
    ) -> float:
        """Price barrier option using Monte Carlo or analytical formula."""
        # Use Monte Carlo for path-dependent options
        return self.monte_carlo_barrier_option(
            underlying_price, strike, barrier, volatility,
            risk_free_rate, time_to_maturity, barrier_type
        )
```

---

## 5. Permissioned User Flows & Roles

### 5.1 User Roles

**Retail Trader**:
- Connect bank accounts (read-only)
- Connect Alpaca account (paper or live)
- View portfolio dashboard
- Place trades (stocks, options, crypto)
- View market data
- Subscribe to structured products (as investor)

**Professional Trader**:
- All Retail Trader permissions
- Access to advanced order types (multi-leg options, bracket orders)
- Real-time market data (full exchange feeds)
- Create watchlists and alerts
- Access to backtesting tools

**Structurer**:
- All Professional Trader permissions
- Create structured product templates
- Price and model products
- Issue products to investors
- Manage product lifecycle

**Admin**:
- All permissions
- Manage user roles and permissions
- Approve structured product issuances
- Access to compliance and audit reports
- System configuration

### 5.2 Permission Definitions

**File**: `app/core/permissions.py` (additions)

```python
# Trading Permissions
PERMISSION_TRADING_VIEW = "TRADING_VIEW"
PERMISSION_TRADING_TRADE = "TRADING_TRADE"
PERMISSION_TRADING_ADVANCED_ORDERS = "TRADING_ADVANCED_ORDERS"
PERMISSION_TRADING_MARKET_DATA = "TRADING_MARKET_DATA"
PERMISSION_TRADING_REALTIME_DATA = "TRADING_REALTIME_DATA"

# Banking Permissions
PERMISSION_BANKING_VIEW = "BANKING_VIEW"
PERMISSION_BANKING_CONNECT = "BANKING_CONNECT"
PERMISSION_BANKING_TRANSACTIONS = "BANKING_TRANSACTIONS"

# Structured Products Permissions
PERMISSION_STRUCTURED_PRODUCTS_VIEW = "STRUCTURED_PRODUCTS_VIEW"
PERMISSION_STRUCTURED_PRODUCTS_CREATE = "STRUCTURED_PRODUCTS_CREATE"
PERMISSION_STRUCTURED_PRODUCTS_ISSUE = "STRUCTURED_PRODUCTS_ISSUE"
PERMISSION_STRUCTURED_PRODUCTS_SUBSCRIBE = "STRUCTURED_PRODUCTS_SUBSCRIBE"

# Add to role permissions
ROLE_PERMISSIONS = {
    UserRole.ANALYST.value: [
        # ... existing permissions ...
        PERMISSION_TRADING_VIEW,
        PERMISSION_BANKING_VIEW,
        PERMISSION_STRUCTURED_PRODUCTS_VIEW,
    ],
    UserRole.BANKER.value: [
        # ... existing permissions ...
        PERMISSION_TRADING_VIEW,
        PERMISSION_TRADING_TRADE,
        PERMISSION_BANKING_VIEW,
        PERMISSION_BANKING_CONNECT,
        PERMISSION_STRUCTURED_PRODUCTS_VIEW,
        PERMISSION_STRUCTURED_PRODUCTS_CREATE,
    ],
    # ... other roles ...
}
```

### 5.3 User Onboarding Flows

**Bank Account Linking Flow**:
1. User clicks "Connect Bank Account"
2. System redirects to Plaid Link (OAuth flow)
3. User selects bank and grants permissions
4. Plaid returns `public_token`
5. Backend exchanges `public_token` for `access_token`
6. Backend fetches accounts and initial transaction history
7. Store `BankConnection` record (encrypted `access_token`)
8. Display connected accounts in dashboard

**Alpaca Account Connection Flow**:
1. User clicks "Connect Alpaca Account"
2. Option A: Connect existing Alpaca account (OAuth via Alpaca Connect API)
3. Option B: Create new Alpaca account via Broker API (requires KYC)
4. Store `AlpacaConnection` record
5. Fetch initial positions and account info
6. Display in trading dashboard

**Structured Product Creation Flow** (Structurer role):
1. Navigate to "Structured Products" → "Create Product"
2. Select product type (equity-linked note, barrier option, etc.)
3. Define underlying asset (stock symbol)
4. Configure payoff formula (strike, barrier, maturity, etc.)
5. Preview pricing and risk metrics
6. Save as template
7. Submit for admin approval (if required)
8. Once approved, can issue to investors

**Product Subscription Flow** (Investor):
1. Browse available structured products
2. View product details (payoff diagram, pricing, risk)
3. Review legal disclosures
4. Enter subscription amount
5. Confirm subscription (may require KYC/AML check)
6. Funds collected (via bank transfer or Alpaca account)
7. Product issued and replicated via Alpaca trades
8. Monitor performance until maturity
9. Receive payout at maturity

---

## 5.5 Integration with Unified Dashboard

### Overview
The Trading Dashboard integration is designed to work within the UnifiedDashboard architecture. Two components are integrated:
1. **TradingDashboard**: Full trading interface (Pro tier required)
2. **PortfolioDashboard**: Portfolio aggregation view (Free tier available)

### Key Integration Points

1. **Component Locations**:
   - `client/src/components/dashboard-tabs/TradingDashboard.tsx`
   - `client/src/components/dashboard-tabs/PortfolioDashboard.tsx`
2. **Tab Configuration**: Both added to UnifiedDashboard tabs array
3. **Subscription Tier Enforcement**: 
   - Trading features require Pro tier
   - Risk analysis requires Pro tier
   - Basic portfolio view available to Free tier
4. **Commission Integration**: Trade execution automatically applies commission charges
5. **Verified Implementations**: Alpaca and Plaid connections use verified implementations system

### Verified Implementations Integration

All external service connections (Alpaca, Plaid, Renta Quattro, etc.) use the verified implementations system:
- Users select implementations during signup
- Connections stored in `UserImplementationConnection`
- Services retrieve connections via implementation name

**Pattern**:
```python
def get_user_implementation_connection(user_id: int, implementation_name: str, db: Session):
    impl = db.query(VerifiedImplementation).filter(
        VerifiedImplementation.name == implementation_name
    ).first()
    
    connection = db.query(UserImplementationConnection).filter(
        UserImplementationConnection.user_id == user_id,
        UserImplementationConnection.implementation_id == impl.id,
        UserImplementationConnection.is_active == True
    ).first()
    
    return connection.connection_data if connection else None
```

### Billing Integration Details

Trading activities automatically generate billing records:

1. **Trade Execution Costs**: Tracked as `usage_cost` in billing periods
2. **Commission Charges**: Tracked as `commission_revenue` (for CreditNexus) in billing periods
3. **Risk Analysis Usage**: Premium risk analysis features tracked as `usage_cost` for Pro tier users
4. **Cost Allocation**: Costs are allocated to organizations and roles via `CostAllocation` records
5. **Billing Dashboard**: Users can view their trading-related costs in the `BillingDashboard` component

**Code Reference**: See `BILLING_DASHBOARD_PLAN.md` for complete billing system details.

### Stock Prediction Integration

**See**: `STOCK_PREDICTION_VENDORING_PLAN.md` for complete stock prediction integration details.

**Integration Points:**
- **Trading Dashboard Tab**: Stock prediction interface integrated into Trading Dashboard
- **Prediction Results**: Display predictions alongside portfolio positions
- **Risk Metrics**: Stock prediction risk metrics integrated into portfolio risk analysis
- **Trading Signals**: Prediction-based trading signals for portfolio management
- **Credit Integration**: Stock predictions consume credits (daily, hourly, 15-minute types)
- **Billing Integration**: Prediction costs tracked in billing dashboard

**Features:**
- Multi-timeframe predictions (daily, hourly, 15-minute)
- Amazon Chronos T5 model (580M+ parameters)
- Ensemble methods for improved accuracy
- Regime detection and stress testing
- Advanced risk metrics (Sharpe, VaR, drawdown)
- Sentiment analysis integration
- Real-time market status monitoring

**Code Reference**: See `STOCK_PREDICTION_VENDORING_PLAN.md` for complete implementation details.

### References
- See `PLAN_INTEGRATION_ADDENDUM.md` for detailed integration patterns
- See `ELECTRON_REFACTORING_PLAN.md` for unified dashboard architecture
- See `MASTER_IMPLEMENTATION_PLAN.md` for overall implementation overview
- See `BILLING_DASHBOARD_PLAN.md` for billing system integration
- See `STOCK_PREDICTION_VENDORING_PLAN.md` for stock prediction integration

---

## 6. Implementation Phases

### Phase 0: Multi-Platform Aggregation Foundation (Weeks 1-2)
- [ ] **Week 1**: Manual asset entry system
  - Create `ManualAsset`, `AssetPriceHistory`, `AssetAlert` models
  - Create Alembic migration
  - Implement `AssetPriceService` for gold/silver price updates
  - Create manual asset entry API endpoints
- [ ] **Week 2**: Platform connector framework
  - Create abstract `PlatformConnector` base class
  - Implement CSV import functionality
  - Create platform-specific connectors (Renta Quattro, XTB, Rent A Four)
  - Add platform connection management UI

### Phase 1: Bank Integration (Weeks 3-5)
- [ ] **Week 1**: Plaid integration service
  - Create `BankIntegrationService` class
  - Implement OAuth flow (Link token creation, public token exchange)
  - Add `BankConnection` and `BankTransaction` models
  - Create Alembic migration
- [ ] **Week 2**: Account and transaction APIs
  - `/api/banking/connect` - Initiate bank connection
  - `/api/banking/accounts` - List connected accounts
  - `/api/banking/transactions` - Fetch transactions
  - `/api/banking/balances` - Get current balances
- [ ] **Week 3**: Frontend bank connection UI
  - Bank connection modal/flow
  - Account list component
  - Transaction history view
  - Testing and error handling

### Phase 2: Alpaca Integration (Weeks 6-9)
- [ ] **Week 6**: Alpaca service layer
  - Create `AlpacaService` class
  - Implement account, positions, orders endpoints
  - Add `AlpacaConnection`, `TradingPosition`, `TradingOrder` models
  - Create Alembic migration
- [ ] **Week 5**: Market data integration
  - Historical bars/candles API
  - Real-time snapshots
  - WebSocket streams for live data
- [ ] **Week 6**: Trading APIs
  - Order creation (market, limit, stop)
  - Order cancellation
  - Multi-leg options support
  - Order status tracking
- [ ] **Week 7**: Frontend trading UI
  - Order entry form
  - Positions table
  - Order history
  - Market data charts

### Phase 3: Amortization & Alerts (Weeks 10-11)
- [ ] **Week 10**: Amortization service
  - Create `AssetAmortizationService`
  - Implement amortization schedule generation
  - Create background task for monitoring payments
  - Add alert notification system (email, in-app)
- [ ] **Week 11**: Alert management UI
  - Create alert configuration interface
  - Display upcoming payments/maturities
  - Alert history and notification preferences

### Phase 4: Trading Dashboard (Weeks 12-14)
- [ ] **Week 12**: Portfolio aggregation service
  - Combine bank balances + trading positions
  - Calculate total equity, P&L
  - Real-time updates via WebSocket
- [ ] **Week 9**: Dashboard frontend
  - Portfolio overview cards
  - Combined positions view
  - Transaction history (bank + trading)
  - Real-time updates
- [ ] **Week 10**: Advanced features
  - Watchlists
  - Price alerts
  - Performance analytics
  - Export functionality

### Phase 5: Premium Risk Analysis (Weeks 15-17)
- [ ] **Week 15**: Risk analysis engine
  - Create `PortfolioRiskService`
  - Implement diversification analysis (asset class, sector, country, currency)
  - Calculate risk metrics (Sharpe ratio, beta, VaR)
- [ ] **Week 16**: Recommendation engine
  - Generate diversification recommendations
  - Overexposure/underexposure detection
  - Risk improvement suggestions
- [ ] **Week 17**: Premium feature gating
  - Integrate RevenueCat for subscription management
  - Add subscription tier checks to risk analysis endpoints
  - Create upgrade prompts in UI

### Phase 6: Structured Products (Weeks 18-21)
- [ ] **Week 18-19**: Product definition engine
  - Create `StructuredProductsService`
  - Product template models
  - Payoff formula DSL/JSON structure
  - Product creation UI
- [ ] **Week 13-14**: Pricing engine
  - Black-Scholes implementation
  - Monte Carlo simulation
  - Integration with Alpaca market data
  - Risk metrics calculation
- [ ] **Week 15**: Product issuance flow
  - Investor subscription system
  - Product replication via Alpaca
  - Lifecycle management
  - Settlement at maturity
- [ ] **Week 16**: Admin and compliance
  - Product approval workflow
  - KYC/AML integration
  - Legal disclosures
  - Audit logging

### Phase 7: Permissions & Security (Weeks 22-23)
- [ ] **Week 22**: Permission system
  - Add trading/banking/structured product permissions
  - Role-based access control
  - Permission checks in APIs
- [ ] **Week 18**: Security hardening
  - Encrypt sensitive tokens (bank access tokens, Alpaca API keys)
  - Rate limiting for trading APIs
  - Audit logging for all trading actions
  - Compliance reporting

### Phase 8: Testing & Documentation (Weeks 24-25)
- [ ] **Week 24**: Integration testing
  - End-to-end bank connection flow
  - End-to-end trading flow
  - Structured product creation and issuance
  - Error handling and edge cases
- [ ] **Week 20**: Documentation and deployment
  - API documentation
  - User guides
  - Deployment checklist
  - Production monitoring setup

---

## 7. Configuration & Environment Variables

**Add to `app/core/config.py`**:

```python
# Bank Integration
BANK_INTEGRATION_ENABLED: bool = Field(default=True)
BANK_PROVIDER: str = Field(default="plaid")  # "plaid", "yodlee", "finicity", "akoya"
PLAID_CLIENT_ID: Optional[SecretStr] = Field(default=None)
PLAID_SECRET: Optional[SecretStr] = Field(default=None)
PLAID_ENV: str = Field(default="sandbox")  # "sandbox", "development", "production"
YODLEE_API_KEY: Optional[SecretStr] = Field(default=None)
FINICITY_APP_KEY: Optional[SecretStr] = Field(default=None)

# Alpaca Markets
ALPACA_ENABLED: bool = Field(default=True)
ALPACA_API_KEY: Optional[SecretStr] = Field(default=None)
ALPACA_SECRET_KEY: Optional[SecretStr] = Field(default=None)
ALPACA_BASE_URL: str = Field(default="https://paper-api.alpaca.markets")  # Paper trading
ALPACA_DATA_URL: str = Field(default="https://data.alpaca.markets")
ALPACA_MARKET_DATA_TIER: str = Field(default="basic")  # "basic" or "algo_trader_plus"

# Structured Products
STRUCTURED_PRODUCTS_ENABLED: bool = Field(default=True)
STRUCTURED_PRODUCTS_REQUIRE_APPROVAL: bool = Field(default=True)
STRUCTURED_PRODUCTS_MIN_NOTIONAL: Decimal = Field(default=Decimal("10000.00"))
```

**Add to `.env`**:
```bash
# Bank Integration
BANK_INTEGRATION_ENABLED=true
BANK_PROVIDER=plaid
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=sandbox

# Alpaca Markets
ALPACA_ENABLED=true
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_URL=https://data.alpaca.markets
ALPACA_MARKET_DATA_TIER=basic

# Structured Products
STRUCTURED_PRODUCTS_ENABLED=true
STRUCTURED_PRODUCTS_REQUIRE_APPROVAL=true
```

---

## 8. API Endpoints Summary

### Manual Asset Endpoints
- `GET /api/assets/manual` - List all manual assets
- `POST /api/assets/manual` - Create manual asset
- `GET /api/assets/manual/{id}` - Get asset details
- `PUT /api/assets/manual/{id}` - Update asset
- `DELETE /api/assets/manual/{id}` - Delete asset
- `POST /api/assets/manual/{id}/update-price` - Manually update asset price
- `GET /api/assets/manual/{id}/price-history` - Get price history
- `POST /api/assets/manual/{id}/alerts` - Create alert for asset
- `GET /api/assets/manual/{id}/alerts` - List alerts for asset
- `GET /api/assets/upcoming-payments` - Get upcoming amortization payments
- `GET /api/assets/maturity-alerts` - Get approaching maturity dates

### Platform Connection Endpoints
- `GET /api/platforms/connections` - List connected platforms
- `POST /api/platforms/connections` - Connect new platform (Renta Quattro, XTB, etc.)
- `POST /api/platforms/connections/{id}/sync` - Sync positions from platform
- `POST /api/platforms/connections/{id}/import-csv` - Import positions via CSV
- `DELETE /api/platforms/connections/{id}` - Disconnect platform

### Portfolio Aggregation Endpoints
- `GET /api/portfolio/overview` - Combined portfolio view (all sources)
- `GET /api/portfolio/breakdown` - Portfolio breakdown by asset class, sector, country
- `GET /api/portfolio/performance` - Performance metrics and analytics
- `GET /api/portfolio/history` - Historical portfolio values

### Premium Risk Analysis Endpoints (Pro/Premium)
- `GET /api/portfolio/risk-analysis` - Full risk analysis (requires Pro tier)
- `GET /api/portfolio/diversification` - Diversification analysis
- `GET /api/portfolio/sector-exposure` - Sector exposure breakdown
- `GET /api/portfolio/country-exposure` - Country exposure breakdown
- `GET /api/portfolio/risk-metrics` - Advanced risk metrics (requires Premium tier)
- `GET /api/portfolio/recommendations` - Diversification recommendations

**Note**: All risk analysis endpoints must check subscription tier. See integration pattern in `PLAN_INTEGRATION_ADDENDUM.md`.

### Banking Endpoints
- `POST /api/banking/connect` - Initiate bank connection (returns Plaid Link token)
- `POST /api/banking/callback` - Handle Plaid OAuth callback
- `GET /api/banking/accounts` - List connected accounts
- `GET /api/banking/accounts/{account_id}/transactions` - Get transactions
- `GET /api/banking/accounts/{account_id}/balance` - Get current balance
- `POST /api/banking/accounts/{account_id}/sync` - Manually sync transactions
- `DELETE /api/banking/connections/{connection_id}` - Disconnect bank account

### Trading Endpoints
- `GET /api/trading/account` - Get Alpaca account summary
- `GET /api/trading/positions` - Get all positions
- `GET /api/trading/positions/{symbol}` - Get position for symbol
- `GET /api/trading/orders` - List orders (with filters)
- `POST /api/trading/orders` - Create new order
- `DELETE /api/trading/orders/{order_id}` - Cancel order
- `GET /api/trading/orders/{order_id}` - Get order details
- `GET /api/trading/market-data/{symbol}` - Get market data (bars, snapshot)
- `GET /api/trading/watchlists` - Get watchlists
- `POST /api/trading/watchlists` - Create watchlist
- `POST /api/trading/alerts` - Create price alert

### Portfolio Endpoints
- `GET /api/portfolio/overview` - Combined portfolio view (bank + trading)
- `GET /api/portfolio/performance` - Performance metrics and analytics
- `GET /api/portfolio/history` - Historical portfolio values

### Structured Products Endpoints
- `GET /api/structured-products/templates` - List product templates
- `POST /api/structured-products/templates` - Create product template
- `GET /api/structured-products/templates/{id}` - Get template details
- `POST /api/structured-products/templates/{id}/price` - Price a product
- `GET /api/structured-products/instances` - List issued products
- `POST /api/structured-products/instances` - Issue new product
- `GET /api/structured-products/instances/{id}` - Get product instance details
- `POST /api/structured-products/instances/{id}/subscribe` - Subscribe to product
- `POST /api/structured-products/instances/{id}/settle` - Settle product at maturity

---

## 9. Success Criteria

### Core Aggregation Features
1. ✅ Users can connect bank accounts via Plaid and view balances/transactions
2. ✅ Users can connect multiple trading platforms (Alpaca, Renta Quattro, XTB, Rent A Four)
3. ✅ Users can manually enter fixed income, real estate, physical assets, and interest accounts
4. ✅ Universal portfolio dashboard displays all investments from all sources in unified view
5. ✅ Real-time price updates for listed assets (stocks, gold, ETFs) via market data APIs

### Manual Asset Management
6. ✅ Users can create manual assets with full metadata (maturity dates, interest rates, etc.)
7. ✅ Amortization schedules generated automatically for fixed income products
8. ✅ Automated alerts for approaching maturity dates and interest payments
9. ✅ Price history tracking for manual assets with market prices (gold, silver)

### Premium Risk Analysis
10. ✅ Pro/Premium users can access portfolio diversification analysis
11. ✅ Risk analysis shows asset class, sector, country, and currency exposure
12. ✅ System generates recommendations for overexposure/underexposure
13. ✅ Premium users can access advanced risk metrics (Sharpe ratio, beta, VaR)

### Trading & Structured Products
14. ✅ Users can place trades (stocks, options) via Alpaca API
15. ✅ Real-time market data updates via WebSocket
16. ✅ Structurers can create structured product templates
17. ✅ Pricing engine accurately prices products using market data
18. ✅ Products can be issued to investors and replicated via Alpaca trades

### Security & Compliance
19. ✅ Permission system restricts access based on user roles and subscription tiers
20. ✅ All trading actions and portfolio changes are logged in audit trail
21. ✅ CDM events generated for all financial transactions
22. ✅ Subscription tiers properly gate premium features (risk analysis, structured products)

---

## 10. Risks & Mitigations

**Regulatory Risks:**
- **Risk**: Structured products may be securities requiring SEC/FINRA registration
- **Mitigation**: Partner with registered broker-dealer or use Alpaca Broker API
- **Risk**: Bank data aggregation requires GLBA compliance
- **Mitigation**: Use Plaid (SOC 2 certified) and encrypt all access tokens

**Technical Risks:**
- **Risk**: Market data API rate limits
- **Mitigation**: Implement caching, use WebSocket streams, upgrade to paid tier
- **Risk**: Order execution failures (partial fills, slippage)
- **Mitigation**: Implement retry logic, order status monitoring, error handling

**Operational Risks:**
- **Risk**: Structured product pricing errors
- **Mitigation**: Extensive testing, use established pricing libraries (QuantLib), peer review
- **Risk**: Unauthorized trading access
- **Mitigation**: Strong permission system, audit logging, rate limiting

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
