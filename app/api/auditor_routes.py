"""
Auditor API routes for CreditNexus.

Provides endpoints for auditor interface including dashboard, audit logs,
entity-specific audit trails, report generation, and export functionality.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import io

from app.db import get_db
from app.db.models import User, AuditLog
from app.auth.jwt_auth import require_auth
from app.core.permissions import has_permission, PERMISSION_AUDIT_VIEW, PERMISSION_AUDIT_EXPORT
from app.services.audit_service import AuditService
from app.services.audit_statistics_service import AuditStatisticsService
from app.services.audit_report_service import AuditReportService
from app.services.audit_export_service import AuditExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auditor", tags=["auditor"])


# Request/Response Models
class GenerateReportRequest(BaseModel):
    """Request model for report generation."""
    report_type: str = Field(description="Type of report: overview, deal, loan, filing, custom")
    date_range: Dict[str, Optional[str]] = Field(description="Date range with start and end (ISO format)")
    entity_selection: Optional[Dict[str, Any]] = Field(None, description="Entity selection (type and ids)")
    template: str = Field(default="standard", description="Report template: standard, comprehensive, executive")
    include_sections: Optional[Dict[str, bool]] = Field(None, description="Sections to include in report")


# Dependency to get services
def get_audit_service() -> AuditService:
    """Get audit service instance."""
    return AuditService()


def get_statistics_service() -> AuditStatisticsService:
    """Get statistics service instance."""
    return AuditStatisticsService()


def get_report_service() -> AuditReportService:
    """Get report service instance."""
    return AuditReportService()


def get_export_service() -> AuditExportService:
    """Get export service instance."""
    return AuditExportService()


@router.get("/dashboard")
async def get_auditor_dashboard(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    statistics_service: AuditStatisticsService = Depends(get_statistics_service),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get auditor dashboard statistics.
    
    Requires AUDIT_VIEW permission.
    """
    # Check permissions
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get overview statistics
        overview = statistics_service.get_overview_statistics(
            db=db,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Get activity timeline
        timeline = statistics_service.get_activity_timeline(
            db=db,
            start_date=start_dt or (datetime.utcnow() - timedelta(days=30)),
            end_date=end_dt or datetime.utcnow()
        )
        
        # Get top users
        top_users = statistics_service.get_top_users(
            db=db,
            start_date=start_dt,
            end_date=end_dt,
            limit=10
        )
        
        # Get top actions
        top_actions = statistics_service.get_top_actions(
            db=db,
            start_date=start_dt,
            end_date=end_dt,
            limit=10
        )
        
        # Get policy decision summary
        from app.services.policy_audit import get_policy_statistics
        policy_stats = get_policy_statistics(
            db=db,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Get recent audit events
        recent_logs, _ = audit_service.get_audit_logs(
            db=db,
            start_date=start_dt,
            end_date=end_dt,
            limit=20
        )
        
        # Return dashboard data
        return {
            "status": "success",
            "overview": overview,
            "timeline": timeline,
            "top_users": top_users,
            "top_actions": top_actions,
            "policy_decisions": policy_stats,
            "recent_events": [audit_service.enrich_audit_log(db, log) for log in recent_logs]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get auditor dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.get("/logs")
async def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    target_id: Optional[int] = Query(None, description="Filter by target ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get audit logs with advanced filtering.
    
    Requires AUDIT_VIEW permission.
    """
    # Check permissions
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get audit logs
        logs, total = audit_service.get_audit_logs(
            db=db,
            action=action,
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit,
            offset=offset
        )
        
        # Enrich logs
        enriched_logs = [audit_service.enrich_audit_log(db, log) for log in logs]
        
        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": enriched_logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get audit logs: {str(e)}")


@router.get("/logs/{log_id}")
async def get_audit_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get detailed audit log entry with related events.
    
    Requires AUDIT_VIEW permission.
    """
    # Check permissions
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Get audit log
        log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")
        
        # Enrich log
        enriched_log = audit_service.enrich_audit_log(db, log)
        
        # Get related events
        if log.target_type and log.target_id:
            related_events = audit_service.get_related_audit_events(
                db=db,
                target_type=log.target_type,
                target_id=log.target_id,
                limit=50
            )
        else:
            related_events = []
        
        return {
            "status": "success",
            "log": enriched_log,
            "related_events": related_events
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit log detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get audit log: {str(e)}")


@router.get("/deals/{deal_id}/audit")
async def get_deal_audit_trail(
    deal_id: int,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get comprehensive audit trail for a deal.
    
    Requires AUDIT_VIEW permission.
    """
    # Check permissions
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get deal audit trail
        trail = audit_service.get_deal_audit_trail(
            db=db,
            deal_id=deal_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return {
            "status": "success",
            **trail
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deal audit trail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get deal audit trail: {str(e)}")


@router.get("/loans/{loan_id}/audit")
async def get_loan_audit_trail(
    loan_id: str,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get comprehensive audit trail for a loan asset.
    
    Requires AUDIT_VIEW permission.
    """
    # Check permissions
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get loan audit trail
        trail = audit_service.get_loan_audit_trail(
            db=db,
            loan_id=loan_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return {
            "status": "success",
            **trail
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get loan audit trail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get loan audit trail: {str(e)}")


@router.get("/filings/{filing_id}/audit")
async def get_filing_audit_trail(
    filing_id: int,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get comprehensive audit trail for a regulatory filing.
    
    Requires AUDIT_VIEW permission.
    """
    # Check permissions
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get filing audit trail
        trail = audit_service.get_filing_audit_trail(
            db=db,
            filing_id=filing_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return {
            "status": "success",
            **trail
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get filing audit trail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get filing audit trail: {str(e)}")


@router.post("/reports/generate")
async def generate_audit_report(
    request: GenerateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    report_service: AuditReportService = Depends(get_report_service)
):
    """
    Generate comprehensive audit report.
    
    Requires AUDIT_VIEW permission.
    """
    # Check permissions
    if not has_permission(current_user, PERMISSION_AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse date range
        date_range = {
            "start": None,
            "end": None
        }
        if request.date_range.get("start"):
            try:
                date_range["start"] = datetime.fromisoformat(request.date_range["start"].replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start date format")
        if request.date_range.get("end"):
            try:
                date_range["end"] = datetime.fromisoformat(request.date_range["end"].replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end date format")
        
        # Generate report
        report = report_service.generate_report(
            db=db,
            report_type=request.report_type,
            date_range=date_range,
            entity_selection=request.entity_selection,
            template=request.template,
            include_sections=request.include_sections
        )
        
        return {
            "status": "success",
            "report_id": report["report_id"],
            "status": "completed",
            "report": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/export")
async def export_audit_data(
    format: str = Query("csv", description="Export format: csv, excel, pdf"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
    audit_service: AuditService = Depends(get_audit_service),
    export_service: AuditExportService = Depends(get_export_service)
):
    """
    Export audit data to various formats.
    
    Requires AUDIT_EXPORT permission.
    """
    # Check permissions
    if not has_permission(current_user, PERMISSION_AUDIT_EXPORT):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get audit logs
        logs, _ = audit_service.get_audit_logs(
            db=db,
            action=action,
            target_type=target_type,
            start_date=start_dt,
            end_date=end_dt,
            limit=10000  # Large limit for export
        )
        
        # Export based on format
        if format == "csv":
            content = export_service.export_to_csv(db, logs, include_metadata=True)
            media_type = "text/csv"
            filename = f"audit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        elif format == "excel":
            content = export_service.export_to_excel(db, logs, include_metadata=True)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"audit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        elif format == "pdf":
            content = export_service.export_to_pdf(db, logs, title="Audit Report")
            media_type = "application/pdf"
            filename = f"audit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export audit data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")
