"""
Audit Report Service for CreditNexus.

Generates comprehensive audit reports with LLM integration for executive summaries,
compliance analysis, and recommendations.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.audit_service import AuditService
from app.services.audit_statistics_service import AuditStatisticsService
from app.services.audit_export_service import AuditExportService
from app.chains.audit_report_chain import AuditReportChain
from app.chains.clause_analysis_chain import ClauseAnalysisChain

logger = logging.getLogger(__name__)


class AuditReportService:
    """Service for generating comprehensive audit reports."""
    
    def __init__(self):
        """Initialize audit report service."""
        self.audit_service = AuditService()
        self.statistics_service = AuditStatisticsService()
        self.export_service = AuditExportService()
        self.report_chain = AuditReportChain()
        self.clause_analysis_chain = ClauseAnalysisChain()
    
    def generate_report(
        self,
        db: Session,
        report_type: str,
        date_range: Dict[str, Optional[datetime]],
        entity_selection: Optional[Dict[str, Any]] = None,
        template: str = "standard",
        include_sections: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive audit report.
        
        Args:
            db: Database session
            report_type: Type of report ('overview', 'deal', 'loan', 'filing', 'custom')
            date_range: Dictionary with 'start' and 'end' datetime objects
            entity_selection: Optional entity selection (type and ids)
            template: Report template ('standard', 'comprehensive', 'executive')
            include_sections: Dictionary of sections to include
            
        Returns:
            Dictionary with report data and metadata
        """
        try:
            report_id = str(uuid.uuid4())
            start_date = date_range.get("start")
            end_date = date_range.get("end")
            
            # Default sections
            if include_sections is None:
                include_sections = {
                    "executive_summary": True,
                    "compliance_analysis": True,
                    "recommendations": True,
                    "detailed_trail": True
                }
            
            # Gather audit data based on report type
            audit_data = self.process_audit_data(
                db=db,
                report_type=report_type,
                date_range=date_range,
                entity_selection=entity_selection
            )
            
            # Generate LLM-powered sections
            report_sections = {}
            
            if include_sections.get("executive_summary", False):
                report_sections["executive_summary"] = self.generate_executive_summary(
                    audit_data=audit_data,
                    date_range={
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None
                    }
                )
            
            if include_sections.get("compliance_analysis", False):
                policy_decisions = audit_data.get("policy_decisions", [])
                audit_logs = audit_data.get("audit_logs", [])
                report_sections["compliance_analysis"] = self.generate_compliance_analysis(
                    policy_decisions=policy_decisions,
                    audit_logs=audit_logs
                )
            
            if include_sections.get("recommendations", False):
                anomalies = audit_data.get("anomalies", [])
                compliance_analysis = report_sections.get("compliance_analysis")
                report_sections["recommendations"] = self.generate_recommendations(
                    audit_data=audit_data,
                    compliance_analysis=compliance_analysis,
                    anomalies=anomalies
                )
            
            # Combine data and LLM output
            report = self.render_report(
                report_id=report_id,
                report_type=report_type,
                template=template,
                audit_data=audit_data,
                report_sections=report_sections,
                date_range=date_range
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}", exc_info=True)
            raise
    
    def generate_executive_summary(
        self,
        audit_data: Dict[str, Any],
        date_range: Dict[str, Optional[str]]
    ) -> Dict[str, Any]:
        """
        Generate executive summary using LLM.
        
        Args:
            audit_data: Dictionary containing audit statistics
            date_range: Dictionary with start and end dates
            
        Returns:
            Executive summary dictionary
        """
        try:
            summary = self.report_chain.generate_executive_summary(
                audit_data=audit_data,
                date_range=date_range
            )
            return summary.model_dump()
            
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}", exc_info=True)
            # Return fallback summary
            return {
                "overview": "Executive summary generation failed. Please review audit data manually.",
                "key_findings": [],
                "risk_assessment": "Unable to assess",
                "recommendations": []
            }
    
    def generate_compliance_analysis(
        self,
        policy_decisions: List[Dict[str, Any]],
        audit_logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate compliance analysis using LLM.
        
        Args:
            policy_decisions: List of policy decision dictionaries
            audit_logs: List of audit log dictionaries
            
        Returns:
            Compliance analysis dictionary
        """
        try:
            analysis = self.report_chain.analyze_compliance(
                policy_decisions=policy_decisions,
                audit_logs=audit_logs
            )
            return analysis.model_dump()
            
        except Exception as e:
            logger.error(f"Failed to generate compliance analysis: {e}", exc_info=True)
            # Return fallback analysis
            return {
                "compliance_status": "UNKNOWN",
                "violations": [],
                "policy_decisions_summary": {},
                "critical_issues": []
            }
    
    def generate_recommendations(
        self,
        audit_data: Dict[str, Any],
        compliance_analysis: Optional[Dict[str, Any]],
        anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate recommendations using LLM.
        
        Args:
            audit_data: Dictionary containing audit statistics
            compliance_analysis: Compliance analysis results
            anomalies: List of detected anomalies
            
        Returns:
            Recommendations dictionary
        """
        try:
            # Convert compliance_analysis dict to ComplianceAnalysis model if needed
            from app.chains.audit_report_chain import ComplianceAnalysis
            
            compliance_model = None
            if compliance_analysis:
                try:
                    compliance_model = ComplianceAnalysis(**compliance_analysis)
                except Exception:
                    # If conversion fails, create a basic model
                    compliance_model = ComplianceAnalysis(
                        compliance_status="UNKNOWN",
                        violations=[],
                        policy_decisions_summary={},
                        critical_issues=[]
                    )
            
            recommendations = self.report_chain.generate_recommendations(
                audit_data=audit_data,
                compliance_analysis=compliance_model or ComplianceAnalysis(
                    compliance_status="UNKNOWN",
                    violations=[],
                    policy_decisions_summary={},
                    critical_issues=[]
                ),
                anomalies=anomalies
            )
            return recommendations.model_dump()
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}", exc_info=True)
            # Return fallback recommendations
            return {
                "immediate_actions": [],
                "short_term_improvements": [],
                "long_term_strategies": []
            }
    
    def process_audit_data(
        self,
        db: Session,
        report_type: str,
        date_range: Dict[str, Optional[datetime]],
        entity_selection: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process and gather audit data for report generation.
        
        Args:
            db: Database session
            report_type: Type of report
            date_range: Dictionary with start and end dates
            entity_selection: Optional entity selection
            
        Returns:
            Dictionary with processed audit data
        """
        try:
            start_date = date_range.get("start")
            end_date = date_range.get("end")
            
            # Get overview statistics
            overview = self.statistics_service.get_overview_statistics(
                db=db,
                start_date=start_date,
                end_date=end_date
            )
            
            # Get activity timeline
            timeline = self.statistics_service.get_activity_timeline(
                db=db,
                start_date=start_date,
                end_date=end_date,
                interval="day"
            )
            
            # Get top users and actions
            top_users = self.statistics_service.get_top_users(
                db=db,
                start_date=start_date,
                end_date=end_date,
                limit=10
            )
            
            top_actions = self.statistics_service.get_top_actions(
                db=db,
                start_date=start_date,
                end_date=end_date,
                limit=10
            )
            
            # Get policy decision summary
            policy_stats = self.statistics_service.get_policy_decision_summary(
                db=db,
                start_date=start_date,
                end_date=end_date
            )
            
            # Get policy decisions (for compliance analysis)
            from app.services.policy_audit import get_policy_decisions
            policy_decisions = get_policy_decisions(
                db=db,
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            # Get audit logs
            audit_logs, total_logs = self.audit_service.get_audit_logs(
                db=db,
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            # Get anomalies
            anomalies = self.statistics_service.get_anomaly_detection(
                db=db,
                start_date=start_date,
                end_date=end_date
            )
            
            # Entity-specific data
            entity_data = {}
            if report_type == "deal" and entity_selection:
                deal_ids = entity_selection.get("ids", [])
                if deal_ids:
                    entity_data["deals"] = []
                    for deal_id in deal_ids[:10]:  # Limit to 10 deals
                        try:
                            trail = self.audit_service.get_deal_audit_trail(
                                db=db,
                                deal_id=deal_id,
                                start_date=start_date,
                                end_date=end_date
                            )
                            entity_data["deals"].append(trail)
                        except Exception as e:
                            logger.warning(f"Failed to get deal audit trail for {deal_id}: {e}")
            
            elif report_type == "loan" and entity_selection:
                loan_ids = entity_selection.get("ids", [])
                if loan_ids:
                    entity_data["loans"] = []
                    for loan_id in loan_ids[:10]:  # Limit to 10 loans
                        try:
                            trail = self.audit_service.get_loan_audit_trail(
                                db=db,
                                loan_id=loan_id,
                                start_date=start_date,
                                end_date=end_date
                            )
                            entity_data["loans"].append(trail)
                        except Exception as e:
                            logger.warning(f"Failed to get loan audit trail for {loan_id}: {e}")
            
            return {
                "overview": overview,
                "timeline": timeline,
                "top_users": top_users,
                "top_actions": top_actions,
                "policy_decisions": policy_stats,
                "policy_decisions_list": [pd.to_dict() for pd in policy_decisions],
                "audit_logs": [self.audit_service.enrich_audit_log(db, log) for log in audit_logs],
                "total_logs": total_logs,
                "anomalies": anomalies,
                "entity_data": entity_data
            }
            
        except Exception as e:
            logger.error(f"Failed to process audit data: {e}", exc_info=True)
            raise
    
    def render_report(
        self,
        report_id: str,
        report_type: str,
        template: str,
        audit_data: Dict[str, Any],
        report_sections: Dict[str, Any],
        date_range: Dict[str, Optional[datetime]]
    ) -> Dict[str, Any]:
        """
        Render final report combining data and LLM output.
        
        Args:
            report_id: Unique report identifier
            report_type: Type of report
            template: Report template
            audit_data: Processed audit data
            report_sections: LLM-generated sections
            date_range: Date range for report
            
        Returns:
            Complete report dictionary
        """
        try:
            report = {
                "report_id": report_id,
                "report_type": report_type,
                "template": template,
                "generated_at": datetime.utcnow().isoformat(),
                "date_range": {
                    "start": date_range.get("start").isoformat() if date_range.get("start") else None,
                    "end": date_range.get("end").isoformat() if date_range.get("end") else None
                },
                "sections": {
                    "executive_summary": report_sections.get("executive_summary"),
                    "compliance_analysis": report_sections.get("compliance_analysis"),
                    "recommendations": report_sections.get("recommendations")
                },
                "data": {
                    "overview": audit_data.get("overview"),
                    "timeline": audit_data.get("timeline"),
                    "top_users": audit_data.get("top_users"),
                    "top_actions": audit_data.get("top_actions"),
                    "policy_decisions": audit_data.get("policy_decisions"),
                    "anomalies": audit_data.get("anomalies"),
                    "entity_data": audit_data.get("entity_data", {})
                },
                "detailed_trail": {
                    "audit_logs": audit_data.get("audit_logs", []),
                    "total_logs": audit_data.get("total_logs", 0)
                },
                "metadata": {
                    "total_sections": len(report_sections),
                    "data_points": audit_data.get("total_logs", 0),
                    "policy_decisions_count": len(audit_data.get("policy_decisions_list", []))
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to render report: {e}", exc_info=True)
            raise
