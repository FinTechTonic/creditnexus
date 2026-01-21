"""Quantitative analysis service using LangAlpha multi-agent system.

Follows repository patterns:
- Service layer with dependency injection
- CDM event generation
- Deal timeline integration
- Audit logging
- Policy engine integration
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models import (
    QuantitativeAnalysisResult,
    QuantitativeAnalysisStatus,
    Deal,
    AuditLog,
    AuditAction
)
from app.workflows.langalpha_graph import build_langalpha_graph, State, TEAM_MEMBERS
from app.services.deal_service import DealService
from app.models.cdm_events import generate_cdm_research_query, generate_cdm_observation, generate_cdm_policy_evaluation
from app.utils.audit import log_audit_action
from app.services.agent_note_service import AgentNoteService
from app.services.agent_report_service import AgentReportService

logger = logging.getLogger(__name__)


class QuantitativeAnalysisService:
    """
    Service for quantitative financial analysis using LangAlpha.
    
    Orchestrates the LangAlpha multi-agent system to perform:
    - Company analysis
    - Market analysis
    - Loan application analysis
    """
    
    def __init__(self, db: Session, policy_service: Optional[Any] = None):
        """
        Initialize quantitative analysis service.
        
        Args:
            db: Database session
            policy_service: Optional policy service for compliance checks
        """
        self.db = db
        self.graph = build_langalpha_graph()
        self.deal_service = DealService(db)
        self.policy_service = policy_service
    
    def _get_cache_key(
        self,
        analysis_type: str,
        query: str,
        ticker: Optional[str] = None,
        company_name: Optional[str] = None,
        time_range: Optional[str] = None
    ) -> str:
        """Generate cache key for analysis."""
        key_parts = [
            analysis_type,
            query.lower().strip(),
            ticker or "",
            company_name or "",
            time_range or ""
        ]
        import hashlib
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _check_cache(
        self,
        cache_key: str,
        max_age_hours: int = 24
    ) -> Optional[QuantitativeAnalysisResult]:
        """
        Check if analysis result exists in cache.
        
        Args:
            cache_key: Cache key hash
            max_age_hours: Maximum age of cached result in hours (default: 24)
            
        Returns:
            Cached QuantitativeAnalysisResult or None
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        # Look for completed analysis with matching query hash
        # We'll store cache_key in a metadata field or use query hash
        cached = self.db.query(QuantitativeAnalysisResult).filter(
            QuantitativeAnalysisResult.status == QuantitativeAnalysisStatus.COMPLETED.value,
            QuantitativeAnalysisResult.completed_at >= cutoff_time
        ).order_by(QuantitativeAnalysisResult.completed_at.desc()).first()
        
        # For now, simple cache: check if same query was analyzed recently
        # TODO: Implement proper cache_key storage in database
        return None  # Disable cache for now, can be enhanced later
    
    async def analyze_company(
        self,
        query: str,
        ticker: Optional[str] = None,
        company_name: Optional[str] = None,
        deal_id: Optional[int] = None,
        user_id: Optional[int] = None,
        time_range: Optional[str] = None,
        use_cache: bool = True,
        max_cache_age_hours: int = 24,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze a company using LangAlpha multi-agent system.
        
        Args:
            query: Analysis query (e.g., "Analyze Apple's financial health")
            ticker: Stock ticker symbol (e.g., "AAPL")
            company_name: Company name
            deal_id: Optional deal ID to associate with analysis
            user_id: Optional user ID initiating the analysis
            time_range: Optional time range for analysis
            use_cache: Whether to use cached results (default: True)
            max_cache_age_hours: Maximum age of cached result in hours (default: 24)
            
        Returns:
            Dict with analysis results including report, market_data, fundamental_data
        """
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key("company", query, ticker, company_name, time_range)
            cached_result = self._check_cache(cache_key, max_cache_age_hours)
            if cached_result:
                logger.info(f"Returning cached analysis result: {cached_result.analysis_id}")
                return {
                    "status": "success",
                    "analysis_id": cached_result.analysis_id,
                    "report": cached_result.report.get("report", "") if cached_result.report else "",
                    "market_data": cached_result.market_data or {},
                    "fundamental_data": cached_result.fundamental_data or {},
                    "cdm_event": cached_result.report.get("cdm_event") if cached_result.report else None,
                    "cached": True
                }
        
        analysis_id = str(uuid.uuid4())
        
        # Create analysis record
        analysis_result = QuantitativeAnalysisResult(
            analysis_id=analysis_id,
            analysis_type="company",
            query=query,
            deal_id=deal_id,
            user_id=user_id,
            status=QuantitativeAnalysisStatus.IN_PROGRESS.value
        )
        self.db.add(analysis_result)
        self.db.commit()
        self.db.refresh(analysis_result)
        
        try:
            # Generate CDM research query event
            cdm_event = generate_cdm_research_query(
                query_id=analysis_id,
                query_text=query,
                query_type="company_analysis",
                metadata={
                    "ticker": ticker,
                    "company_name": company_name,
                    "time_range": time_range
                }
            )
            
            # Initialize state for LangAlpha graph
            initial_state: State = {
                "TEAM_MEMBERS": TEAM_MEMBERS,
                "messages": [query],
                "next": "coordinator",
                "full_plan": "",
                "final_report": "",
                "last_agent": None,
                "current_timestamp": datetime.now(timezone.utc),
                "researcher_credits": 6,
                "coder_credits": 0,
                "browser_credits": 3,
                "market_credits": 6,
                "time_range": time_range or "not specified",
                "ticker_type": "company" if ticker or company_name else None,
                "tickers": [{
                    "company": company_name,
                    "ticker": ticker,
                    "tradingview_symbol": f"NASDAQ:{ticker}" if ticker else None
                }] if ticker or company_name else None,
                "agent_llm_map": None,
                "llm_configs": None
            }
            
            # Execute LangAlpha graph with checkpointing
            logger.info(f"Starting LangAlpha analysis for company: {ticker or company_name}")
            final_state = None
            
            # Create checkpoint config for resumable execution
            checkpoint_config = {
                "recursion_limit": 150,
                "configurable": {
                    "thread_id": analysis_id  # Use analysis_id as thread_id for checkpointing
                }
            }
            
            # Track progress for streaming
            total_steps = 20  # Estimated total steps
            current_step = 0
            
            async for state in self.graph.astream(initial_state, config=checkpoint_config):
                final_state = state
                # Log progress
                next_agent = state.get("next", "unknown")
                logger.debug(f"LangAlpha progress: {next_agent}")
                
                # Update progress for streaming
                current_step += 1
                progress = min(int((current_step / total_steps) * 100), 95)  # Cap at 95% until completion
                
                if progress_callback:
                    try:
                        await progress_callback({
                            "status": "in_progress",
                            "progress": progress,
                            "current_step": f"Running {next_agent} agent...",
                            "message": f"Analysis in progress: {next_agent}"
                        })
                    except Exception as e:
                        logger.warning(f"Failed to send progress update: {e}")
                
                # Checkpointing is handled automatically by LangGraph when checkpointer is configured
                # The state is persisted after each node execution
            
            # Extract results
            final_report = final_state.get("final_report", "") if final_state else ""
            market_data = {}
            fundamental_data = {}
            
            # Extract market and fundamental data from agent messages
            if final_state and final_state.get("messages"):
                for msg in final_state["messages"]:
                    if hasattr(msg, 'name'):
                        if msg.name == "market":
                            # Parse market data from message
                            try:
                                import json
                                market_data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                            except:
                                market_data = {"raw": str(msg.content)}
                        elif msg.name == "researcher":
                            # Extract fundamental data hints from researcher
                            pass
            
            # Generate structured report
            structured_report = self._generate_structured_report(
                analysis_type="company",
                query=query,
                ticker=ticker,
                company_name=company_name,
                final_report=final_report,
                market_data=market_data,
                fundamental_data=fundamental_data,
                time_range=time_range
            )
            
            # Update analysis result with structured report
            analysis_result.report = {
                "report": final_report,
                "structured_report": structured_report,
                "cdm_event": cdm_event
            }
            analysis_result.market_data = market_data
            analysis_result.fundamental_data = fundamental_data
            analysis_result.status = QuantitativeAnalysisStatus.COMPLETED.value
            analysis_result.completed_at = datetime.now(timezone.utc)
            self.db.add(analysis_result)
            self.db.commit()
            
            # Policy evaluation (if enabled)
            policy_evaluation_event = None
            if self.policy_service:
                try:
                    # Create CDM event for policy evaluation
                    policy_cdm_event = {
                        "eventType": "ResearchQuery",
                        "eventDate": datetime.now(timezone.utc).isoformat(),
                        "observation": {
                            "observationType": "QuantitativeAnalysis",
                            "query": query,
                            "analysisType": "company",
                            "ticker": ticker,
                            "companyName": company_name
                        },
                        "meta": {
                            "globalKey": str(uuid.uuid4()),
                            "sourceSystem": "CreditNexus_LangAlpha_v1"
                        }
                    }
                    
                    # Evaluate using policy service
                    policy_result = self.policy_service.evaluate_with_cdm_process(
                        cdm_event=policy_cdm_event,
                        credit_agreement=None
                    )
                    
                    # Generate policy evaluation CDM event
                    policy_evaluation_event = generate_cdm_policy_evaluation(
                        transaction_id=analysis_id,
                        transaction_type="quantitative_analysis",
                        decision=policy_result.get("decision", "ALLOW"),
                        rule_applied=policy_result.get("rule_applied"),
                        related_event_identifiers=[{
                            "eventIdentifier": {
                                "issuer": "CreditNexus",
                                "assignedIdentifier": [{"identifier": {"value": analysis_id}}]
                            }
                        }],
                        evaluation_trace=policy_result.get("trace", []),
                        matched_rules=policy_result.get("matched_rules", [])
                    )
                    
                    logger.info(f"Policy evaluation for analysis {analysis_id}: {policy_result.get('decision', 'ALLOW')}")
                except Exception as e:
                    logger.warning(f"Policy evaluation failed: {e}")
            
            # Update deal timeline if deal_id provided
            if deal_id:
                self.deal_service.add_timeline_event(
                    deal_id=deal_id,
                    event_type="quantitative_analysis_completed",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data={
                        "analysis_id": analysis_id,
                        "analysis_type": "company",
                        "ticker": ticker,
                        "company_name": company_name,
                        "policy_decision": policy_evaluation_event.get("policyEvaluation", {}).get("decision") if policy_evaluation_event else None
                    },
                    user_id=user_id
                )
            
            # Audit logging
            log_audit_action(
                db=self.db,
                action=AuditAction.CREATE,
                target_type="quantitative_analysis",
                target_id=analysis_result.id,
                user_id=user_id,
                metadata={
                    "analysis_type": "company",
                    "ticker": ticker,
                    "company_name": company_name,
                    "deal_id": deal_id,
                    "policy_decision": policy_evaluation_event.get("policyEvaluation", {}).get("decision") if policy_evaluation_event else None
                }
            )
            
            # Create agent interaction note
            if deal_id:
                try:
                    note_service = AgentNoteService(self.db)
                    note = note_service.create_agent_interaction_note(
                        agent_type="langalpha",
                        interaction_data={
                            "analysis_type": "company",
                            "query": query,
                            "ticker": ticker,
                            "company_name": company_name,
                            "report_summary": structured_report.get("executive_summary", ""),
                            "key_findings": structured_report.get("key_findings", []),
                            "metrics": structured_report.get("metrics", {}),
                            "analysis_id": analysis_id,
                            "full_result": {
                                "report": final_report,
                                "structured_report": structured_report,
                                "market_data": market_data,
                                "fundamental_data": fundamental_data
                            }
                        },
                        deal_id=deal_id,
                        user_id=user_id
                    )
                    logger.info(f"Created agent interaction note {note.id} for analysis {analysis_id}")
                except Exception as e:
                    logger.warning(f"Failed to create agent interaction note: {e}")
            
            # Create agent report and attach as document
            if deal_id:
                try:
                    report_service = AgentReportService(self.db)
                    report_result = await report_service.create_agent_report(
                        agent_type="langalpha",
                        agent_result={
                            "analysis_type": "company",
                            "query": query,
                            "ticker": ticker,
                            "company_name": company_name,
                            "report": final_report,
                            "structured_report": structured_report,
                            "market_data": market_data,
                            "fundamental_data": fundamental_data,
                            "analysis_id": analysis_id,
                            "cdm_event": cdm_event,
                            "policy_evaluation": policy_evaluation_event
                        },
                        deal_id=deal_id,
                        user_id=user_id,
                        format="markdown",
                        attach_as_document=True,
                        create_note=False  # Note already created above
                    )
                    logger.info(f"Created agent report document {report_result.get('document_id')} for analysis {analysis_id}")
                except Exception as e:
                    logger.warning(f"Failed to create agent report: {e}")
            
            logger.info(f"Company analysis completed: {analysis_id}")
            
            return {
                "status": "success",
                "analysis_id": analysis_id,
                "report": final_report,
                "structured_report": structured_report,
                "market_data": market_data,
                "fundamental_data": fundamental_data,
                "cdm_event": cdm_event,
                "policy_evaluation": policy_evaluation_event
            }
            
        except Exception as e:
            logger.error(f"Error in company analysis: {e}", exc_info=True)
            analysis_result.status = QuantitativeAnalysisStatus.FAILED.value
            analysis_result.error_message = str(e)
            analysis_result.completed_at = datetime.now(timezone.utc)
            self.db.add(analysis_result)
            self.db.commit()
            
            # Audit log error
            log_audit_action(
                db=self.db,
                action=AuditAction.CREATE,
                target_type="agent_error",
                target_id=analysis_result.id,
                user_id=user_id,
                metadata={
                    "agent_type": "langalpha",
                    "analysis_type": "company",
                    "error": str(e),
                    "query": query,
                    "ticker": ticker,
                    "company_name": company_name,
                    "analysis_id": analysis_id
                }
            )
            
            raise
    
    async def analyze_market(
        self,
        query: str,
        market_type: Optional[str] = None,
        deal_id: Optional[int] = None,
        user_id: Optional[int] = None,
        time_range: Optional[str] = None,
        use_cache: bool = True,
        max_cache_age_hours: int = 24,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze market conditions using LangAlpha.
        
        Args:
            query: Analysis query (e.g., "Analyze the semiconductor market")
            market_type: Type of market (e.g., "semiconductor", "tech", "overall")
            deal_id: Optional deal ID
            user_id: Optional user ID
            time_range: Optional time range
            use_cache: Whether to use cached results (default: True)
            max_cache_age_hours: Maximum age of cached result in hours (default: 24)
            
        Returns:
            Dict with analysis results
        """
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key("market", query, time_range=time_range)
            cached_result = self._check_cache(cache_key, max_cache_age_hours)
            if cached_result:
                logger.info(f"Returning cached market analysis result: {cached_result.analysis_id}")
                return {
                    "status": "success",
                    "analysis_id": cached_result.analysis_id,
                    "report": cached_result.report.get("report", "") if cached_result.report else "",
                    "cdm_event": cached_result.report.get("cdm_event") if cached_result.report else None,
                    "cached": True
                }
        
        analysis_id = str(uuid.uuid4())
        
        # Create analysis record
        analysis_result = QuantitativeAnalysisResult(
            analysis_id=analysis_id,
            analysis_type="market",
            query=query,
            deal_id=deal_id,
            user_id=user_id,
            status=QuantitativeAnalysisStatus.IN_PROGRESS.value
        )
        self.db.add(analysis_result)
        self.db.commit()
        self.db.refresh(analysis_result)
        
        try:
            # Generate CDM event
            cdm_event = generate_cdm_research_query(
                query_id=analysis_id,
                query_text=query,
                query_type="market_analysis",
                metadata={"market_type": market_type, "time_range": time_range}
            )
            
            # Initialize state
            initial_state: State = {
                "TEAM_MEMBERS": TEAM_MEMBERS,
                "messages": [query],
                "next": "coordinator",
                "full_plan": "",
                "final_report": "",
                "last_agent": None,
                "current_timestamp": datetime.now(timezone.utc),
                "researcher_credits": 6,
                "coder_credits": 0,
                "browser_credits": 3,
                "market_credits": 6,
                "time_range": time_range or "not specified",
                "ticker_type": "market",
                "tickers": None,
                "agent_llm_map": None,
                "llm_configs": None,
                "db": self.db,  # Pass db for audit logging
                "user_id": user_id,
                "analysis_id": analysis_id
            }
            
            # Execute graph
            logger.info(f"Starting LangAlpha market analysis")
            final_state = None
            
            # Track progress for streaming
            total_steps = 20
            current_step = 0
            
            async for state in self.graph.astream(initial_state, config={"recursion_limit": 150}):
                final_state = state
                
                # Update progress for streaming
                current_step += 1
                progress = min(int((current_step / total_steps) * 100), 95)
                
                if progress_callback:
                    try:
                        next_agent = state.get("next", "unknown")
                        await progress_callback({
                            "status": "in_progress",
                            "progress": progress,
                            "current_step": f"Running {next_agent} agent...",
                            "message": f"Market analysis in progress: {next_agent}"
                        })
                    except Exception as e:
                        logger.warning(f"Failed to send progress update: {e}")
            
            # Extract results
            final_report = final_state.get("final_report", "") if final_state else ""
            
            # Update analysis result
            analysis_result.report = {"report": final_report, "cdm_event": cdm_event}
            analysis_result.status = QuantitativeAnalysisStatus.COMPLETED.value
            analysis_result.completed_at = datetime.now(timezone.utc)
            self.db.add(analysis_result)
            self.db.commit()
            
            # Update deal timeline
            if deal_id:
                self.deal_service.add_timeline_event(
                    deal_id=deal_id,
                    event_type="quantitative_analysis_completed",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data={
                        "analysis_id": analysis_id,
                        "analysis_type": "market",
                        "market_type": market_type
                    },
                    user_id=user_id
                )
            
            # Audit logging
            log_audit_action(
                db=self.db,
                action=AuditAction.CREATE,
                target_type="quantitative_analysis",
                target_id=analysis_result.id,
                user_id=user_id,
                metadata={"analysis_type": "market", "market_type": market_type, "deal_id": deal_id}
            )
            
            # Create agent interaction note if deal_id provided
            if deal_id:
                try:
                    structured_report = self._generate_structured_report(
                        analysis_type="market",
                        query=query,
                        final_report=final_report,
                        time_range=time_range
                    )
                    note_service = AgentNoteService(self.db)
                    note = note_service.create_agent_interaction_note(
                        agent_type="langalpha",
                        interaction_data={
                            "analysis_type": "market",
                            "query": query,
                            "market_type": market_type,
                            "report_summary": structured_report.get("executive_summary", ""),
                            "key_findings": structured_report.get("key_findings", []),
                            "metrics": structured_report.get("metrics", {}),
                            "analysis_id": analysis_id,
                            "full_result": {
                                "report": final_report,
                                "structured_report": structured_report
                            }
                        },
                        deal_id=deal_id,
                        user_id=user_id
                    )
                    logger.info(f"Created agent interaction note {note.id} for market analysis {analysis_id}")
                except Exception as e:
                    logger.warning(f"Failed to create agent interaction note: {e}")
            
            # Create agent report and attach as document
            if deal_id:
                try:
                    report_service = AgentReportService(self.db)
                    report_result = await report_service.create_agent_report(
                        agent_type="langalpha",
                        agent_result={
                            "analysis_type": "market",
                            "query": query,
                            "market_type": market_type,
                            "report": final_report,
                            "structured_report": structured_report,
                            "analysis_id": analysis_id,
                            "cdm_event": cdm_event
                        },
                        deal_id=deal_id,
                        user_id=user_id,
                        format="markdown",
                        attach_as_document=True,
                        create_note=False  # Note already created above
                    )
                    logger.info(f"Created agent report document {report_result.get('document_id')} for market analysis {analysis_id}")
                except Exception as e:
                    logger.warning(f"Failed to create agent report: {e}")
            
            return {
                "status": "success",
                "analysis_id": analysis_id,
                "report": final_report,
                "cdm_event": cdm_event
            }
            
        except Exception as e:
            logger.error(f"Error in market analysis: {e}", exc_info=True)
            analysis_result.status = QuantitativeAnalysisStatus.FAILED.value
            analysis_result.error_message = str(e)
            analysis_result.completed_at = datetime.now(timezone.utc)
            self.db.add(analysis_result)
            self.db.commit()
            
            # Audit log error
            log_audit_action(
                db=self.db,
                action=AuditAction.CREATE,
                target_type="agent_error",
                target_id=analysis_result.id,
                user_id=user_id,
                metadata={
                    "agent_type": "langalpha",
                    "analysis_type": "market",
                    "error": str(e),
                    "query": query,
                    "market_type": market_type,
                    "analysis_id": analysis_id
                }
            )
            
            raise
    
    async def analyze_loan_application(
        self,
        query: str,
        borrower_name: Optional[str] = None,
        deal_id: Optional[int] = None,
        user_id: Optional[int] = None,
        time_range: Optional[str] = None,
        use_cache: bool = False,  # Loan applications are usually unique, disable cache by default
        max_cache_age_hours: int = 24,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze a loan application using LangAlpha.
        
        Args:
            query: Analysis query focused on loan application
            borrower_name: Name of the borrower
            deal_id: Deal ID (required for loan analysis)
            user_id: Optional user ID
            time_range: Optional time range
            
        Returns:
            Dict with analysis results
        """
        if not deal_id:
            raise ValueError("deal_id is required for loan application analysis")
        
        analysis_id = str(uuid.uuid4())
        
        # Create analysis record
        analysis_result = QuantitativeAnalysisResult(
            analysis_id=analysis_id,
            analysis_type="loan_application",
            query=query,
            deal_id=deal_id,
            user_id=user_id,
            status=QuantitativeAnalysisStatus.IN_PROGRESS.value
        )
        self.db.add(analysis_result)
        self.db.commit()
        self.db.refresh(analysis_result)
        
        try:
            # Generate CDM event
            cdm_event = generate_cdm_research_query(
                query_id=analysis_id,
                query_text=query,
                query_type="loan_application_analysis",
                metadata={"borrower_name": borrower_name, "deal_id": deal_id, "time_range": time_range}
            )
            
            # Initialize state with loan-specific context
            initial_state: State = {
                "TEAM_MEMBERS": TEAM_MEMBERS,
                "messages": [f"Analyze loan application for {borrower_name or 'borrower'}: {query}"],
                "next": "coordinator",
                "full_plan": "",
                "final_report": "",
                "last_agent": None,
                "current_timestamp": datetime.now(timezone.utc),
                "researcher_credits": 6,
                "coder_credits": 0,
                "browser_credits": 3,
                "market_credits": 6,
                "time_range": time_range or "not specified",
                "ticker_type": None,
                "tickers": None,
                "agent_llm_map": None,
                "llm_configs": None,
                "db": self.db,  # Pass db for audit logging
                "user_id": user_id,
                "analysis_id": analysis_id
            }
            
            # Execute graph with checkpointing
            logger.info(f"Starting LangAlpha loan application analysis for deal {deal_id}")
            final_state = None
            
            checkpoint_config = {
                "recursion_limit": 150,
                "configurable": {
                    "thread_id": analysis_id
                }
            }
            
            # Track progress for streaming
            total_steps = 20
            current_step = 0
            
            async for state in self.graph.astream(initial_state, config=checkpoint_config):
                final_state = state
                
                # Update progress for streaming
                current_step += 1
                progress = min(int((current_step / total_steps) * 100), 95)
                
                if progress_callback:
                    try:
                        next_agent = state.get("next", "unknown")
                        await progress_callback({
                            "status": "in_progress",
                            "progress": progress,
                            "current_step": f"Running {next_agent} agent...",
                            "message": f"Loan application analysis in progress: {next_agent}"
                        })
                    except Exception as e:
                        logger.warning(f"Failed to send progress update: {e}")
            
            # Extract results
            final_report = final_state.get("final_report", "") if final_state else ""
            
            # Update analysis result
            analysis_result.report = {"report": final_report, "cdm_event": cdm_event}
            analysis_result.status = QuantitativeAnalysisStatus.COMPLETED.value
            analysis_result.completed_at = datetime.now(timezone.utc)
            self.db.add(analysis_result)
            self.db.commit()
            
            # Update deal timeline
            self.deal_service.add_timeline_event(
                deal_id=deal_id,
                event_type="quantitative_analysis_completed",
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={
                    "analysis_id": analysis_id,
                    "analysis_type": "loan_application",
                    "borrower_name": borrower_name
                },
                user_id=user_id
            )
            
            # Audit logging
            log_audit_action(
                db=self.db,
                action=AuditAction.CREATE,
                target_type="quantitative_analysis",
                target_id=analysis_result.id,
                user_id=user_id,
                metadata={
                    "analysis_type": "loan_application",
                    "borrower_name": borrower_name,
                    "deal_id": deal_id
                }
            )
            
            # Create agent interaction note
            try:
                structured_report = self._generate_structured_report(
                    analysis_type="loan_application",
                    query=query,
                    final_report=final_report,
                    time_range=time_range
                )
                note_service = AgentNoteService(self.db)
                note = note_service.create_agent_interaction_note(
                    agent_type="langalpha",
                    interaction_data={
                        "analysis_type": "loan_application",
                        "query": query,
                        "borrower_name": borrower_name,
                        "report_summary": structured_report.get("executive_summary", ""),
                        "key_findings": structured_report.get("key_findings", []),
                        "metrics": structured_report.get("metrics", {}),
                        "analysis_id": analysis_id,
                        "full_result": {
                            "report": final_report,
                            "structured_report": structured_report
                        }
                    },
                    deal_id=deal_id,
                    user_id=user_id
                )
                logger.info(f"Created agent interaction note {note.id} for loan application analysis {analysis_id}")
            except Exception as e:
                logger.warning(f"Failed to create agent interaction note: {e}")
            
            # Create agent report and attach as document
            if deal_id:
                try:
                    report_service = AgentReportService(self.db)
                    report_result = await report_service.create_agent_report(
                        agent_type="langalpha",
                        agent_result={
                            "analysis_type": "loan_application",
                            "query": query,
                            "borrower_name": borrower_name,
                            "report": final_report,
                            "structured_report": structured_report,
                            "analysis_id": analysis_id,
                            "cdm_event": cdm_event
                        },
                        deal_id=deal_id,
                        user_id=user_id,
                        format="markdown",
                        attach_as_document=True,
                        create_note=False  # Note already created above
                    )
                    logger.info(f"Created agent report document {report_result.get('document_id')} for loan application analysis {analysis_id}")
                except Exception as e:
                    logger.warning(f"Failed to create agent report: {e}")
            
            return {
                "status": "success",
                "analysis_id": analysis_id,
                "report": final_report,
                "cdm_event": cdm_event
            }
            
        except Exception as e:
            logger.error(f"Error in loan application analysis: {e}", exc_info=True)
            analysis_result.status = QuantitativeAnalysisStatus.FAILED.value
            analysis_result.error_message = str(e)
            analysis_result.completed_at = datetime.now(timezone.utc)
            self.db.add(analysis_result)
            self.db.commit()
            
            # Audit log error
            log_audit_action(
                db=self.db,
                action=AuditAction.CREATE,
                target_type="agent_error",
                target_id=analysis_result.id,
                user_id=user_id,
                metadata={
                    "agent_type": "langalpha",
                    "analysis_type": "loan_application",
                    "error": str(e),
                    "query": query,
                    "borrower_name": borrower_name,
                    "deal_id": deal_id,
                    "analysis_id": analysis_id
                }
            )
            
            raise
    
    def _generate_structured_report(
        self,
        analysis_type: str,
        query: str,
        final_report: str,
        ticker: Optional[str] = None,
        company_name: Optional[str] = None,
        market_data: Optional[Dict[str, Any]] = None,
        fundamental_data: Optional[Dict[str, Any]] = None,
        time_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured report from analysis results.
        
        Args:
            analysis_type: Type of analysis (company, market, loan_application)
            query: Original query
            final_report: Final report text from LangAlpha
            ticker: Optional ticker symbol
            company_name: Optional company name
            market_data: Optional market data
            fundamental_data: Optional fundamental data
            time_range: Optional time range
            
        Returns:
            Structured report dictionary
        """
        structured = {
            "analysis_type": analysis_type,
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "time_range": time_range or "not specified",
            "executive_summary": "",
            "key_findings": [],
            "metrics": {},
            "recommendations": [],
            "risk_assessment": {},
            "data_sources": []
        }
        
        # Add type-specific metadata
        if analysis_type == "company":
            structured["company"] = {
                "ticker": ticker,
                "company_name": company_name
            }
            if market_data:
                structured["metrics"]["market_metrics"] = market_data
            if fundamental_data:
                structured["metrics"]["fundamental_metrics"] = fundamental_data
        
        # Extract key findings from final_report (simple extraction)
        if final_report:
            structured["executive_summary"] = final_report[:500] if len(final_report) > 500 else final_report
            # Try to extract key findings (simple heuristic)
            lines = final_report.split("\n")
            for line in lines:
                if any(keyword in line.lower() for keyword in ["finding", "conclusion", "recommendation", "risk"]):
                    if len(line.strip()) > 20:  # Filter out very short lines
                        structured["key_findings"].append(line.strip())
        
        # Add data sources
        if market_data:
            structured["data_sources"].append("Market Data (Polygon API)")
        if fundamental_data:
            structured["data_sources"].append("Fundamental Data (Alpha Vantage)")
        structured["data_sources"].append("Web Search (Serper API)")
        structured["data_sources"].append("News (Tickertick API)")
        
        return structured
    
    def get_analysis_result(self, analysis_id: str) -> Optional[QuantitativeAnalysisResult]:
        """
        Retrieve analysis result by analysis_id.
        
        Args:
            analysis_id: UUID of the analysis
            
        Returns:
            QuantitativeAnalysisResult or None if not found
        """
        return self.db.query(QuantitativeAnalysisResult).filter(
            QuantitativeAnalysisResult.analysis_id == analysis_id
        ).first()
