# Stock Prediction Vendoring Plan: CreditNexus
## Complete Integration of Amazon Chronos T5 Stock Prediction System

**Status**: Comprehensive Integration Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 8-10 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This document provides a **complete plan** for vendoring in the stock prediction functionality from `dev/stockpredictions.py` into CreditNexus. The system uses Amazon's Chronos T5 foundation model (580M+ parameters) for time series forecasting with advanced features including ensemble methods, regime detection, stress testing, sentiment analysis, and multi-timeframe support (daily, hourly, 15-minute).

**Key Integration Points:**
- **Service Layer Integration**: Create `StockPredictionService` following CreditNexus service patterns
- **API Endpoints**: FastAPI endpoints with permission checks and CDM event generation
- **Database Models**: Store predictions, analysis results, and model metadata
- **Frontend Integration**: React components for prediction UI in Trading Dashboard
- **Credit System Integration**: Track credit usage per prediction type
- **Audit & Traceability**: Full logging of predictions, model calls, and results
- **Billing Integration**: Cost tracking for prediction operations

---

## Current State Analysis

### ✅ Existing Infrastructure

#### 1. Stock Prediction System (`dev/stockpredictions.py`)
**Location**: `dev/stockpredictions.py` (5099 lines)

**Current Capabilities:**
- ✅ Amazon Chronos T5 model integration (580M+ parameters)
- ✅ Multi-timeframe support (daily, hourly, 15-minute)
- ✅ Ensemble methods (Random Forest, Gradient Boosting, SVR, Neural Networks)
- ✅ Regime detection (HMM-based and volatility-based)
- ✅ Stress testing scenarios
- ✅ Sentiment analysis (TextBlob)
- ✅ Enhanced covariate data (market indices, sectors, commodities, currencies)
- ✅ Advanced uncertainty quantification
- ✅ Technical indicators (RSI, MACD, Bollinger Bands, SMAs)
- ✅ Volume prediction
- ✅ Market status management (multi-market support)
- ✅ Gradio UI interface

**Key Functions:**
- `make_prediction_enhanced()` - Main prediction function
- `get_historical_data()` - yfinance data fetching
- `detect_market_regime()` - Regime detection
- `calculate_advanced_risk_metrics()` - Risk analysis
- `create_enhanced_ensemble_model()` - Ensemble predictions
- `calculate_market_sentiment()` - Sentiment analysis
- `stress_test_scenarios()` - Stress testing

**Dependencies:**
- `chronos` (Amazon Chronos T5)
- `yfinance` (market data)
- `torch` (PyTorch for model)
- `plotly` (visualization)
- `scikit-learn` (ensemble methods)
- `hmmlearn` (regime detection)
- `textblob` (sentiment analysis)

#### 2. CreditNexus Existing Services

**QuantitativeAnalysisService** (`app/services/quantitative_analysis_service.py`):
- ✅ LangAlpha multi-agent system integration
- ✅ Market analysis endpoints
- ✅ Company analysis
- ✅ Loan application analysis
- ✅ CDM event generation
- ✅ Audit logging

**Trading Dashboard Plan** (`dev/TRADING_DASHBOARD_IMPLEMENTATION_PLAN.md`):
- ✅ Portfolio aggregation
- ✅ Real-time price updates
- ✅ Risk analysis
- ✅ Trading signals

**Market Analysis Endpoints** (`app/api/routes.py`):
- ✅ `/api/quantitative-analysis/market` - Market analysis
- ✅ Market data integration
- ✅ Policy service integration

---

## Integration Architecture

### 1. Service Layer

#### 1.1 StockPredictionService

**Location**: `app/services/stock_prediction_service.py` (NEW)

**Responsibilities:**
- Orchestrate Chronos model predictions
- Manage model loading and GPU resources
- Integrate with ensemble methods
- Handle regime detection and stress testing
- Generate CDM events for predictions
- Track credit usage
- Log audit trails

**Key Methods:**
```python
class StockPredictionService:
    def __init__(self, db: Session, policy_service: Optional[PolicyService] = None):
        """Initialize stock prediction service."""
        
    async def predict_stock_price(
        self,
        symbol: str,
        timeframe: str = "1d",
        prediction_days: int = 30,
        strategy: str = "chronos",
        use_ensemble: bool = True,
        use_regime_detection: bool = True,
        use_stress_testing: bool = True,
        user_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        credit_type: str = "quantitative_analysis"
    ) -> Dict[str, Any]:
        """Generate stock price prediction with full analysis."""
        
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        lookback_days: int = 365
    ) -> pd.DataFrame:
        """Fetch historical market data."""
        
    def detect_market_regime(
        self,
        returns: pd.Series,
        n_regimes: int = 3
    ) -> Dict[str, Any]:
        """Detect market regime using HMM or volatility-based methods."""
        
    def calculate_risk_metrics(
        self,
        df: pd.DataFrame,
        market_returns: Optional[pd.Series] = None,
        risk_free_rate: float = 0.02
    ) -> Dict[str, Any]:
        """Calculate advanced risk metrics."""
        
    def perform_stress_testing(
        self,
        df: pd.DataFrame,
        prediction: np.ndarray,
        scenarios: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Perform stress testing under various scenarios."""
```

**Integration Points:**
- Uses `get_chat_model()` from `app/core/llm_client.py` for sentiment analysis (if needed)
- Integrates with `CreditService` for credit tracking
- Uses `AuditService` for logging
- Generates CDM events via `generate_cdm_observation()`

#### 1.2 ChronosModelManager

**Location**: `app/services/chronos_model_manager.py` (NEW)

**Responsibilities:**
- Manage Chronos model lifecycle (loading, caching, GPU allocation)
- Handle model initialization and cleanup
- Provide thread-safe model access
- Monitor GPU memory usage

**Key Methods:**
```python
class ChronosModelManager:
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Initialize model manager (singleton)."""
        
    def get_pipeline(self) -> ChronosPipeline:
        """Get or load Chronos pipeline."""
        
    def clear_gpu_memory(self):
        """Clear GPU memory cache."""
        
    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
```

---

### 2. Database Models

#### 2.1 StockPrediction

**Location**: `app/db/models.py` (UPDATE)

```python
class StockPrediction(Base):
    """Store stock prediction results."""
    __tablename__ = "stock_predictions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    timeframe: Mapped[str] = mapped_column(String(10))  # "1d", "1h", "15m"
    prediction_days: Mapped[int] = mapped_column(Integer)
    strategy: Mapped[str] = mapped_column(String(50))  # "chronos", "technical"
    
    # Prediction results (JSONB)
    predictions: Mapped[dict] = mapped_column(JSONB)  # Price predictions with dates
    technical_indicators: Mapped[dict] = mapped_column(JSONB)  # RSI, MACD, etc.
    risk_metrics: Mapped[dict] = mapped_column(JSONB)  # Sharpe, VaR, etc.
    regime_info: Mapped[dict] = mapped_column(JSONB)  # Market regime detection
    stress_test_results: Mapped[dict] = mapped_column(JSONB)  # Stress scenarios
    ensemble_metrics: Mapped[dict] = mapped_column(JSONB)  # Ensemble analysis
    
    # Metadata
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    deal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("deals.id"))
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"))
    
    # Model configuration
    model_config: Mapped[dict] = mapped_column(JSONB)  # Ensemble weights, smoothing, etc.
    
    # CDM events
    cdm_events: Mapped[List[dict]] = mapped_column(JSONB, default=list)
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="stock_predictions")
    deal: Mapped[Optional["Deal"]] = relationship(back_populates="stock_predictions")
```

#### 2.2 StockPredictionCache

**Location**: `app/db/models.py` (UPDATE)

```python
class StockPredictionCache(Base):
    """Cache stock prediction results for performance."""
    __tablename__ = "stock_prediction_cache"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    timeframe: Mapped[str] = mapped_column(String(10))
    prediction_days: Mapped[int] = mapped_column(Integer)
    
    # Cached results
    prediction_data: Mapped[dict] = mapped_column(JSONB)
    
    # Expiration
    expires_at: Mapped[datetime] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

---

### 3. API Endpoints

#### 3.1 Stock Prediction Endpoints

**Location**: `app/api/routes.py` (UPDATE) or `app/api/stock_prediction_routes.py` (NEW)

```python
@router.post("/stock-prediction/predict")
async def predict_stock(
    request: StockPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    stock_prediction_service: StockPredictionService = Depends(get_stock_prediction_service)
):
    """Generate stock price prediction with full analysis."""
    # Check credits
    # Generate prediction
    # Store in database
    # Generate CDM events
    # Log audit
    # Return results

@router.get("/stock-prediction/{prediction_id}")
async def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get stored prediction result."""
    
@router.get("/stock-prediction/history")
async def get_prediction_history(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get prediction history with pagination."""
    
@router.post("/stock-prediction/batch")
async def batch_predict(
    request: BatchStockPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    stock_prediction_service: StockPredictionService = Depends(get_stock_prediction_service)
):
    """Generate predictions for multiple symbols."""
```

**Request/Response Models:**
```python
class StockPredictionRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    timeframe: str = Field("1d", pattern="^(1d|1h|15m)$")
    prediction_days: int = Field(30, ge=1, le=365)
    strategy: str = Field("chronos", pattern="^(chronos|technical)$")
    use_ensemble: bool = Field(True)
    use_regime_detection: bool = Field(True)
    use_stress_testing: bool = Field(True)
    use_covariates: bool = Field(True)
    use_sentiment: bool = Field(True)
    risk_free_rate: float = Field(0.02, ge=0.0, le=0.1)
    market_index: str = Field("^GSPC")
    ensemble_weights: Optional[Dict[str, float]] = None
    smoothing_type: str = Field("exponential")
    deal_id: Optional[int] = None

class StockPredictionResponse(BaseModel):
    prediction_id: int
    symbol: str
    predictions: Dict[str, Any]
    technical_indicators: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    regime_info: Dict[str, Any]
    stress_test_results: Dict[str, Any]
    ensemble_metrics: Dict[str, Any]
    cdm_events: List[Dict[str, Any]]
    created_at: datetime
```

---

### 4. Frontend Integration

#### 4.1 StockPredictionDashboard Component

**Location**: `client/src/apps/trading/StockPredictionDashboard.tsx` (NEW)

**Features:**
- Symbol input and timeframe selection
- Prediction parameters configuration
- Real-time prediction results display
- Interactive Plotly charts (price, technical indicators, volume)
- Risk metrics visualization
- Regime detection display
- Stress test scenario viewer
- Prediction history table
- Export functionality

**Integration:**
- Uses Trading Dashboard tab system
- FDC3 context broadcasting for predictions
- Credit balance display
- Permission-based access

#### 4.2 PredictionChart Component

**Location**: `client/src/components/trading/PredictionChart.tsx` (NEW)

**Features:**
- Plotly-based interactive charts
- Historical + predicted price display
- Confidence intervals
- Technical indicators overlay
- Volume charts
- Bollinger Bands visualization

---

### 5. Credit System Integration

#### 5.1 Credit Types

**Location**: `app/db/models.py` (UPDATE)

Add to `CreditType` enum:
```python
class CreditType(str, Enum):
    # ... existing types ...
    STOCK_PREDICTION_DAILY = "stock_prediction_daily"
    STOCK_PREDICTION_HOURLY = "stock_prediction_hourly"
    STOCK_PREDICTION_15MIN = "stock_prediction_15min"
```

#### 5.2 Credit Usage Tracking

**Location**: `app/services/stock_prediction_service.py`

```python
async def predict_stock_price(...):
    # Check credits
    credit_service = CreditService(self.db)
    credit_type = self._get_credit_type_for_timeframe(timeframe)
    
    required_credits = self._calculate_credit_cost(
        timeframe=timeframe,
        prediction_days=prediction_days,
        use_ensemble=use_ensemble,
        use_stress_testing=use_stress_testing
    )
    
    has_credits = await credit_service.check_credits(
        user_id=user_id,
        credit_type=credit_type,
        amount=required_credits
    )
    
    if not has_credits:
        raise HTTPException(402, "Insufficient credits")
    
    # Generate prediction
    result = await self._generate_prediction(...)
    
    # Deduct credits
    await credit_service.use_credits(
        user_id=user_id,
        credit_type=credit_type,
        amount=required_credits,
        workflow_id=result["prediction_id"],
        metadata={"symbol": symbol, "timeframe": timeframe}
    )
    
    return result
```

---

### 6. CDM Event Generation

#### 6.1 Prediction Observation Events

**Location**: `app/models/cdm_events.py` (UPDATE)

```python
def generate_cdm_stock_prediction_observation(
    prediction_id: int,
    symbol: str,
    predictions: Dict[str, Any],
    risk_metrics: Dict[str, Any],
    regime_info: Dict[str, Any],
    related_event_identifiers: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """Generate CDM Observation event for stock prediction."""
    return {
        "eventType": "Observation",
        "eventDate": datetime.utcnow().isoformat(),
        "meta": {
            "globalKey": {
                "issuer": "CreditNexus",
                "assignedIdentifier": [{
                    "identifier": {
                        "value": f"STOCK_PRED_{prediction_id}"
                    }
                }]
            }
        },
        "observation": {
            "observationType": "StockPricePrediction",
            "observedValue": {
                "value": predictions.get("mean_prediction", []),
                "unit": "USD"
            },
            "observationDate": datetime.utcnow().isoformat(),
            "metadata": {
                "symbol": symbol,
                "timeframe": predictions.get("timeframe"),
                "risk_metrics": risk_metrics,
                "regime_info": regime_info
            }
        },
        "relatedEventIdentifier": related_event_identifiers or []
    }
```

---

### 7. Audit & Traceability

#### 7.1 LLM Call Tracing

**Location**: `app/services/stock_prediction_service.py`

- Log all Chronos model calls
- Track GPU usage and latency
- Record prediction parameters
- Store model configuration

#### 7.2 Prediction Audit Logging

**Location**: `app/services/stock_prediction_service.py`

```python
log_audit_action(
    db=self.db,
    action=AuditAction.CREATE,
    target_type="stock_prediction",
    target_id=prediction_id,
    user_id=user_id,
    metadata={
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy": strategy,
        "prediction_days": prediction_days,
        "credits_used": required_credits
    }
)
```

---

### 8. Billing Integration

#### 8.1 Cost Calculation

**Location**: `app/services/stock_prediction_service.py`

```python
def _calculate_prediction_cost(
    self,
    timeframe: str,
    prediction_days: int,
    use_ensemble: bool,
    use_stress_testing: bool
) -> Decimal:
    """Calculate cost for prediction operation."""
    base_cost = Decimal("0.10")  # Base cost per prediction
    
    # Timeframe multiplier
    timeframe_multiplier = {
        "1d": Decimal("1.0"),
        "1h": Decimal("1.5"),
        "15m": Decimal("2.0")
    }.get(timeframe, Decimal("1.0"))
    
    # Prediction days multiplier
    days_multiplier = Decimal(str(prediction_days)) / Decimal("30")
    
    # Feature multipliers
    ensemble_multiplier = Decimal("1.2") if use_ensemble else Decimal("1.0")
    stress_multiplier = Decimal("1.3") if use_stress_testing else Decimal("1.0")
    
    total_cost = (
        base_cost *
        timeframe_multiplier *
        days_multiplier *
        ensemble_multiplier *
        stress_multiplier
    )
    
    return total_cost
```

#### 8.2 Billing Service Integration

**Location**: `app/services/billing_service.py` (UPDATE)

Track prediction costs in billing periods:
- Cost per prediction operation
- GPU compute costs
- Data fetching costs (yfinance API)

---

## Implementation Phases

### Phase 1: Core Service Integration (Weeks 1-2)

**Goal**: Extract and integrate core prediction functionality

**Tasks:**
1. Create `app/services/chronos_model_manager.py`
   - Model loading and caching
   - GPU memory management
   - Thread-safe access

2. Create `app/services/stock_prediction_service.py`
   - Extract `make_prediction_enhanced()` logic
   - Integrate with CreditNexus patterns
   - Add credit checking
   - Add audit logging

3. Create database models
   - `StockPrediction` model
   - `StockPredictionCache` model
   - Alembic migration

4. Extract utility functions
   - `get_historical_data()` → `app/services/market_data_service.py`
   - `detect_market_regime()` → `app/services/stock_prediction_service.py`
   - `calculate_advanced_risk_metrics()` → `app/services/stock_prediction_service.py`

**Files Created:**
- `app/services/chronos_model_manager.py`
- `app/services/stock_prediction_service.py`
- `app/services/market_data_service.py` (NEW or UPDATE)
- `app/db/models.py` (UPDATE)
- `alembic/versions/XXXX_add_stock_prediction_models.py`

---

### Phase 2: API Integration (Week 3)

**Goal**: Create FastAPI endpoints with full integration

**Tasks:**
1. Create API endpoints
   - `/api/stock-prediction/predict`
   - `/api/stock-prediction/{id}`
   - `/api/stock-prediction/history`
   - `/api/stock-prediction/batch`

2. Add request/response models
   - `StockPredictionRequest`
   - `StockPredictionResponse`
   - `BatchStockPredictionRequest`

3. Integrate with existing systems
   - Credit checking
   - Permission checks
   - CDM event generation
   - Audit logging

**Files Created:**
- `app/api/stock_prediction_routes.py` (NEW)
- `app/models/stock_prediction.py` (NEW) - Pydantic models

---

### Phase 3: Frontend Integration (Weeks 4-5)

**Goal**: Create React components for prediction UI

**Tasks:**
1. Create `StockPredictionDashboard` component
   - Symbol input and configuration
   - Prediction execution
   - Results display

2. Create `PredictionChart` component
   - Plotly integration
   - Interactive charts
   - Technical indicators overlay

3. Integrate with Trading Dashboard
   - Add prediction tab
   - FDC3 context broadcasting
   - Credit balance display

**Files Created:**
- `client/src/apps/trading/StockPredictionDashboard.tsx`
- `client/src/components/trading/PredictionChart.tsx`
- `client/src/components/trading/PredictionHistory.tsx`
- `client/src/components/trading/RiskMetricsDisplay.tsx`

---

### Phase 4: Advanced Features (Weeks 6-7)

**Goal**: Integrate ensemble methods, regime detection, stress testing

**Tasks:**
1. Integrate ensemble methods
   - Random Forest, Gradient Boosting, SVR, Neural Networks
   - Weighted combination logic
   - Performance tracking

2. Integrate regime detection
   - HMM-based detection
   - Volatility-based fallback
   - Regime-aware uncertainty

3. Integrate stress testing
   - Scenario definitions
   - Stress test execution
   - Results visualization

4. Integrate sentiment analysis
   - News sentiment calculation
   - Integration with predictions

**Files Updated:**
- `app/services/stock_prediction_service.py`
- `app/services/market_data_service.py`

---

### Phase 5: Optimization & Caching (Week 8)

**Goal**: Performance optimization and caching

**Tasks:**
1. Implement prediction caching
   - Cache key generation
   - Cache expiration logic
   - Cache invalidation

2. Optimize model loading
   - Lazy loading
   - Model pooling
   - GPU memory optimization

3. Optimize data fetching
   - yfinance request caching
   - Batch data fetching
   - Rate limiting

**Files Updated:**
- `app/services/stock_prediction_service.py`
- `app/services/market_data_service.py`
- `app/services/chronos_model_manager.py`

---

### Phase 6: Testing & Documentation (Weeks 9-10)

**Goal**: Comprehensive testing and documentation

**Tasks:**
1. Unit tests
   - Service layer tests
   - Model manager tests
   - Utility function tests

2. Integration tests
   - API endpoint tests
   - Credit system integration
   - CDM event generation

3. Documentation
   - API documentation
   - Service documentation
   - Frontend component documentation

**Files Created:**
- `tests/test_stock_prediction_service.py`
- `tests/test_stock_prediction_api.py`
- `docs/features/stock-prediction.mdx`

---

## Dependencies & Requirements

### Python Dependencies

**New Dependencies:**
```python
# Add to requirements.txt
chronos>=0.1.0  # Amazon Chronos T5
yfinance>=0.2.0  # Market data (may already exist)
hmmlearn>=0.2.7  # Regime detection
textblob>=0.17.1  # Sentiment analysis
arch>=6.0.0  # GARCH modeling (optional)
```

**Existing Dependencies (verify):**
- `torch>=2.0.0` (PyTorch)
- `plotly>=5.0.0` (Visualization)
- `scikit-learn>=1.0.0` (Ensemble methods)
- `pandas>=2.0.0`
- `numpy>=1.24.0`

### GPU Requirements

- **Minimum**: CUDA-capable GPU with 8GB VRAM
- **Recommended**: CUDA-capable GPU with 16GB+ VRAM
- **Model Size**: Chronos T5 Large (~580M parameters)
- **Memory**: ~4-6GB VRAM for model + inference

### Environment Variables

```env
# Stock Prediction Configuration
STOCK_PREDICTION_ENABLED=true
CHRONOS_MODEL_PATH=amazon/chronos-t5-large
CHRONOS_DEVICE=cuda  # or "cpu" for CPU-only
CHRONOS_DTYPE=float16  # or "float32"
STOCK_PREDICTION_CACHE_TTL=3600  # Cache TTL in seconds
STOCK_PREDICTION_MAX_CONCURRENT=2  # Max concurrent predictions
```

---

## Integration with Existing Plans

### Trading Dashboard Plan

**Update**: `dev/TRADING_DASHBOARD_IMPLEMENTATION_PLAN.md`

**Add Section**: "Stock Prediction Integration"
- Stock prediction tab in Trading Dashboard
- Prediction results in portfolio view
- Risk metrics integration
- Prediction-based trading signals

### Billing Dashboard Plan

**Update**: `dev/BILLING_DASHBOARD_PLAN.md`

**Add Section**: "Stock Prediction Costs"
- Cost tracking per prediction
- GPU compute costs
- Credit usage per timeframe
- Cost allocation by organization

### Rolling Credits Plan

**Update**: `dev/ROLLING_CREDITS_SUBSCRIPTION_PLAN.md`

**Add Credit Types**:
- `STOCK_PREDICTION_DAILY` - Daily predictions
- `STOCK_PREDICTION_HOURLY` - Hourly predictions
- `STOCK_PREDICTION_15MIN` - 15-minute predictions

**Credit Allocation**:
- Free tier: 10 daily predictions/month
- Pro tier: 100 daily, 50 hourly, 20 15-minute/month
- Premium tier: Unlimited predictions

### Audit & Traceability Plan

**Update**: `dev/AUDIT_TRACEABILITY_PLAN.md`

**Add Section**: "Stock Prediction Audit"
- LLM call tracing for Chronos model
- Prediction parameter logging
- GPU usage tracking
- Model performance metrics

---

## Migration Strategy

### Step 1: Extract Core Functions

1. Copy prediction functions from `dev/stockpredictions.py`
2. Refactor to follow CreditNexus patterns
3. Remove Gradio dependencies
4. Add service layer abstraction

### Step 2: Create Service Layer

1. Create `StockPredictionService`
2. Integrate with existing services
3. Add credit checking
4. Add audit logging

### Step 3: Create API Layer

1. Create FastAPI endpoints
2. Add request/response models
3. Integrate with authentication
4. Add permission checks

### Step 4: Create Frontend

1. Create React components
2. Integrate with Trading Dashboard
3. Add FDC3 broadcasting
4. Add credit balance display

### Step 5: Testing & Deployment

1. Unit tests
2. Integration tests
3. Performance testing
4. Documentation

---

## Risk Mitigation

### Technical Risks

1. **GPU Memory Issues**
   - **Mitigation**: Implement model pooling and memory management
   - **Fallback**: CPU inference (slower but functional)

2. **Model Loading Time**
   - **Mitigation**: Lazy loading and caching
   - **Fallback**: Pre-load model on startup (optional)

3. **yfinance Rate Limits**
   - **Mitigation**: Request caching and rate limiting
   - **Fallback**: Alternative data providers

4. **Prediction Accuracy**
   - **Mitigation**: Ensemble methods and uncertainty quantification
   - **Fallback**: Technical analysis fallback

### Business Risks

1. **Credit Cost Miscalculation**
   - **Mitigation**: Careful cost calculation and testing
   - **Monitoring**: Track actual costs vs. predicted

2. **High GPU Costs**
   - **Mitigation**:** Optimize model usage and caching
   - **Monitoring**: Track GPU usage and costs

---

## Success Metrics

1. **Performance**
   - Prediction latency < 30 seconds (daily)
   - Prediction latency < 60 seconds (hourly)
   - Prediction latency < 90 seconds (15-minute)

2. **Accuracy**
   - Mean Absolute Percentage Error (MAPE) < 5% for daily
   - Correlation with actual prices > 0.7

3. **Usage**
   - 100+ predictions/day (target)
   - User satisfaction > 4.0/5.0

4. **Cost**
   - Cost per prediction < $0.50
   - GPU utilization > 60%

---

## Future Enhancements

1. **Multi-Asset Support**
   - ETFs, commodities, forex
   - Cryptocurrency predictions

2. **Portfolio-Level Predictions**
   - Aggregate predictions
   - Portfolio risk analysis

3. **Real-Time Predictions**
   - Streaming predictions
   - WebSocket updates

4. **Advanced Features**
   - Options pricing integration
   - Volatility surface modeling
   - Correlation analysis

---

## References

- **Chronos Model**: [Amazon Chronos T5](https://huggingface.co/amazon/chronos-t5-large)
- **Trading Dashboard Plan**: `dev/TRADING_DASHBOARD_IMPLEMENTATION_PLAN.md`
- **Billing Dashboard Plan**: `dev/BILLING_DASHBOARD_PLAN.md`
- **Rolling Credits Plan**: `dev/ROLLING_CREDITS_SUBSCRIPTION_PLAN.md`
- **Audit Plan**: `dev/AUDIT_TRACEABILITY_PLAN.md`
- **Service Layer Pattern**: `dev/rules/service-layer.md`
- **API Routing Rules**: `dev/rules/api-routing.md`

---

**Plan Created**: 2024-12-XX  
**Status**: Ready for Implementation  
**Next Steps**: Begin Phase 1 - Core Service Integration
