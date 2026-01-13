"""
Audit Statistics Service for CreditNexus.

Provides aggregated statistics and analytics for audit data.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.services.audit_service import AuditService
from app.services.policy_audit import get_policy_statistics
from app.db.models import AuditLog, User

logger = logging.getLogger(__name__)


class AuditStatisticsService:
    """Service for generating audit statistics and analytics."""
    
    def __init__(self):
        """Initialize audit statistics service."""
        self.audit_service = AuditService()
    
    def get_overview_statistics(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get high-level overview statistics.
        
        Args:
            db: Database session
            start_date: Filter from date
            end_date: Filter to date
            
        Returns:
            Dictionary with overview statistics
        """
        try:
            # Build base query
            query = db.query(AuditLog)
            
            # Apply date filters
            if start_date:
                query = query.filter(AuditLog.occurred_at >= start_date)
            if end_date:
                query = query.filter(AuditLog.occurred_at <= end_date)
            
            # Total audit logs
            total_logs = query.count()
            
            # Count by action type
            action_counts = (
                query.with_entities(
                    AuditLog.action,
                    func.count(AuditLog.id).label('count')
                )
                .group_by(AuditLog.action)
                .all()
            )
            actions = {action: count for action, count in action_counts}
            
            # Count by target type
            target_type_counts = (
                query.with_entities(
                    AuditLog.target_type,
                    func.count(AuditLog.id).label('count')
                )
                .group_by(AuditLog.target_type)
                .all()
            )
            target_types = {target_type: count for target_type, count in target_type_counts}
            
            # Unique users
            unique_users = (
                query.filter(AuditLog.user_id.isnot(None))
                .with_entities(func.count(func.distinct(AuditLog.user_id)))
                .scalar() or 0
            )
            
            return {
                "total_logs": total_logs,
                "actions": actions,
                "target_types": target_types,
                "unique_users": unique_users,
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None,
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get overview statistics: {e}", exc_info=True)
            raise
    
    def get_activity_timeline(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "day"
    ) -> List[Dict[str, Any]]:
        """
        Get activity timeline over time.
        
        Args:
            db: Database session
            start_date: Filter from date
            end_date: Filter to date
            interval: Time interval ('day', 'hour', 'week')
            
        Returns:
            List of timeline data points
        """
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Build base query
            query = db.query(AuditLog).filter(
                and_(
                    AuditLog.occurred_at >= start_date,
                    AuditLog.occurred_at <= end_date
                )
            )
            
            timeline = []
            current_date = start_date
            
            if interval == "day":
                while current_date <= end_date:
                    day_start = datetime.combine(current_date.date(), datetime.min.time())
                    day_end = datetime.combine(current_date.date(), datetime.max.time())
                    
                    day_count = query.filter(
                        and_(
                            AuditLog.occurred_at >= day_start,
                            AuditLog.occurred_at <= day_end
                        )
                    ).count()
                    
                    timeline.append({
                        "date": current_date.date().isoformat(),
                        "count": day_count
                    })
                    
                    current_date += timedelta(days=1)
            
            elif interval == "hour":
                while current_date <= end_date:
                    hour_end = current_date + timedelta(hours=1)
                    
                    hour_count = query.filter(
                        and_(
                            AuditLog.occurred_at >= current_date,
                            AuditLog.occurred_at < hour_end
                        )
                    ).count()
                    
                    timeline.append({
                        "date": current_date.isoformat(),
                        "count": hour_count
                    })
                    
                    current_date = hour_end
            
            elif interval == "week":
                while current_date <= end_date:
                    week_end = current_date + timedelta(weeks=1)
                    
                    week_count = query.filter(
                        and_(
                            AuditLog.occurred_at >= current_date,
                            AuditLog.occurred_at < week_end
                        )
                    ).count()
                    
                    timeline.append({
                        "date": current_date.date().isoformat(),
                        "count": week_count
                    })
                    
                    current_date = week_end
            
            return timeline
            
        except Exception as e:
            logger.error(f"Failed to get activity timeline: {e}", exc_info=True)
            raise
    
    def get_top_users(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top users by audit activity.
        
        Args:
            db: Database session
            start_date: Filter from date
            end_date: Filter to date
            limit: Maximum results
            
        Returns:
            List of user statistics
        """
        try:
            # Build base query
            query = db.query(AuditLog).filter(AuditLog.user_id.isnot(None))
            
            # Apply date filters
            if start_date:
                query = query.filter(AuditLog.occurred_at >= start_date)
            if end_date:
                query = query.filter(AuditLog.occurred_at <= end_date)
            
            # Count by user
            user_counts = (
                query.with_entities(
                    AuditLog.user_id,
                    func.count(AuditLog.id).label('count')
                )
                .group_by(AuditLog.user_id)
                .order_by(func.count(AuditLog.id).desc())
                .limit(limit)
                .all()
            )
            
            # Enrich with user information
            top_users = []
            for user_id, count in user_counts:
                user = db.query(User).filter(User.id == user_id).first()
                top_users.append({
                    "user_id": user_id,
                    "user_name": user.display_name if user else "Unknown",
                    "user_email": user.email if user else None,
                    "count": count
                })
            
            return top_users
            
        except Exception as e:
            logger.error(f"Failed to get top users: {e}", exc_info=True)
            raise
    
    def get_top_actions(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top actions by frequency.
        
        Args:
            db: Database session
            start_date: Filter from date
            end_date: Filter to date
            limit: Maximum results
            
        Returns:
            List of action statistics
        """
        try:
            # Build base query
            query = db.query(AuditLog)
            
            # Apply date filters
            if start_date:
                query = query.filter(AuditLog.occurred_at >= start_date)
            if end_date:
                query = query.filter(AuditLog.occurred_at <= end_date)
            
            # Count by action
            action_counts = (
                query.with_entities(
                    AuditLog.action,
                    func.count(AuditLog.id).label('count')
                )
                .group_by(AuditLog.action)
                .order_by(func.count(AuditLog.id).desc())
                .limit(limit)
                .all()
            )
            
            return [
                {"action": action, "count": count}
                for action, count in action_counts
            ]
            
        except Exception as e:
            logger.error(f"Failed to get top actions: {e}", exc_info=True)
            raise
    
    def get_policy_decision_summary(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get policy decision summary statistics.
        
        Args:
            db: Database session
            start_date: Filter from date
            end_date: Filter to date
            
        Returns:
            Dictionary with policy decision statistics
        """
        try:
            return get_policy_statistics(
                db=db,
                start_date=start_date,
                end_date=end_date
            )
            
        except Exception as e:
            logger.error(f"Failed to get policy decision summary: {e}", exc_info=True)
            raise
    
    def get_anomaly_detection(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect unusual patterns in audit logs.
        
        Args:
            db: Database session
            start_date: Filter from date
            end_date: Filter to date
            
        Returns:
            List of detected anomalies
        """
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            anomalies = []
            
            # Detect unusual spike in activity
            timeline = self.get_activity_timeline(db, start_date, end_date, interval="day")
            if timeline:
                counts = [point["count"] for point in timeline]
                if counts:
                    mean_count = sum(counts) / len(counts)
                    std_count = (sum((x - mean_count) ** 2 for x in counts) / len(counts)) ** 0.5
                    
                    # Find days with activity > 2 standard deviations above mean
                    for point in timeline:
                        if point["count"] > mean_count + 2 * std_count:
                            anomalies.append({
                                "type": "activity_spike",
                                "date": point["date"],
                                "count": point["count"],
                                "expected_range": f"{mean_count:.1f} ± {std_count:.1f}",
                                "severity": "medium"
                            })
            
            # Detect unusual user activity
            top_users = self.get_top_users(db, start_date, end_date, limit=20)
            if top_users:
                user_counts = [user["count"] for user in top_users]
                if user_counts:
                    mean_user_count = sum(user_counts) / len(user_counts)
                    std_user_count = (sum((x - mean_user_count) ** 2 for x in user_counts) / len(user_counts)) ** 0.5
                    
                    # Find users with activity > 2 standard deviations above mean
                    for user in top_users:
                        if user["count"] > mean_user_count + 2 * std_user_count:
                            anomalies.append({
                                "type": "user_activity_spike",
                                "user_id": user["user_id"],
                                "user_name": user["user_name"],
                                "count": user["count"],
                                "expected_range": f"{mean_user_count:.1f} ± {std_user_count:.1f}",
                                "severity": "low"
                            })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}", exc_info=True)
            raise
