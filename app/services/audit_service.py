"""
Audit Service for CreditNexus.

Provides centralized audit data aggregation service for querying and enriching
audit logs across all entities (deals, documents, loans, filings).
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.db.models import (
    AuditLog,
    Deal,
    Document,
    Workflow,
    PolicyDecision,
    VerificationAuditLog,
    User
)
from app.models.loan_asset import LoanAsset
from app.utils.audit import AuditAction

logger = logging.getLogger(__name__)


class AuditService:
    """Service for aggregating and querying audit data across entities."""
    
    def get_audit_logs(
        self,
        db: Session,
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
        """
        Query audit logs with advanced filtering.
        
        Args:
            db: Database session
            action: Filter by action type
            target_type: Filter by target type
            target_id: Filter by target ID
            user_id: Filter by user ID
            start_date: Filter from date
            end_date: Filter to date
            metadata_filter: Filter by metadata (JSONB key-value pairs)
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            Tuple of (audit logs list, total count)
        """
        try:
            # Build base query with eager loading
            query = db.query(AuditLog).options(joinedload(AuditLog.user))
            
            # Apply action filter
            if action:
                query = query.filter(AuditLog.action == action)
            
            # Apply target_type filter
            if target_type:
                query = query.filter(AuditLog.target_type == target_type)
            
            # Apply target_id filter
            if target_id:
                query = query.filter(AuditLog.target_id == target_id)
            
            # Apply user_id filter
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            
            # Apply start_date filter
            if start_date:
                query = query.filter(AuditLog.occurred_at >= start_date)
            
            # Apply end_date filter
            if end_date:
                query = query.filter(AuditLog.occurred_at <= end_date)
            
            # Apply metadata filter (JSONB contains operator)
            if metadata_filter:
                for key, value in metadata_filter.items():
                    # Use JSONB contains operator for metadata filtering
                    query = query.filter(
                        AuditLog.action_metadata.has_key(key)
                    )
                    if value is not None:
                        query = query.filter(
                            AuditLog.action_metadata[key].astext == str(value)
                        )
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            logs = query.order_by(AuditLog.occurred_at.desc()).offset(offset).limit(limit).all()
            
            return logs, total
            
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}", exc_info=True)
            raise
    
    def get_deal_audit_trail(
        self,
        db: Session,
        deal_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive audit trail for a deal.
        
        Args:
            db: Database session
            deal_id: Deal ID
            start_date: Filter from date
            end_date: Filter to date
            
        Returns:
            Dictionary with deal info and audit logs
        """
        try:
            # Fetch deal
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if not deal:
                raise ValueError(f"Deal {deal_id} not found")
            
            # Get deal-level audit logs
            deal_logs, _ = self.get_audit_logs(
                db=db,
                target_type="deal",
                target_id=deal_id,
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            # Get document audit logs (all documents in deal)
            documents = db.query(Document).filter(Document.deal_id == deal_id).all()
            document_ids = [doc.id for doc in documents]
            
            document_logs = []
            if document_ids:
                # Query all document logs and filter in memory (SQLAlchemy limitation)
                all_doc_logs, _ = self.get_audit_logs(
                    db=db,
                    target_type="document",
                    start_date=start_date,
                    end_date=end_date,
                    limit=10000  # Large limit to get all
                )
                # Filter to only documents in this deal
                document_logs = [log for log in all_doc_logs if log.target_id in document_ids]
            
            # Get workflow audit logs
            workflows = db.query(Workflow).filter(Workflow.document_id.in_(document_ids)).all() if document_ids else []
            workflow_ids = [wf.id for wf in workflows]
            
            workflow_logs = []
            if workflow_ids:
                all_workflow_logs, _ = self.get_audit_logs(
                    db=db,
                    target_type="workflow",
                    start_date=start_date,
                    end_date=end_date,
                    limit=10000
                )
                workflow_logs = [log for log in all_workflow_logs if log.target_id in workflow_ids]
            
            # Get policy decision audit logs
            from app.services.policy_audit import get_policy_decisions
            policy_decisions = get_policy_decisions(
                db=db,
                transaction_id=deal.deal_id,
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            # Combine and sort all audit logs
            all_logs = deal_logs + document_logs + workflow_logs
            all_logs.sort(key=lambda x: x.occurred_at, reverse=True)
            
            # Return comprehensive audit trail
            return {
                "deal": {
                    "id": deal.id,
                    "deal_id": deal.deal_id,
                    "title": getattr(deal, "title", None) or deal.deal_id,
                    "status": deal.status,
                    "created_at": deal.created_at.isoformat() if deal.created_at else None,
                    "updated_at": deal.updated_at.isoformat() if deal.updated_at else None,
                },
                "audit_logs": [self._enrich_audit_log(log) for log in all_logs],
                "policy_decisions": [pd.to_dict() for pd in policy_decisions],
                "summary": {
                    "total_logs": len(all_logs),
                    "total_policy_decisions": len(policy_decisions),
                    "date_range": {
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None,
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get deal audit trail: {e}", exc_info=True)
            raise
    
    def get_loan_audit_trail(
        self,
        db: Session,
        loan_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive audit trail for a loan asset.
        
        Args:
            db: Database session
            loan_id: Loan ID (external identifier)
            start_date: Filter from date
            end_date: Filter to date
            
        Returns:
            Dictionary with loan info and audit logs
        """
        try:
            # Fetch loan asset (SQLModel)
            from sqlmodel import select
            loan = db.exec(select(LoanAsset).where(LoanAsset.loan_id == loan_id)).first()
            if not loan:
                raise ValueError(f"Loan {loan_id} not found")
            
            # Get verification audit logs
            verification_logs = []
            # Note: VerificationAuditLog links to VerificationRequest, not directly to LoanAsset
            # We'll need to query through verification requests if that relationship exists
            # For now, we'll get policy decisions and audit logs related to the loan
            
            # Get policy decision audit logs
            from app.services.policy_audit import get_policy_decisions
            policy_decisions = get_policy_decisions(
                db=db,
                transaction_id=loan_id,
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            # Get audit logs that reference this loan (via metadata or target_id)
            # Since LoanAsset uses SQLModel, we'll search by loan_id in metadata
            loan_logs, _ = self.get_audit_logs(
                db=db,
                target_type="loan_asset",
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            # Filter to this specific loan
            loan_logs = [
                log for log in loan_logs
                if log.target_id and str(log.target_id) == str(loan.id)
            ]
            
            # Combine and sort
            all_logs = loan_logs + verification_logs
            all_logs.sort(key=lambda x: x.occurred_at, reverse=True)
            
            # Return comprehensive audit trail
            return {
                "loan": {
                    "id": loan.id,
                    "loan_id": loan.loan_id,
                    "risk_status": loan.risk_status,
                    "last_verified_score": loan.last_verified_score,
                    "created_at": loan.created_at.isoformat() if loan.created_at else None,
                    "last_verified_at": loan.last_verified_at.isoformat() if loan.last_verified_at else None,
                },
                "audit_logs": [self._enrich_audit_log(log) for log in all_logs],
                "policy_decisions": [pd.to_dict() for pd in policy_decisions],
                "verification_logs": [log.to_dict() for log in verification_logs],
                "summary": {
                    "total_logs": len(all_logs),
                    "total_policy_decisions": len(policy_decisions),
                    "total_verification_logs": len(verification_logs),
                    "date_range": {
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None,
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get loan audit trail: {e}", exc_info=True)
            raise
    
    def get_filing_audit_trail(
        self,
        db: Session,
        filing_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive audit trail for a regulatory filing.
        
        Note: Filing model may not exist yet. This is a placeholder implementation.
        
        Args:
            db: Database session
            filing_id: Filing ID
            start_date: Filter from date
            end_date: Filter to date
            
        Returns:
            Dictionary with filing info and audit logs
        """
        try:
            # TODO: Implement when Filing model is created
            # For now, return structure for future implementation
            
            # Get filing-level audit logs
            filing_logs, _ = self.get_audit_logs(
                db=db,
                target_type="filing",
                target_id=filing_id,
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            # Get policy decision audit logs (if filing has transaction_id)
            # This would need to be implemented when Filing model exists
            
            return {
                "filing": {
                    "id": filing_id,
                    "status": "unknown",  # Placeholder
                },
                "audit_logs": [self._enrich_audit_log(log) for log in filing_logs],
                "policy_decisions": [],
                "summary": {
                    "total_logs": len(filing_logs),
                    "total_policy_decisions": 0,
                    "date_range": {
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None,
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get filing audit trail: {e}", exc_info=True)
            raise
    
    def get_related_audit_events(
        self,
        db: Session,
        target_type: str,
        target_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get related audit events for an entity.
        
        Args:
            db: Database session
            target_type: Type of entity
            target_id: ID of entity
            limit: Maximum results
            
        Returns:
            List of enriched audit log dictionaries
        """
        try:
            logs, _ = self.get_audit_logs(
                db=db,
                target_type=target_type,
                target_id=target_id,
                limit=limit
            )
            
            return [self._enrich_audit_log(log) for log in logs]
            
        except Exception as e:
            logger.error(f"Failed to get related audit events: {e}", exc_info=True)
            raise
    
    def enrich_audit_log(
        self,
        db: Session,
        audit_log: AuditLog
    ) -> Dict[str, Any]:
        """
        Add related entity details to audit log.
        
        Args:
            db: Database session
            audit_log: AuditLog instance
            
        Returns:
            Enriched audit log dictionary
        """
        return self._enrich_audit_log(audit_log)
    
    def _enrich_audit_log(self, audit_log: AuditLog) -> Dict[str, Any]:
        """
        Internal method to enrich audit log with related entity details.
        
        Args:
            audit_log: AuditLog instance
            
        Returns:
            Enriched audit log dictionary
        """
        result = audit_log.to_dict()
        
        # Add user information if available
        if audit_log.user:
            result["user"] = {
                "id": audit_log.user.id,
                "name": audit_log.user.display_name,
                "email": audit_log.user.email,
                "role": audit_log.user.role.value if hasattr(audit_log.user.role, 'value') else str(audit_log.user.role)
            }
        else:
            result["user"] = None
        
        # Add related entity information based on target_type
        if audit_log.target_type and audit_log.target_id:
            # This would require additional queries, so we'll add a placeholder
            # that can be expanded later
            result["related_entity"] = {
                "type": audit_log.target_type,
                "id": audit_log.target_id
            }
        
        return result
