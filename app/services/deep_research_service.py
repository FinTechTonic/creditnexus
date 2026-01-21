"""DeepResearch service for orchestrating research queries.

Follows service layer pattern:
- Service class with dependency injection
- Database session management
- CDM event integration
- Result storage and caching
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.agents.deep_research_agent import (
    research_query,
    ResearchContext,
    KnowledgeItem
)
from app.db.models import Document, Deal, Workflow, DeepResearchResult
from app.utils.audit import log_audit_action
from app.db.models import AuditAction
from app.services.agent_note_service import AgentNoteService

logger = logging.getLogger(__name__)


class DeepResearchService:
    """
    DeepResearch service for executing research queries.
    
    Follows service layer pattern:
    - Database session injected via constructor
    - Returns domain models, not database models
    - Generates CDM events for state changes
    - Uses log_audit_action() for all operations
    """
    
    def __init__(self, db: Session):
        """
        Initialize DeepResearch service.
        
        Args:
            db: Database session for data persistence
        """
        self.db = db
    
    async def research(
        self,
        query: str,
        deal_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute general research query.
        
        Args:
            query: Research question
            deal_id: Optional deal ID for linking
            workflow_id: Optional workflow ID for linking
            user_id: Optional user ID for audit logging
            
        Returns:
            Research result with answer, knowledge items, and CDM events
        """
        context = ResearchContext()
        
        # Execute research
        result = await research_query(
            question=query,
            context=context,
            deal_id=deal_id,
            workflow_id=workflow_id
        )
        
        # Persist to deep_research_results so GET /api/deep-research/results shows items
        research_id = str(uuid.uuid4())
        record = DeepResearchResult(
            research_id=research_id,
            query=query,
            answer=result.get("answer"),
            knowledge_items=result.get("knowledge_items"),
            visited_urls=result.get("visited_urls") or [],
            searched_queries=result.get("searched_queries") or [],
            deal_id=deal_id,
            workflow_id=workflow_id,
            status="completed",
            completed_at=datetime.utcnow(),
        )
        self.db.add(record)
        self.db.flush()
        result["research_id"] = research_id
        
        # Audit logging
        if user_id:
            log_audit_action(
                db=self.db,
                action=AuditAction.CREATE,
                target_type="research_query",
                target_id=None,  # Will be set when table is created
                user_id=user_id,
                metadata={
                    "query": query,
                    "deal_id": deal_id,
                    "workflow_id": workflow_id
                }
            )
        
        # Create agent interaction note if deal_id provided
        if deal_id:
            try:
                note_service = AgentNoteService(self.db)
                research_id = result.get("research_id") or str(uuid.uuid4())
                note = note_service.create_agent_interaction_note(
                    agent_type="deepresearch",
                    interaction_data={
                        "query": query,
                        "answer": result.get("answer", ""),
                        "knowledge_items": result.get("knowledge_items", []),
                        "visited_urls": result.get("visited_urls", []),
                        "research_id": research_id
                    },
                    deal_id=deal_id,
                    user_id=user_id
                )
                logger.info(f"Created agent interaction note {note.id} for DeepResearch query")
            except Exception as e:
                logger.warning(f"Failed to create agent interaction note: {e}")
        
        return result
    
    async def research_loan_application(
        self,
        loan_application_id: Optional[int] = None,
        borrower_name: Optional[str] = None,
        deal_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute loan application-specific research.
        
        Args:
            loan_application_id: Optional loan application ID
            borrower_name: Optional borrower name for research
            deal_id: Optional deal ID
            user_id: Optional user ID for audit logging
            
        Returns:
            Research result focused on loan application intelligence
        """
        # Generate research queries for loan application
        queries = []
        if borrower_name:
            queries.append(f"Financial news and recent developments about {borrower_name}")
            queries.append(f"Credit rating and financial health of {borrower_name}")
            queries.append(f"Regulatory compliance and sanctions for {borrower_name}")
        
        # Execute multiple research queries
        results = []
        for query in queries:
            result = await self.research(
                query=query,
                deal_id=deal_id,
                user_id=user_id
            )
            results.append(result)
        
        # Aggregate results
        aggregated_answer = "\n\n".join([r.get("answer", "") for r in results])
        all_knowledge_items = []
        all_visited_urls = []
        for r in results:
            all_knowledge_items.extend(r.get("knowledge_items", []))
            all_visited_urls.extend(r.get("visited_urls", []))
        
        return {
            "answer": aggregated_answer,
            "knowledge_items": all_knowledge_items,
            "visited_urls": list(set(all_visited_urls)),  # Deduplicate
            "cdm_events": [r.get("cdm_event") for r in results if r.get("cdm_event")]
        }
