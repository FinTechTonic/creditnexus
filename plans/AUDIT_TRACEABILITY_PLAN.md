# Complete Audit and Traceability Implementation Plan

## Executive Summary

This plan addresses comprehensive audit flows, logging, and traceability across CreditNexus. It ensures that **absolutely every trace** from LLM calls, policy decisions, workflows, blockchain transactions, and notarization activities is registered and logged. The audit dashboard will be accessible to all users in a permissioned way, with role-based data access controls.

---

## Current State Assessment

### ✅ Existing Components

1. **Basic Audit Logging**
   - `AuditLog` model with encrypted metadata
   - `log_audit_action()` utility function
   - Audit dashboard UI (`AuditDashboard.tsx`)
   - Audit service (`AuditService`) with filtering and enrichment
   - Audit API routes (`/api/auditor/*`)

2. **Policy Decision Logging**
   - `PolicyDecision` model with CDM events
   - `log_policy_decision()` function
   - Policy audit service (`PolicyAuditService`)

3. **Verification Audit**
   - `VerificationAuditLog` model
   - Verification service audit logging

4. **Notarization**
   - `NotarizationRecord` model
   - Notarization service with CDM event generation

5. **Blockchain Service**
   - `BlockchainService` for contract interactions
   - Transaction execution but **no audit logging**

### ❌ Critical Gaps

1. **LLM Call Tracing**: No comprehensive logging of:
   - Prompts and responses
   - Token usage (input/output)
   - Costs per call
   - Model/provider used
   - Latency/timing
   - Error traces
   - **Stock Prediction Model Calls**: Chronos T5 model calls, GPU usage, prediction parameters
     - Chronos T5 inference calls (not traditional LLM but ML model)
     - GPU memory usage and allocation
     - Prediction parameters (timeframe, strategy, ensemble weights)
     - Model loading and initialization events
     - Prediction latency and throughput

2. **Blockchain Transaction Audit**: No logging of:
   - Transaction hashes
   - Block numbers
   - Gas costs
   - Contract addresses
   - Event logs
   - Transaction status

3. **Workflow Traceability**: Incomplete logging of:
   - Agent workflow state transitions
   - Multi-agent coordination
   - Tool usage within workflows
   - Workflow execution traces

4. **Analysis Report Notarization**: Missing:
   - Notarization for signed analysis reports
   - Blockchain verification for reports
   - Report integrity verification

5. **Permissioned Access**: Audit dashboard may not be:
   - Accessible to all users with proper permissions
   - Filtered by organization/role
   - Showing only relevant data per user

6. **Comprehensive Traceability**: Missing:
   - End-to-end trace linking (LLM → Policy → Workflow → Blockchain)
   - Trace correlation IDs
   - Parent-child trace relationships

---

## Implementation Plan

### Project 1: LLM Call Tracing System

**Objective**: Log every LLM call with full traceability including prompts, responses, tokens, costs, and performance metrics.

#### Task 1.1.1: Create LLMCallLog Database Model

**File**: `app/db/models.py` (UPDATE)

```python
class LLMCallLog(Base):
    """Comprehensive logging for all LLM API calls."""
    
    __tablename__ = "llm_call_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Call identification
    call_id = Column(String(255), unique=True, nullable=False, index=True)  # UUID
    trace_id = Column(String(255), nullable=True, index=True)  # Links to workflow/policy trace
    parent_call_id = Column(String(255), ForeignKey("llm_call_logs.call_id"), nullable=True)  # For chained calls
    
    # Provider and model
    provider = Column(String(50), nullable=False, index=True)  # openai, vllm, huggingface, chronos
    model = Column(String(255), nullable=False, index=True)  # gpt-4o, chronos-t5-580m, etc.
    model_type = Column(String(50), nullable=True, index=True)  # llm, time_series, classification, etc.
    temperature = Column(Float, nullable=True)
    
    # Request data
    prompt = Column(EncryptedJSON(), nullable=False)  # Full prompt (encrypted)
    prompt_tokens = Column(Integer, nullable=False)
    prompt_length = Column(Integer, nullable=False)  # Character count
    
    # Response data
    response = Column(EncryptedJSON(), nullable=True)  # Full response (encrypted)
    response_tokens = Column(Integer, nullable=True)
    response_length = Column(Integer, nullable=True)  # Character count
    finish_reason = Column(String(50), nullable=True)  # stop, length, error
    
    # Cost tracking
    input_cost = Column(Numeric(10, 6), nullable=True)  # Cost for input tokens
    output_cost = Column(Numeric(10, 6), nullable=True)  # Cost for output tokens
    total_cost = Column(Numeric(10, 6), nullable=True)  # Total cost
    currency = Column(String(10), default="USD", nullable=False)
    
    # Performance metrics
    latency_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    retry_count = Column(Integer, default=0, nullable=False)
    
    # ML/Time Series specific (for Chronos T5, etc.)
    gpu_memory_mb = Column(Integer, nullable=True)  # GPU memory used (for ML models)
    gpu_utilization = Column(Float, nullable=True)  # GPU utilization percentage
    prediction_horizon = Column(Integer, nullable=True)  # Prediction horizon (days/hours)
    model_parameters = Column(JSONB, nullable=True)  # Model-specific parameters (ensemble weights, etc.)
    
    # Error tracking
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    success = Column(Boolean, default=True, nullable=False, index=True)
    
    # Context and relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True, index=True)
    policy_decision_id = Column(Integer, ForeignKey("policy_decisions.id"), nullable=True, index=True)
    
    # Metadata
    metadata = Column(JSONB, nullable=True)  # Additional context (chain type, tool name, etc.)
    
    # Timestamps
    called_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="llm_call_logs")
    deal = relationship("Deal", backref="llm_call_logs")
    document = relationship("Document", backref="llm_call_logs")
    workflow = relationship("Workflow", backref="llm_call_logs")
    policy_decision = relationship("PolicyDecision", backref="llm_call_logs")
    parent_call = relationship("LLMCallLog", remote_side=[id], backref="child_calls")
    
    def to_dict(self):
        """Convert to dictionary (excludes encrypted fields by default)."""
        return {
            "id": self.id,
            "call_id": self.call_id,
            "trace_id": self.trace_id,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "response_tokens": self.response_tokens,
            "total_cost": float(self.total_cost) if self.total_cost else None,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "called_at": self.called_at.isoformat() if self.called_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
```

#### Task 1.1.2: Create LLM Call Tracing Wrapper

**File**: `app/core/llm_tracing.py` (NEW)

```python
"""
LLM Call Tracing Wrapper for CreditNexus.

Wraps all LLM calls to automatically log prompts, responses, tokens, costs, and performance.
"""

import logging
import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from app.db.models import LLMCallLog
from app.core.llm_client import get_chat_model

logger = logging.getLogger(__name__)

# Cost per 1M tokens (approximate, should be configurable)
COST_PER_TOKEN = {
    "gpt-4o": {"input": 2.50, "output": 10.00},  # $2.50/$10 per 1M tokens
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "default": {"input": 1.00, "output": 2.00},
}


class TracingChatModel(BaseChatModel):
    """Wrapper around BaseChatModel that adds comprehensive tracing."""
    
    def __init__(
        self,
        model: BaseChatModel,
        db: Optional[Session] = None,
        user_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        document_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        trace_id: Optional[str] = None,
        parent_call_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__()
        self.model = model
        self.db = db
        self.user_id = user_id
        self.deal_id = deal_id
        self.document_id = document_id
        self.workflow_id = workflow_id
        self.trace_id = trace_id
        self.parent_call_id = parent_call_id
        self.metadata = metadata or {}
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatGeneration:
        """Generate response with tracing."""
        call_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Extract provider and model info
        provider = self.metadata.get("provider", "unknown")
        model_name = self.metadata.get("model", "unknown")
        
        # Prepare prompt for logging
        prompt_data = {
            "messages": [msg.dict() for msg in messages],
            "stop": stop,
            **kwargs
        }
        prompt_length = sum(len(str(msg.content)) for msg in messages)
        
        # Log call start
        llm_log = LLMCallLog(
            call_id=call_id,
            trace_id=self.trace_id,
            parent_call_id=self.parent_call_id,
            provider=provider,
            model=model_name,
            temperature=kwargs.get("temperature"),
            prompt=prompt_data,
            prompt_length=prompt_length,
            user_id=self.user_id,
            deal_id=self.deal_id,
            document_id=self.document_id,
            workflow_id=self.workflow_id,
            metadata=self.metadata,
            called_at=datetime.utcnow(),
            success=False  # Will update on success
        )
        
        if self.db:
            self.db.add(llm_log)
            self.db.flush()  # Get ID without committing
        
        try:
            # Call actual model
            result = self.model._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
            
            # Calculate metrics
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            # Extract token usage (if available)
            prompt_tokens = getattr(result, "prompt_tokens", None) or self._estimate_tokens(prompt_length)
            response_tokens = getattr(result, "completion_tokens", None) or self._estimate_tokens(len(str(result.text)))
            
            # Calculate costs
            cost_config = COST_PER_TOKEN.get(model_name, COST_PER_TOKEN["default"])
            input_cost = Decimal(prompt_tokens) * Decimal(cost_config["input"]) / Decimal(1_000_000)
            output_cost = Decimal(response_tokens) * Decimal(cost_config["output"]) / Decimal(1_000_000)
            total_cost = input_cost + output_cost
            
            # Prepare response for logging
            response_data = {
                "text": result.text,
                "message": result.message.dict() if hasattr(result, "message") else None,
                "generation_info": result.generation_info if hasattr(result, "generation_info") else None,
            }
            
            # Update log
            if self.db:
                llm_log.response = response_data
                llm_log.response_length = len(str(result.text))
                llm_log.prompt_tokens = prompt_tokens
                llm_log.response_tokens = response_tokens
                llm_log.input_cost = input_cost
                llm_log.output_cost = output_cost
                llm_log.total_cost = total_cost
                llm_log.latency_ms = latency_ms
                llm_log.success = True
                llm_log.completed_at = datetime.utcnow()
                llm_log.finish_reason = getattr(result, "finish_reason", "stop")
                self.db.commit()
            
            logger.info(
                f"LLM call logged: call_id={call_id}, model={model_name}, "
                f"tokens={prompt_tokens}+{response_tokens}, cost=${total_cost:.6f}, latency={latency_ms}ms"
            )
            
            return result
            
        except Exception as e:
            # Log error
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            if self.db:
                llm_log.error_type = type(e).__name__
                llm_log.error_message = str(e)
                llm_log.latency_ms = latency_ms
                llm_log.completed_at = datetime.utcnow()
                self.db.commit()
            
            logger.error(f"LLM call failed: call_id={call_id}, error={e}", exc_info=True)
            raise
    
    def _estimate_tokens(self, text_length: int) -> int:
        """Estimate token count from character length (rough approximation)."""
        # Average: 1 token ≈ 4 characters for English
        return int(text_length / 4)
    
    @property
    def _llm_type(self) -> str:
        return "tracing_wrapper"
    
    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        """Streaming support (delegates to wrapped model)."""
        return self.model._stream(messages, stop=stop, run_manager=run_manager, **kwargs)


def get_traced_chat_model(
    db: Session,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    user_id: Optional[int] = None,
    deal_id: Optional[int] = None,
    document_id: Optional[int] = None,
    workflow_id: Optional[int] = None,
    trace_id: Optional[str] = None,
    parent_call_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> TracingChatModel:
    """
    Get a traced chat model that automatically logs all calls.
    
    Args:
        db: Database session
        model: Model name (uses default if not provided)
        temperature: Temperature override
        user_id: User ID for audit
        deal_id: Deal ID for context
        document_id: Document ID for context
        workflow_id: Workflow ID for context
        trace_id: Trace ID for correlation
        parent_call_id: Parent LLM call ID (for chained calls)
        metadata: Additional metadata
        **kwargs: Additional model arguments
    
    Returns:
        TracingChatModel instance
    """
    # Get base model
    base_model = get_chat_model(model=model, temperature=temperature, **kwargs)
    
    # Extract provider/model from config
    from app.core.llm_client import _llm_config
    provider = _llm_config.get("provider", "unknown") if _llm_config else "unknown"
    model_name = model or (_llm_config.get("model", "unknown") if _llm_config else "unknown")
    
    # Add provider/model to metadata
    tracing_metadata = metadata or {}
    tracing_metadata.update({
        "provider": provider,
        "model": model_name,
    })
    
    return TracingChatModel(
        model=base_model,
        db=db,
        user_id=user_id,
        deal_id=deal_id,
        document_id=document_id,
        workflow_id=workflow_id,
        trace_id=trace_id,
        parent_call_id=parent_call_id,
        metadata=tracing_metadata
    )
```

#### Task 1.1.3: Update LLM Client to Use Tracing

**File**: `app/core/llm_client.py` (UPDATE)

Add optional tracing parameter to `get_chat_model()`:

```python
def get_chat_model(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    enable_tracing: bool = False,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    deal_id: Optional[int] = None,
    document_id: Optional[int] = None,
    workflow_id: Optional[int] = None,
    trace_id: Optional[str] = None,
    **kwargs
) -> BaseChatModel:
    """
    Get a chat model instance with optional tracing.
    
    If enable_tracing=True, returns TracingChatModel that logs all calls.
    Otherwise, returns standard model.
    """
    if enable_tracing and db:
        from app.core.llm_tracing import get_traced_chat_model
        return get_traced_chat_model(
            db=db,
            model=model,
            temperature=temperature,
            user_id=user_id,
            deal_id=deal_id,
            document_id=document_id,
            workflow_id=workflow_id,
            trace_id=trace_id,
            **kwargs
        )
    else:
        # Standard implementation (existing code)
        ...
```

#### Task 1.1.4: Create LLM Call Audit Service

**File**: `app/services/llm_audit_service.py` (NEW)

```python
"""
LLM Call Audit Service for querying and analyzing LLM call logs.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.db.models import LLMCallLog

logger = logging.getLogger(__name__)


class LLMAuditService:
    """Service for querying and analyzing LLM call logs."""
    
    def get_llm_calls(
        self,
        db: Session,
        user_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        document_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        success: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        trace_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[LLMCallLog], int]:
        """Query LLM call logs with filtering."""
        query = db.query(LLMCallLog)
        
        if user_id:
            query = query.filter(LLMCallLog.user_id == user_id)
        if deal_id:
            query = query.filter(LLMCallLog.deal_id == deal_id)
        if document_id:
            query = query.filter(LLMCallLog.document_id == document_id)
        if workflow_id:
            query = query.filter(LLMCallLog.workflow_id == workflow_id)
        if provider:
            query = query.filter(LLMCallLog.provider == provider)
        if model:
            query = query.filter(LLMCallLog.model == model)
        if success is not None:
            query = query.filter(LLMCallLog.success == success)
        if start_date:
            query = query.filter(LLMCallLog.called_at >= start_date)
        if end_date:
            query = query.filter(LLMCallLog.called_at <= end_date)
        if trace_id:
            query = query.filter(LLMCallLog.trace_id == trace_id)
        
        total = query.count()
        logs = query.order_by(LLMCallLog.called_at.desc()).offset(offset).limit(limit).all()
        
        return logs, total
    
    def get_cost_statistics(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get cost statistics for LLM calls."""
        query = db.query(
            func.sum(LLMCallLog.total_cost).label("total_cost"),
            func.sum(LLMCallLog.prompt_tokens).label("total_input_tokens"),
            func.sum(LLMCallLog.response_tokens).label("total_output_tokens"),
            func.count(LLMCallLog.id).label("total_calls"),
            func.avg(LLMCallLog.latency_ms).label("avg_latency_ms")
        ).filter(LLMCallLog.success == True)
        
        if start_date:
            query = query.filter(LLMCallLog.called_at >= start_date)
        if end_date:
            query = query.filter(LLMCallLog.called_at <= end_date)
        if provider:
            query = query.filter(LLMCallLog.provider == provider)
        if model:
            query = query.filter(LLMCallLog.model == model)
        
        result = query.first()
        
        return {
            "total_cost": float(result.total_cost) if result.total_cost else 0.0,
            "total_input_tokens": result.total_input_tokens or 0,
            "total_output_tokens": result.total_output_tokens or 0,
            "total_calls": result.total_calls or 0,
            "avg_latency_ms": float(result.avg_latency_ms) if result.avg_latency_ms else 0.0,
        }
    
    def get_trace_chain(
        self,
        db: Session,
        trace_id: str
    ) -> List[LLMCallLog]:
        """Get all LLM calls in a trace chain."""
        return db.query(LLMCallLog).filter(
            LLMCallLog.trace_id == trace_id
        ).order_by(LLMCallLog.called_at.asc()).all()
```

#### Task 1.1.5: Add LLM Call Audit API Endpoints

**File**: `app/api/auditor_routes.py` (UPDATE)

Add endpoints:

```python
@router.get("/llm-calls")
async def get_llm_calls(
    user_id: Optional[int] = Query(None),
    deal_id: Optional[int] = Query(None),
    trace_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    llm_audit_service: LLMAuditService = Depends(get_llm_audit_service)
):
    """Get LLM call logs (requires AUDIT_VIEW permission)."""
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Parse dates, apply filters, return logs
    ...

@router.get("/llm-calls/{call_id}")
async def get_llm_call_detail(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get detailed LLM call log with prompt and response (requires AUDIT_VIEW)."""
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Return full log including encrypted prompt/response
    ...

@router.get("/llm-calls/statistics/costs")
async def get_llm_cost_statistics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    llm_audit_service: LLMAuditService = Depends(get_llm_audit_service)
):
    """Get LLM cost statistics (requires AUDIT_VIEW)."""
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Return cost statistics
    ...
```

---

### Project 2: Blockchain Transaction Audit Logging

**Objective**: Log all blockchain transactions with full traceability including transaction hashes, block numbers, gas costs, and event logs.

#### Task 2.1.1: Create BlockchainTransactionLog Model

**File**: `app/db/models.py` (UPDATE)

```python
class BlockchainTransactionLog(Base):
    """Audit log for all blockchain transactions."""
    
    __tablename__ = "blockchain_transaction_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Transaction identification
    transaction_hash = Column(String(66), unique=True, nullable=False, index=True)  # 0x...
    block_number = Column(BigInteger, nullable=True, index=True)
    block_hash = Column(String(66), nullable=True)
    transaction_index = Column(Integer, nullable=True)
    
    # Contract and function
    contract_address = Column(String(42), nullable=False, index=True)  # 0x...
    contract_name = Column(String(100), nullable=True)  # SecuritizationToken, etc.
    function_name = Column(String(100), nullable=True)  # mintTranche, distributePayment, etc.
    
    # Transaction details
    from_address = Column(String(42), nullable=False, index=True)  # Sender
    to_address = Column(String(42), nullable=True)  # Recipient (contract)
    value = Column(Numeric(36, 18), nullable=True)  # ETH value
    gas_price = Column(BigInteger, nullable=True)  # Wei
    gas_used = Column(BigInteger, nullable=True)
    gas_limit = Column(BigInteger, nullable=True)
    gas_cost_eth = Column(Numeric(36, 18), nullable=True)  # gas_used * gas_price
    
    # Status
    status = Column(String(20), nullable=False, index=True)  # pending, confirmed, failed
    confirmed_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # Event logs
    event_logs = Column(JSONB, nullable=True)  # Decoded event logs
    
    # Context and relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    notarization_id = Column(Integer, ForeignKey("notarization_records.id"), nullable=True, index=True)
    securitization_pool_id = Column(Integer, ForeignKey("securitization_pools.id"), nullable=True, index=True)
    
    # Metadata
    metadata = Column(JSONB, nullable=True)  # Function parameters, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", backref="blockchain_transactions")
    deal = relationship("Deal", backref="blockchain_transactions")
    notarization = relationship("NotarizationRecord", backref="blockchain_transactions")
    securitization_pool = relationship("SecuritizationPool", backref="blockchain_transactions")
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "contract_address": self.contract_address,
            "contract_name": self.contract_name,
            "function_name": self.function_name,
            "from_address": self.from_address,
            "status": self.status,
            "gas_used": self.gas_used,
            "gas_cost_eth": float(self.gas_cost_eth) if self.gas_cost_eth else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
```

#### Task 2.1.2: Update BlockchainService to Log Transactions

**File**: `app/services/blockchain_service.py` (UPDATE)

Add transaction logging to all blockchain operations:

```python
def _log_transaction(
    self,
    db: Session,
    transaction_hash: str,
    contract_address: str,
    contract_name: str,
    function_name: str,
    from_address: str,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    deal_id: Optional[int] = None,
    notarization_id: Optional[int] = None,
    securitization_pool_id: Optional[int] = None
) -> BlockchainTransactionLog:
    """Log blockchain transaction."""
    from app.db.models import BlockchainTransactionLog
    
    log = BlockchainTransactionLog(
        transaction_hash=transaction_hash,
        contract_address=contract_address,
        contract_name=contract_name,
        function_name=function_name,
        from_address=from_address,
        status="pending",
        metadata=metadata,
        user_id=user_id,
        deal_id=deal_id,
        notarization_id=notarization_id,
        securitization_pool_id=securitization_pool_id
    )
    
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log

def _update_transaction_status(
    self,
    db: Session,
    transaction_hash: str,
    receipt: Any  # Web3 transaction receipt
):
    """Update transaction log with block confirmation details."""
    from app.db.models import BlockchainTransactionLog
    
    log = db.query(BlockchainTransactionLog).filter(
        BlockchainTransactionLog.transaction_hash == transaction_hash
    ).first()
    
    if not log:
        logger.warning(f"Transaction log not found: {transaction_hash}")
        return
    
    log.block_number = receipt.blockNumber
    log.block_hash = receipt.blockHash.hex()
    log.transaction_index = receipt.transactionIndex
    log.gas_used = receipt.gasUsed
    log.gas_price = receipt.effectiveGasPrice if hasattr(receipt, "effectiveGasPrice") else None
    
    if log.gas_used and log.gas_price:
        log.gas_cost_eth = Decimal(log.gas_used) * Decimal(log.gas_price) / Decimal(10**18)
    
    log.status = "confirmed" if receipt.status == 1 else "failed"
    log.confirmed_at = datetime.utcnow()
    
    if receipt.status != 1:
        log.failure_reason = "Transaction reverted"
    
    # Decode and store event logs
    if receipt.logs:
        log.event_logs = [self._decode_event_log(log_entry) for log_entry in receipt.logs]
    
    db.commit()
    
    logger.info(
        f"Transaction confirmed: {transaction_hash}, block={log.block_number}, "
        f"status={log.status}, gas_used={log.gas_used}"
    )
```

Update `mint_tranche_token()` and `distribute_payment_to_tranche()` to log transactions.

#### Task 2.1.3: Create Blockchain Audit Service

**File**: `app/services/blockchain_audit_service.py` (NEW)

```python
"""
Blockchain Transaction Audit Service for querying and analyzing blockchain transactions.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import BlockchainTransactionLog

logger = logging.getLogger(__name__)


class BlockchainAuditService:
    """Service for querying and analyzing blockchain transaction logs."""
    
    def get_transactions(
        self,
        db: Session,
        user_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        contract_address: Optional[str] = None,
        contract_name: Optional[str] = None,
        function_name: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[BlockchainTransactionLog], int]:
        """Query blockchain transactions with filtering."""
        query = db.query(BlockchainTransactionLog)
        
        if user_id:
            query = query.filter(BlockchainTransactionLog.user_id == user_id)
        if deal_id:
            query = query.filter(BlockchainTransactionLog.deal_id == deal_id)
        if contract_address:
            query = query.filter(BlockchainTransactionLog.contract_address == contract_address)
        if contract_name:
            query = query.filter(BlockchainTransactionLog.contract_name == contract_name)
        if function_name:
            query = query.filter(BlockchainTransactionLog.function_name == function_name)
        if status:
            query = query.filter(BlockchainTransactionLog.status == status)
        if start_date:
            query = query.filter(BlockchainTransactionLog.created_at >= start_date)
        if end_date:
            query = query.filter(BlockchainTransactionLog.created_at <= end_date)
        
        total = query.count()
        transactions = query.order_by(
            BlockchainTransactionLog.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return transactions, total
    
    def get_gas_statistics(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get gas cost statistics."""
        query = db.query(
            func.sum(BlockchainTransactionLog.gas_cost_eth).label("total_gas_cost"),
            func.sum(BlockchainTransactionLog.gas_used).label("total_gas_used"),
            func.count(BlockchainTransactionLog.id).label("total_transactions"),
            func.avg(BlockchainTransactionLog.gas_used).label("avg_gas_used")
        ).filter(BlockchainTransactionLog.status == "confirmed")
        
        if start_date:
            query = query.filter(BlockchainTransactionLog.created_at >= start_date)
        if end_date:
            query = query.filter(BlockchainTransactionLog.created_at <= end_date)
        
        result = query.first()
        
        return {
            "total_gas_cost_eth": float(result.total_gas_cost) if result.total_gas_cost else 0.0,
            "total_gas_used": result.total_gas_used or 0,
            "total_transactions": result.total_transactions or 0,
            "avg_gas_used": float(result.avg_gas_used) if result.avg_gas_used else 0.0,
        }
```

#### Task 2.1.4: Add Blockchain Audit API Endpoints

**File**: `app/api/auditor_routes.py` (UPDATE)

Add endpoints:

```python
@router.get("/blockchain-transactions")
async def get_blockchain_transactions(
    deal_id: Optional[int] = Query(None),
    contract_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    blockchain_audit_service: BlockchainAuditService = Depends(get_blockchain_audit_service)
):
    """Get blockchain transaction logs (requires AUDIT_VIEW permission)."""
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Parse dates, apply filters, return transactions
    ...

@router.get("/blockchain-transactions/{tx_hash}")
async def get_blockchain_transaction_detail(
    tx_hash: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get detailed blockchain transaction with event logs (requires AUDIT_VIEW)."""
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Return full transaction log
    ...
```

---

### Project 3: Analysis Report Notarization

**Objective**: Enable notarization for signed analysis reports with blockchain verification.

#### Task 3.1.1: Create AnalysisReportNotarization Model

**File**: `app/db/models.py` (UPDATE)

```python
class AnalysisReportNotarization(Base):
    """Notarization records for analysis reports."""
    
    __tablename__ = "analysis_report_notarizations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Report identification
    report_id = Column(String(255), nullable=False, index=True)  # Analysis report ID
    report_type = Column(String(50), nullable=False)  # quantitative_analysis, deep_research, etc.
    report_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256 hash of report
    
    # Notarization details
    notarization_hash = Column(String(64), nullable=True)  # Hash stored on blockchain
    blockchain_tx_hash = Column(String(66), nullable=True, index=True)  # Transaction hash
    blockchain_block_number = Column(BigInteger, nullable=True)
    
    # Signatures
    signer_wallet_address = Column(String(42), nullable=False, index=True)
    signature = Column(Text, nullable=False)  # Ethereum signature
    signed_message = Column(Text, nullable=False)
    signed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Status
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, signed, notarized, verified
    
    # Context
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    
    # Metadata
    metadata = Column(JSONB, nullable=True)  # Report metadata, CDM event ID, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    notarized_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="analysis_report_notarizations")
    deal = relationship("Deal", backref="analysis_report_notarizations")
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "report_id": self.report_id,
            "report_type": self.report_type,
            "report_hash": self.report_hash,
            "blockchain_tx_hash": self.blockchain_tx_hash,
            "status": self.status,
            "signed_at": self.signed_at.isoformat() if self.signed_at else None,
            "notarized_at": self.notarized_at.isoformat() if self.notarized_at else None,
        }
```

#### Task 3.1.2: Create Analysis Report Notarization Service

**File**: `app/services/analysis_report_notarization_service.py` (NEW)

```python
"""
Analysis Report Notarization Service.

Handles notarization of signed analysis reports with blockchain verification.
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import AnalysisReportNotarization
from app.utils.crypto_verification import verify_ethereum_signature, generate_signing_message
from app.services.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)


class AnalysisReportNotarizationService:
    """Service for notarizing analysis reports."""
    
    def __init__(self, db: Session):
        self.db = db
        self.blockchain_service = BlockchainService()
    
    def create_notarization_request(
        self,
        report_id: str,
        report_type: str,
        report_data: Dict[str, Any],
        signer_wallet_address: str,
        user_id: Optional[int] = None,
        deal_id: Optional[int] = None
    ) -> AnalysisReportNotarization:
        """Create notarization request for analysis report."""
        # Generate report hash
        report_json = json.dumps(report_data, sort_keys=True)
        report_hash = hashlib.sha256(report_json.encode()).hexdigest()
        
        # Generate signing message
        message = generate_signing_message(
            nonce=datetime.utcnow().isoformat(),
            timestamp=datetime.utcnow().isoformat(),
            deal_id=deal_id,
            verification_id=None
        )
        message_with_hash = f"{message}\n\nReport Hash: {report_hash}"
        
        notarization = AnalysisReportNotarization(
            report_id=report_id,
            report_type=report_type,
            report_hash=report_hash,
            signer_wallet_address=signer_wallet_address,
            signed_message=message_with_hash,
            status="pending",
            user_id=user_id,
            deal_id=deal_id,
            metadata={"report_data_summary": self._summarize_report(report_data)}
        )
        
        self.db.add(notarization)
        self.db.commit()
        self.db.refresh(notarization)
        
        logger.info(
            f"Created analysis report notarization request: report_id={report_id}, "
            f"hash={report_hash[:16]}..."
        )
        
        return notarization
    
    def verify_and_store_signature(
        self,
        notarization_id: int,
        signature: str
    ) -> AnalysisReportNotarization:
        """Verify signature and store in notarization record."""
        notarization = self.db.query(AnalysisReportNotarization).filter(
            AnalysisReportNotarization.id == notarization_id
        ).first()
        
        if not notarization:
            raise ValueError(f"Notarization {notarization_id} not found")
        
        # Verify signature
        is_valid = verify_ethereum_signature(
            message=notarization.signed_message,
            signature=signature,
            wallet_address=notarization.signer_wallet_address
        )
        
        if not is_valid:
            raise ValueError("Invalid signature")
        
        notarization.signature = signature
        notarization.status = "signed"
        notarization.signed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(notarization)
        
        # Automatically notarize on blockchain
        self._notarize_on_blockchain(notarization)
        
        return notarization
    
    def _notarize_on_blockchain(
        self,
        notarization: AnalysisReportNotarization
    ):
        """Notarize report hash on blockchain."""
        if not self.blockchain_service.is_connected():
            logger.warning("Blockchain not connected, skipping notarization")
            return
        
        try:
            # Use SecuritizationNotarization contract to store hash
            # For now, we'll create a placeholder transaction
            # In production, this would call the contract's createNotarization function
            
            # Log transaction (will be updated when transaction confirms)
            from app.db.models import BlockchainTransactionLog
            tx_hash = f"0x{hashlib.sha256(f'{notarization.report_hash}{datetime.utcnow()}'.encode()).hexdigest()[:64]}"
            
            blockchain_log = BlockchainTransactionLog(
                transaction_hash=tx_hash,
                contract_address="0x...",  # SecuritizationNotarization contract
                contract_name="SecuritizationNotarization",
                function_name="notarizeReport",
                from_address=notarization.signer_wallet_address,
                status="pending",
                metadata={
                    "report_id": notarization.report_id,
                    "report_hash": notarization.report_hash,
                    "notarization_id": notarization.id
                },
                user_id=notarization.user_id,
                deal_id=notarization.deal_id
            )
            
            self.db.add(blockchain_log)
            self.db.commit()
            
            notarization.blockchain_tx_hash = tx_hash
            notarization.status = "notarized"
            notarization.notarized_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(
                f"Notarized analysis report on blockchain: report_id={notarization.report_id}, "
                f"tx_hash={tx_hash}"
            )
            
        except Exception as e:
            logger.error(f"Failed to notarize on blockchain: {e}", exc_info=True)
            # Don't fail the notarization if blockchain fails
    
    def _summarize_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of report data for metadata."""
        return {
            "keys": list(report_data.keys()),
            "size": len(json.dumps(report_data)),
            "has_findings": "findings" in report_data or "conclusion" in report_data,
        }
```

#### Task 3.1.3: Integrate Notarization with Analysis Report Generation

**File**: `app/services/quantitative_analysis_service.py` (UPDATE)

Add notarization option when generating reports:

```python
async def analyze_company(
    self,
    query: str,
    ...
    notarize_report: bool = False,
    signer_wallet_address: Optional[str] = None,
    ...
) -> Dict[str, Any]:
    """Analyze company with optional notarization."""
    # ... existing analysis code ...
    
    result = {
        "analysis_id": analysis_id,
        "final_report": final_report,
        "market_data": market_data,
        ...
    }
    
    # Notarize if requested
    if notarize_report and signer_wallet_address:
        from app.services.analysis_report_notarization_service import AnalysisReportNotarizationService
        notarization_service = AnalysisReportNotarizationService(self.db)
        
        notarization = notarization_service.create_notarization_request(
            report_id=analysis_id,
            report_type="quantitative_analysis",
            report_data=result,
            signer_wallet_address=signer_wallet_address,
            user_id=user_id,
            deal_id=deal_id
        )
        
        result["notarization"] = {
            "notarization_id": notarization.id,
            "report_hash": notarization.report_hash,
            "status": notarization.status,
            "signed_message": notarization.signed_message
        }
    
    return result
```

---

### Project 4: Enhanced Workflow Traceability

**Objective**: Log all workflow state transitions, agent coordination, and tool usage with full traceability.

#### Task 4.1.1: Create WorkflowTrace Model

**File**: `app/db/models.py` (UPDATE)

```python
class WorkflowTrace(Base):
    """Comprehensive trace for workflow execution."""
    
    __tablename__ = "workflow_traces"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Trace identification
    trace_id = Column(String(255), unique=True, nullable=False, index=True)  # UUID
    parent_trace_id = Column(String(255), nullable=True, index=True)  # For nested workflows
    
    # Workflow identification
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True, index=True)
    workflow_type = Column(String(50), nullable=False, index=True)  # extraction, analysis, audit, etc.
    
    # State and execution
    state = Column(String(50), nullable=False, index=True)  # started, running, completed, failed
    previous_state = Column(String(50), nullable=True)
    state_transition_reason = Column(Text, nullable=True)
    
    # Agent and tool information
    agent_name = Column(String(100), nullable=True)  # analyzer, verifier, classifier, etc.
    tool_name = Column(String(100), nullable=True)  # Tool used in this step
    tool_parameters = Column(JSONB, nullable=True)  # Tool input parameters
    tool_result = Column(JSONB, nullable=True)  # Tool output (may be large)
    
    # LLM call linkage
    llm_call_id = Column(String(255), ForeignKey("llm_call_logs.call_id"), nullable=True, index=True)
    
    # Policy decision linkage
    policy_decision_id = Column(Integer, ForeignKey("policy_decisions.id"), nullable=True, index=True)
    
    # Error tracking
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Performance
    duration_ms = Column(Integer, nullable=True)  # Step duration
    
    # Context
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    
    # Metadata
    metadata = Column(JSONB, nullable=True)  # Additional context
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    workflow = relationship("Workflow", backref="traces")
    user = relationship("User", backref="workflow_traces")
    deal = relationship("Deal", backref="workflow_traces")
    document = relationship("Document", backref="workflow_traces")
    llm_call = relationship("LLMCallLog", foreign_keys=[llm_call_id], backref="workflow_traces")
    policy_decision = relationship("PolicyDecision", backref="workflow_traces")
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "workflow_type": self.workflow_type,
            "state": self.state,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
```

#### Task 4.1.2: Create Workflow Tracing Service

**File**: `app/services/workflow_tracing_service.py` (NEW)

```python
"""
Workflow Tracing Service for comprehensive workflow execution logging.
"""

import logging
import uuid
import time
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import WorkflowTrace

logger = logging.getLogger(__name__)


class WorkflowTracingService:
    """Service for tracing workflow execution."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def start_trace(
        self,
        workflow_type: str,
        workflow_id: Optional[int] = None,
        parent_trace_id: Optional[str] = None,
        user_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        document_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new workflow trace and return trace_id."""
        trace_id = str(uuid.uuid4())
        
        trace = WorkflowTrace(
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            state="started",
            user_id=user_id,
            deal_id=deal_id,
            document_id=document_id,
            metadata=metadata,
            started_at=datetime.utcnow()
        )
        
        self.db.add(trace)
        self.db.commit()
        
        logger.info(f"Started workflow trace: trace_id={trace_id}, type={workflow_type}")
        
        return trace_id
    
    def log_state_transition(
        self,
        trace_id: str,
        new_state: str,
        reason: Optional[str] = None,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_parameters: Optional[Dict[str, Any]] = None,
        tool_result: Optional[Dict[str, Any]] = None,
        llm_call_id: Optional[str] = None,
        policy_decision_id: Optional[int] = None
    ):
        """Log a state transition in workflow execution."""
        trace = self.db.query(WorkflowTrace).filter(
            WorkflowTrace.trace_id == trace_id
        ).first()
        
        if not trace:
            logger.warning(f"Trace not found: {trace_id}")
            return
        
        trace.previous_state = trace.state
        trace.state = new_state
        trace.state_transition_reason = reason
        trace.agent_name = agent_name
        trace.tool_name = tool_name
        trace.tool_parameters = tool_parameters
        trace.tool_result = tool_result
        trace.llm_call_id = llm_call_id
        trace.policy_decision_id = policy_decision_id
        
        if new_state in ["completed", "failed"]:
            trace.completed_at = datetime.utcnow()
            if trace.started_at:
                duration = (trace.completed_at - trace.started_at).total_seconds() * 1000
                trace.duration_ms = int(duration)
        
        self.db.commit()
        
        logger.debug(
            f"Workflow state transition: trace_id={trace_id}, "
            f"{trace.previous_state} -> {new_state}, agent={agent_name}, tool={tool_name}"
        )
    
    def log_error(
        self,
        trace_id: str,
        error_type: str,
        error_message: str,
        retry_count: int = 0
    ):
        """Log an error in workflow execution."""
        trace = self.db.query(WorkflowTrace).filter(
            WorkflowTrace.trace_id == trace_id
        ).first()
        
        if not trace:
            logger.warning(f"Trace not found: {trace_id}")
            return
        
        trace.state = "failed"
        trace.error_type = error_type
        trace.error_message = error_message
        trace.retry_count = retry_count
        trace.completed_at = datetime.utcnow()
        
        if trace.started_at:
            duration = (trace.completed_at - trace.started_at).total_seconds() * 1000
            trace.duration_ms = int(duration)
        
        self.db.commit()
        
        logger.error(
            f"Workflow error logged: trace_id={trace_id}, error={error_type}: {error_message}"
        )
    
    def get_trace_chain(
        self,
        trace_id: str
    ) -> List[WorkflowTrace]:
        """Get full trace chain including parent traces."""
        traces = []
        current_trace_id = trace_id
        
        while current_trace_id:
            trace = self.db.query(WorkflowTrace).filter(
                WorkflowTrace.trace_id == current_trace_id
            ).first()
            
            if not trace:
                break
            
            traces.append(trace)
            current_trace_id = trace.parent_trace_id
        
        return list(reversed(traces))  # Return in chronological order
```

#### Task 4.1.3: Integrate Tracing with Agent Workflows

**File**: `app/agents/audit_workflow.py` (UPDATE)

Add tracing to workflow execution:

```python
async def run_full_audit(
    loan_id: str,
    document_text: str,
    db_session=None,
    ...
) -> AuditResult:
    """Run full audit with comprehensive tracing."""
    from app.services.workflow_tracing_service import WorkflowTracingService
    
    tracing_service = WorkflowTracingService(db_session)
    trace_id = tracing_service.start_trace(
        workflow_type="audit",
        user_id=user_id,
        deal_id=deal_id,
        metadata={"loan_id": loan_id}
    )
    
    try:
        # Log each step
        tracing_service.log_state_transition(
            trace_id=trace_id,
            new_state="running",
            agent_name="analyzer",
            tool_name="extract_spt"
        )
        
        # ... perform extraction ...
        
        # Link LLM call if available
        if llm_call_id:
            tracing_service.log_state_transition(
                trace_id=trace_id,
                new_state="running",
                agent_name="analyzer",
                llm_call_id=llm_call_id
            )
        
        # ... continue workflow ...
        
        tracing_service.log_state_transition(
            trace_id=trace_id,
            new_state="completed",
            reason="Audit completed successfully"
        )
        
    except Exception as e:
        tracing_service.log_error(
            trace_id=trace_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise
    
    return result
```

---

### Project 5: Permissioned Audit Dashboard Access

**Objective**: Ensure audit dashboard is accessible to all users with proper permission-based data filtering.

#### Task 5.1.1: Update Audit Service with Permission-Based Filtering

**File**: `app/services/audit_service.py` (UPDATE)

Add permission-based filtering:

```python
def get_audit_logs(
    self,
    db: Session,
    current_user: User,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metadata_filter: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[List[AuditLog], int]:
    """Query audit logs with permission-based filtering."""
    from app.core.permissions import has_permission, PERMISSION_AUDIT_VIEW_ALL
    
    query = db.query(AuditLog).options(joinedload(AuditLog.user))
    
    # Permission-based filtering
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW_ALL):
        # Regular users can only see their own logs or logs for their organization
        if current_user.organization_id:
            # Filter by organization
            query = query.join(User).filter(
                User.organization_id == current_user.organization_id
            )
        else:
            # Filter by user_id only
            query = query.filter(AuditLog.user_id == current_user.id)
    
    # Apply other filters...
    ...
    
    return logs, total
```

#### Task 5.1.2: Add Permission Constants

**File**: `app/core/permissions.py` (UPDATE)

Add new permission:

```python
# Audit Permissions
PERMISSION_AUDIT_VIEW = "AUDIT_VIEW"  # View own/organization audit logs
PERMISSION_AUDIT_VIEW_ALL = "AUDIT_VIEW_ALL"  # View all audit logs (admin)
PERMISSION_AUDIT_EXPORT = "AUDIT_EXPORT"
PERMISSION_AUDIT_CREATE = "AUDIT_CREATE"
```

#### Task 5.1.3: Update Audit Dashboard UI with Permission Checks

**File**: `client/src/apps/auditor/AuditDashboard.tsx` (UPDATE)

Add permission-based UI rendering:

```typescript
import { usePermissions } from '@/hooks/usePermissions';

export function AuditDashboard({ showLogsOnly = false }: { showLogsOnly?: boolean }) {
  const { hasPermission } = usePermissions();
  const canViewAll = hasPermission('AUDIT_VIEW_ALL');
  const canViewOwn = hasPermission('AUDIT_VIEW');
  
  // Show organization filter only if user can view all
  // Show user filter only if user can view all
  // ...
}
```

---

### Project 6: Comprehensive Trace Correlation

**Objective**: Link all traces (LLM calls, policy decisions, workflows, blockchain) with correlation IDs.

#### Task 6.1.1: Create TraceCorrelation Service

**File**: `app/services/trace_correlation_service.py` (NEW)

```python
"""
Trace Correlation Service for linking related traces across systems.
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.models import (
    AuditLog, PolicyDecision, LLMCallLog, WorkflowTrace,
    BlockchainTransactionLog, AnalysisReportNotarization
)

logger = logging.getLogger(__name__)


class TraceCorrelationService:
    """Service for correlating traces across systems."""
    
    def get_related_traces(
        self,
        db: Session,
        trace_id: Optional[str] = None,
        deal_id: Optional[int] = None,
        document_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all related traces for a given context."""
        traces = {
            "audit_logs": [],
            "policy_decisions": [],
            "llm_calls": [],
            "workflow_traces": [],
            "blockchain_transactions": [],
            "notarizations": []
        }
        
        # Get audit logs
        if trace_id:
            audit_logs = db.query(AuditLog).filter(
                AuditLog.action_metadata.has_key("trace_id")
            ).filter(
                AuditLog.action_metadata["trace_id"].astext == trace_id
            ).all()
        elif deal_id:
            audit_logs = db.query(AuditLog).filter(
                or_(
                    AuditLog.target_type == "deal",
                    AuditLog.target_id == deal_id
                )
            ).all()
        else:
            audit_logs = []
        
        traces["audit_logs"] = [log.to_dict() for log in audit_logs]
        
        # Get policy decisions
        if trace_id:
            policy_decisions = db.query(PolicyDecision).filter(
                PolicyDecision.trace_id == trace_id
            ).all()
        elif deal_id:
            policy_decisions = db.query(PolicyDecision).filter(
                PolicyDecision.deal_id == deal_id
            ).all()
        else:
            policy_decisions = []
        
        traces["policy_decisions"] = [pd.to_dict() for pd in policy_decisions]
        
        # Get LLM calls
        if trace_id:
            llm_calls = db.query(LLMCallLog).filter(
                LLMCallLog.trace_id == trace_id
            ).all()
        elif deal_id:
            llm_calls = db.query(LLMCallLog).filter(
                LLMCallLog.deal_id == deal_id
            ).all()
        else:
            llm_calls = []
        
        traces["llm_calls"] = [call.to_dict() for call in llm_calls]
        
        # Get workflow traces
        if trace_id:
            workflow_traces = db.query(WorkflowTrace).filter(
                WorkflowTrace.trace_id == trace_id
            ).all()
        elif workflow_id:
            workflow_traces = db.query(WorkflowTrace).filter(
                WorkflowTrace.workflow_id == workflow_id
            ).all()
        else:
            workflow_traces = []
        
        traces["workflow_traces"] = [trace.to_dict() for trace in workflow_traces]
        
        # Get blockchain transactions
        if deal_id:
            blockchain_txs = db.query(BlockchainTransactionLog).filter(
                BlockchainTransactionLog.deal_id == deal_id
            ).all()
        else:
            blockchain_txs = []
        
        traces["blockchain_transactions"] = [tx.to_dict() for tx in blockchain_txs]
        
        # Get notarizations
        if deal_id:
            notarizations = db.query(AnalysisReportNotarization).filter(
                AnalysisReportNotarization.deal_id == deal_id
            ).all()
        else:
            notarizations = []
        
        traces["notarizations"] = [not.to_dict() for not in notarizations]
        
        return traces
```

#### Task 6.1.2: Add Trace Correlation API Endpoint

**File**: `app/api/auditor_routes.py` (UPDATE)

Add endpoint:

```python
@router.get("/traces/correlate")
async def get_correlated_traces(
    trace_id: Optional[str] = Query(None),
    deal_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    workflow_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    correlation_service: TraceCorrelationService = Depends(get_trace_correlation_service)
):
    """Get all correlated traces for a given context (requires AUDIT_VIEW)."""
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    traces = correlation_service.get_related_traces(
        db=db,
        trace_id=trace_id,
        deal_id=deal_id,
        document_id=document_id,
        workflow_id=workflow_id,
        user_id=current_user.id if not has_permission(current_user, PERMISSION_AUDIT_VIEW_ALL) else None
    )
    
    return {
        "status": "success",
        "traces": traces
    }
```

---

## Database Migrations

### Migration 1: LLM Call Logs

**File**: `alembic/versions/XXXX_add_llm_call_logs.py`

```python
def upgrade():
    op.create_table(
        'llm_call_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('call_id', sa.String(255), nullable=False),
        sa.Column('trace_id', sa.String(255), nullable=True),
        sa.Column('parent_call_id', sa.String(255), nullable=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(255), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('prompt', sa.JSON(), nullable=False),  # EncryptedJSON
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('prompt_length', sa.Integer(), nullable=False),
        sa.Column('response', sa.JSON(), nullable=True),  # EncryptedJSON
        sa.Column('response_tokens', sa.Integer(), nullable=True),
        sa.Column('response_length', sa.Integer(), nullable=True),
        sa.Column('finish_reason', sa.String(50), nullable=True),
        sa.Column('input_cost', sa.Numeric(10, 6), nullable=True),
        sa.Column('output_cost', sa.Numeric(10, 6), nullable=True),
        sa.Column('total_cost', sa.Numeric(10, 6), nullable=True),
        sa.Column('currency', sa.String(10), default='USD', nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0, nullable=False),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), default=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('deal_id', sa.Integer(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('workflow_id', sa.Integer(), nullable=True),
        sa.Column('policy_decision_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('called_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id']),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
        sa.ForeignKeyConstraint(['policy_decision_id'], ['policy_decisions.id']),
        sa.ForeignKeyConstraint(['parent_call_id'], ['llm_call_logs.call_id']),
    )
    op.create_index('ix_llm_call_logs_call_id', 'llm_call_logs', ['call_id'], unique=True)
    op.create_index('ix_llm_call_logs_trace_id', 'llm_call_logs', ['trace_id'])
    op.create_index('ix_llm_call_logs_provider', 'llm_call_logs', ['provider'])
    op.create_index('ix_llm_call_logs_model', 'llm_call_logs', ['model'])
    op.create_index('ix_llm_call_logs_success', 'llm_call_logs', ['success'])
    op.create_index('ix_llm_call_logs_called_at', 'llm_call_logs', ['called_at'])
```

### Migration 2: Blockchain Transaction Logs

**File**: `alembic/versions/XXXX_add_blockchain_transaction_logs.py`

```python
def upgrade():
    op.create_table(
        'blockchain_transaction_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_hash', sa.String(66), nullable=False),
        sa.Column('block_number', sa.BigInteger(), nullable=True),
        sa.Column('block_hash', sa.String(66), nullable=True),
        sa.Column('transaction_index', sa.Integer(), nullable=True),
        sa.Column('contract_address', sa.String(42), nullable=False),
        sa.Column('contract_name', sa.String(100), nullable=True),
        sa.Column('function_name', sa.String(100), nullable=True),
        sa.Column('from_address', sa.String(42), nullable=False),
        sa.Column('to_address', sa.String(42), nullable=True),
        sa.Column('value', sa.Numeric(36, 18), nullable=True),
        sa.Column('gas_price', sa.BigInteger(), nullable=True),
        sa.Column('gas_used', sa.BigInteger(), nullable=True),
        sa.Column('gas_limit', sa.BigInteger(), nullable=True),
        sa.Column('gas_cost_eth', sa.Numeric(36, 18), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('event_logs', sa.JSON(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('deal_id', sa.Integer(), nullable=True),
        sa.Column('notarization_id', sa.Integer(), nullable=True),
        sa.Column('securitization_pool_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id']),
        sa.ForeignKeyConstraint(['notarization_id'], ['notarization_records.id']),
    )
    op.create_index('ix_blockchain_transaction_logs_transaction_hash', 'blockchain_transaction_logs', ['transaction_hash'], unique=True)
    op.create_index('ix_blockchain_transaction_logs_block_number', 'blockchain_transaction_logs', ['block_number'])
    op.create_index('ix_blockchain_transaction_logs_contract_address', 'blockchain_transaction_logs', ['contract_address'])
    op.create_index('ix_blockchain_transaction_logs_status', 'blockchain_transaction_logs', ['status'])
```

### Migration 3: Analysis Report Notarizations

**File**: `alembic/versions/XXXX_add_analysis_report_notarizations.py`

```python
def upgrade():
    op.create_table(
        'analysis_report_notarizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.String(255), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('report_hash', sa.String(64), nullable=False),
        sa.Column('notarization_hash', sa.String(64), nullable=True),
        sa.Column('blockchain_tx_hash', sa.String(66), nullable=True),
        sa.Column('blockchain_block_number', sa.BigInteger(), nullable=True),
        sa.Column('signer_wallet_address', sa.String(42), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('signed_message', sa.Text(), nullable=False),
        sa.Column('signed_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('deal_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('notarized_at', sa.DateTime(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id']),
    )
    op.create_index('ix_analysis_report_notarizations_report_id', 'analysis_report_notarizations', ['report_id'])
    op.create_index('ix_analysis_report_notarizations_report_hash', 'analysis_report_notarizations', ['report_hash'], unique=True)
    op.create_index('ix_analysis_report_notarizations_blockchain_tx_hash', 'analysis_report_notarizations', ['blockchain_tx_hash'])
    op.create_index('ix_analysis_report_notarizations_status', 'analysis_report_notarizations', ['status'])
```

### Migration 4: Workflow Traces

**File**: `alembic/versions/XXXX_add_workflow_traces.py`

```python
def upgrade():
    op.create_table(
        'workflow_traces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trace_id', sa.String(255), nullable=False),
        sa.Column('parent_trace_id', sa.String(255), nullable=True),
        sa.Column('workflow_id', sa.Integer(), nullable=True),
        sa.Column('workflow_type', sa.String(50), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('previous_state', sa.String(50), nullable=True),
        sa.Column('state_transition_reason', sa.Text(), nullable=True),
        sa.Column('agent_name', sa.String(100), nullable=True),
        sa.Column('tool_name', sa.String(100), nullable=True),
        sa.Column('tool_parameters', sa.JSON(), nullable=True),
        sa.Column('tool_result', sa.JSON(), nullable=True),
        sa.Column('llm_call_id', sa.String(255), nullable=True),
        sa.Column('policy_decision_id', sa.Integer(), nullable=True),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0, nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('deal_id', sa.Integer(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id']),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['llm_call_id'], ['llm_call_logs.call_id']),
        sa.ForeignKeyConstraint(['policy_decision_id'], ['policy_decisions.id']),
    )
    op.create_index('ix_workflow_traces_trace_id', 'workflow_traces', ['trace_id'], unique=True)
    op.create_index('ix_workflow_traces_parent_trace_id', 'workflow_traces', ['parent_trace_id'])
    op.create_index('ix_workflow_traces_workflow_type', 'workflow_traces', ['workflow_type'])
    op.create_index('ix_workflow_traces_state', 'workflow_traces', ['state'])
```

---

## Frontend Updates

### Update Audit Dashboard

**File**: `client/src/apps/auditor/AuditDashboard.tsx` (UPDATE)

Add new sections:

1. **LLM Calls Tab**: Display LLM call logs with costs, tokens, latency
2. **Blockchain Transactions Tab**: Display blockchain transactions with gas costs
3. **Workflow Traces Tab**: Display workflow execution traces
4. **Trace Correlation View**: Show all related traces for a given context
5. **Analysis Report Notarizations**: Display notarized reports

---

## Implementation Checklist

### Phase 1: Core Tracing Infrastructure (Week 1-2)
- [ ] Create LLMCallLog model and migration
- [ ] Create LLM tracing wrapper
- [ ] Update LLM client to support tracing
- [ ] Create LLM audit service
- [ ] Add LLM call audit API endpoints
- [ ] Test LLM call logging

### Phase 2: Blockchain Audit Logging (Week 2-3)
- [ ] Create BlockchainTransactionLog model and migration
- [ ] Update BlockchainService to log transactions
- [ ] Create blockchain audit service
- [ ] Add blockchain audit API endpoints
- [ ] Test blockchain transaction logging

### Phase 3: Analysis Report Notarization (Week 3-4)
- [ ] Create AnalysisReportNotarization model and migration
- [ ] Create analysis report notarization service
- [ ] Integrate notarization with report generation
- [ ] Add notarization API endpoints
- [ ] Test report notarization

### Phase 4: Workflow Traceability (Week 4-5)
- [ ] Create WorkflowTrace model and migration
- [ ] Create workflow tracing service
- [ ] Integrate tracing with agent workflows
- [ ] Add workflow trace API endpoints
- [ ] Test workflow tracing

### Phase 5: Permissioned Access (Week 5)
- [ ] Update audit service with permission filtering
- [ ] Add permission constants
- [ ] Update audit dashboard UI with permission checks
- [ ] Test permission-based access

### Phase 6: Trace Correlation (Week 6)
- [ ] Create trace correlation service
- [ ] Add trace correlation API endpoint
- [ ] Update audit dashboard with correlation view
- [ ] Test trace correlation

### Phase 7: Frontend Updates (Week 6-7)
- [ ] Add LLM calls tab to audit dashboard
- [ ] Add blockchain transactions tab
- [ ] Add workflow traces tab
- [ ] Add trace correlation view
- [ ] Add analysis report notarizations view
- [ ] Test all UI components

### Phase 8: Testing & Documentation (Week 7-8)
- [ ] Write unit tests for all services
- [ ] Write integration tests
- [ ] Update API documentation
- [ ] Create user guide for audit dashboard
- [ ] Performance testing

---

## Success Criteria

1. ✅ **Every LLM call is logged** with prompts, responses, tokens, costs, and performance metrics
2. ✅ **Every blockchain transaction is logged** with transaction hash, block number, gas costs, and event logs
3. ✅ **Every workflow execution is traced** with state transitions, agent actions, and tool usage
4. ✅ **Analysis reports can be notarized** with blockchain verification
5. ✅ **All traces are correlated** across LLM calls, policy decisions, workflows, and blockchain
6. ✅ **Audit dashboard is accessible** to all users with proper permission-based filtering
7. ✅ **All audit data is encrypted** where sensitive (prompts, responses, IP addresses)
8. ✅ **Performance impact is minimal** (<10ms overhead per LLM call, <5ms per blockchain transaction)

---

## Performance Considerations

1. **LLM Call Logging**: Use async logging or background tasks for large responses
2. **Blockchain Transaction Logging**: Update transaction status asynchronously after confirmation
3. **Workflow Tracing**: Batch trace updates where possible
4. **Database Indexing**: Ensure all foreign keys and frequently queried fields are indexed
5. **Encryption Overhead**: Use efficient encryption for large JSON fields

---

## Security Considerations

1. **Encrypted Fields**: Prompts, responses, IP addresses must be encrypted at rest
2. **Permission Checks**: All audit endpoints must check permissions
3. **Data Access**: Users can only see audit logs for their organization/own data (unless admin)
4. **Audit Log Integrity**: Audit logs themselves should be immutable (append-only)

---

## Future Enhancements

1. **Real-time Audit Streaming**: WebSocket updates for audit events
2. **Audit Alerting**: Alerts for suspicious patterns (e.g., high LLM costs, failed transactions)
3. **Audit Analytics**: Advanced analytics and reporting
4. **External Audit Export**: Export audit logs to external systems (SIEM, etc.)
5. **Audit Retention Policies**: Automated archival of old audit logs

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Planning

---

## Related Plans

- **`STOCK_PREDICTION_VENDORING_PLAN.md`** - Stock prediction integration includes audit logging for Chronos T5 model calls, GPU usage tracking, and prediction parameter logging
- **`TRADING_DASHBOARD_IMPLEMENTATION_PLAN.md`** - Trading activities require comprehensive audit logging
- **`BILLING_DASHBOARD_PLAN.md`** - Cost tracking requires full audit trail for billing transparency
