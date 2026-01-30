"""Service for GDPR breach notification (Article 33, 34)."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import BreachRecord, User, AuditAction
from app.utils.audit import log_audit_action

logger = logging.getLogger(__name__)


class BreachNotificationService:
    """Service for GDPR breach notification and management.
    
    Implements:
    - Article 33: Notification to supervisory authority (within 72 hours)
    - Article 34: Notification to affected users (without undue delay)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def record_breach(
        self,
        breach_type: str,
        breach_description: str,
        affected_users: List[int],
        affected_data_types: Optional[List[str]] = None,
        risk_level: str = "medium",
        discovered_by_user_id: Optional[int] = None,
        breach_discovered_at: Optional[datetime] = None
    ) -> BreachRecord:
        """Record a data breach.
        
        Args:
            breach_type: Type of breach (unauthorized_access, data_loss, encryption_failure, etc.)
            breach_description: Detailed description of the breach
            affected_users: List of affected user IDs
            affected_data_types: Types of data affected (email, password, financial_data, etc.)
            risk_level: Risk level (low, medium, high, critical)
            discovered_by_user_id: User ID who discovered the breach (admin/system)
            breach_discovered_at: When the breach was discovered (defaults to now)
            
        Returns:
            Created BreachRecord
        """
        if breach_discovered_at is None:
            breach_discovered_at = datetime.utcnow()
        
        breach = BreachRecord(
            breach_type=breach_type,
            breach_description=breach_description,
            breach_discovered_at=breach_discovered_at,
            affected_users_count=len(affected_users) if affected_users else 0,
            risk_level=risk_level
        )
        
        self.db.add(breach)
        self.db.commit()
        self.db.refresh(breach)
        
        # Log audit action
        log_audit_action(
            self.db,
            AuditAction.CREATE,
            "breach_record",
            breach.id,
            discovered_by_user_id,
            action_metadata={
                "breach_type": breach_type,
                "risk_level": risk_level,
                "affected_users_count": len(affected_users) if affected_users else 0
            }
        )
        
        # Auto-notify if high risk (within 72 hours for supervisory authority)
        if risk_level in ["high", "critical"]:
            await self.notify_supervisory_authority(breach)
        
        # Notify affected users without undue delay if high risk
        if risk_level in ["high", "critical"] and affected_users:
            await self.notify_affected_users(breach, affected_users)
        
        return breach
    
    async def notify_supervisory_authority(
        self,
        breach: BreachRecord
    ) -> bool:
        """Notify supervisory authority within 72 hours (Article 33).
        
        Args:
            breach: BreachRecord to notify about
            
        Returns:
            True if notification was successful
        """
        try:
            # Check if 72 hours have passed
            time_since_discovery = datetime.utcnow() - breach.breach_discovered_at
            if time_since_discovery > timedelta(hours=72):
                logger.warning(
                    f"Breach {breach.id} discovered more than 72 hours ago. "
                    "Notification may be late."
                )
            
            # In production, this would send actual notification to DPA
            # For now, we mark as notified and log
            breach.supervisory_authority_notified = True
            breach.supervisory_authority_notified_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(
                f"Supervisory authority notified of breach {breach.id} "
                f"(risk level: {breach.risk_level})"
            )
            
            # Log audit action
            log_audit_action(
                self.db,
                AuditAction.UPDATE,
                "breach_record",
                breach.id,
                None,  # System action
                action_metadata={
                    "action": "supervisory_authority_notified",
                    "notified_at": breach.supervisory_authority_notified_at.isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to notify supervisory authority for breach {breach.id}: {e}")
            return False
    
    async def notify_affected_users(
        self,
        breach: BreachRecord,
        user_ids: List[int]
    ) -> Dict[str, Any]:
        """Notify affected users without undue delay (Article 34).
        
        Args:
            breach: BreachRecord to notify about
            user_ids: List of affected user IDs
            
        Returns:
            Dictionary with notification results
        """
        results = {
            "notified_count": 0,
            "failed_count": 0,
            "errors": []
        }
        
        try:
            users = self.db.query(User).filter(User.id.in_(user_ids)).all()
            
            for user in users:
                try:
                    # In production, this would send actual email notification
                    # For now, we log and mark as notified
                    logger.info(
                        f"Notifying user {user.id} ({user.email}) about breach {breach.id}"
                    )
                    
                    # TODO: Send email notification
                    # await send_breach_notification_email(user, breach)
                    
                    results["notified_count"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to notify user {user.id}: {e}")
                    results["failed_count"] += 1
                    results["errors"].append(f"User {user.id}: {str(e)}")
            
            # Mark breach as users notified
            breach.users_notified = True
            breach.users_notified_at = datetime.utcnow()
            self.db.commit()
            
            # Log audit action
            log_audit_action(
                self.db,
                AuditAction.UPDATE,
                "breach_record",
                breach.id,
                None,  # System action
                action_metadata={
                    "action": "users_notified",
                    "notified_count": results["notified_count"],
                    "failed_count": results["failed_count"],
                    "notified_at": breach.users_notified_at.isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to notify affected users for breach {breach.id}: {e}")
            results["errors"].append(f"General error: {str(e)}")
        
        return results
    
    async def contain_breach(
        self,
        breach_id: int,
        containment_actions: Optional[List[str]] = None
    ) -> BreachRecord:
        """Mark breach as contained and record containment actions.
        
        Args:
            breach_id: ID of breach to contain
            containment_actions: List of actions taken to contain the breach
            
        Returns:
            Updated BreachRecord
        """
        breach = self.db.query(BreachRecord).filter(
            BreachRecord.id == breach_id
        ).first()
        
        if not breach:
            raise ValueError(f"Breach {breach_id} not found")
        
        breach.breach_contained_at = datetime.utcnow()
        if containment_actions:
            # Store containment actions in metadata (if we add that field)
            pass
        
        self.db.commit()
        self.db.refresh(breach)
        
        logger.info(f"Breach {breach_id} marked as contained")
        
        return breach
    
    def get_breach(self, breach_id: int) -> Optional[BreachRecord]:
        """Get breach record by ID.
        
        Args:
            breach_id: ID of breach
            
        Returns:
            BreachRecord or None
        """
        return self.db.query(BreachRecord).filter(
            BreachRecord.id == breach_id
        ).first()
    
    def list_breaches(
        self,
        risk_level: Optional[str] = None,
        notified_only: bool = False,
        limit: int = 100
    ) -> List[BreachRecord]:
        """List breach records with optional filters.
        
        Args:
            risk_level: Filter by risk level (low, medium, high, critical)
            notified_only: Only return breaches that have been notified
            limit: Maximum number of records to return
            
        Returns:
            List of BreachRecord
        """
        query = self.db.query(BreachRecord)
        
        if risk_level:
            query = query.filter(BreachRecord.risk_level == risk_level)
        
        if notified_only:
            query = query.filter(BreachRecord.supervisory_authority_notified == True)
        
        return query.order_by(BreachRecord.breach_discovered_at.desc()).limit(limit).all()
    
    def get_breach_statistics(self) -> Dict[str, Any]:
        """Get breach statistics for reporting.
        
        Returns:
            Dictionary with breach statistics
        """
        total_breaches = self.db.query(BreachRecord).count()
        
        by_risk = {}
        for risk in ["low", "medium", "high", "critical"]:
            by_risk[risk] = self.db.query(BreachRecord).filter(
                BreachRecord.risk_level == risk
            ).count()
        
        notified_count = self.db.query(BreachRecord).filter(
            BreachRecord.supervisory_authority_notified == True
        ).count()
        
        users_notified_count = self.db.query(BreachRecord).filter(
            BreachRecord.users_notified == True
        ).count()
        
        return {
            "total_breaches": total_breaches,
            "by_risk_level": by_risk,
            "supervisory_authority_notified": notified_count,
            "users_notified": users_notified_count,
            "notification_compliance_rate": (
                notified_count / total_breaches * 100 if total_breaches > 0 else 0
            )
        }
