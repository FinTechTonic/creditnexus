"""
Audit Report Chain for CreditNexus.

LLM-powered report generation with structured outputs for audit reports.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_client import get_chat_model

logger = logging.getLogger(__name__)


class ExecutiveSummary(BaseModel):
    """Executive summary for audit report."""
    overview: str = Field(description="High-level overview of audit activities")
    key_findings: List[str] = Field(description="Key findings from the audit")
    risk_assessment: str = Field(description="Overall risk assessment")
    recommendations: List[str] = Field(description="Top recommendations")


class ComplianceAnalysis(BaseModel):
    """Compliance analysis for audit report."""
    compliance_status: str = Field(description="Overall compliance status")
    violations: List[Dict[str, Any]] = Field(description="List of compliance violations")
    policy_decisions_summary: Dict[str, int] = Field(description="Summary of policy decisions")
    critical_issues: List[str] = Field(description="Critical compliance issues")


class Recommendations(BaseModel):
    """Recommendations for audit report."""
    immediate_actions: List[str] = Field(description="Immediate actions required")
    short_term_improvements: List[str] = Field(description="Short-term improvements")
    long_term_strategies: List[str] = Field(description="Long-term strategic recommendations")


class ClauseAnalysis(BaseModel):
    """Analysis of specific clauses."""
    clause_text: str = Field(description="The clause text being analyzed")
    interpretation: str = Field(description="Interpretation of the clause")
    compliance_status: str = Field(description="Compliance status for this clause")
    risks: List[str] = Field(description="Risks associated with this clause")
    recommendations: List[str] = Field(description="Recommendations for this clause")


class AuditReportChain:
    """LangChain chain for audit report generation."""
    
    def __init__(self, temperature: float = 0.3):
        """
        Initialize audit report chain.
        
        Args:
            temperature: LLM temperature (default: 0.3 for balanced creativity/consistency)
        """
        self.llm = get_chat_model(temperature=temperature)
        self.temperature = temperature
    
    def generate_executive_summary(
        self,
        audit_data: Dict[str, Any],
        date_range: Dict[str, str]
    ) -> ExecutiveSummary:
        """
        Generate executive summary from audit data.
        
        Args:
            audit_data: Dictionary containing audit statistics and data
            date_range: Dictionary with start and end dates
            
        Returns:
            ExecutiveSummary Pydantic model
        """
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert Audit Analyst. Generate a comprehensive executive summary for an audit report based on the provided audit data.

Your summary should:
1. Provide a high-level overview of audit activities
2. Identify key findings and patterns
3. Assess overall risk levels
4. Provide top-level recommendations

Be concise, professional, and data-driven."""),
                ("user", """Generate an executive summary for the following audit data:

Date Range: {start_date} to {end_date}

Audit Statistics:
- Total Audit Logs: {total_logs}
- Unique Users: {unique_users}
- Top Actions: {top_actions}
- Policy Decisions: {policy_decisions}

Activity Timeline: {timeline}

Please provide:
1. Overview: High-level summary of audit activities
2. Key Findings: List of 3-5 key findings
3. Risk Assessment: Overall risk assessment
4. Recommendations: Top 3-5 recommendations""")
            ])
            
            structured_llm = self.llm.with_structured_output(ExecutiveSummary)
            chain = prompt | structured_llm
            
            result = chain.invoke({
                "start_date": date_range.get("start", "N/A"),
                "end_date": date_range.get("end", "N/A"),
                "total_logs": audit_data.get("total_logs", 0),
                "unique_users": audit_data.get("unique_users", 0),
                "top_actions": str(audit_data.get("top_actions", [])),
                "policy_decisions": str(audit_data.get("policy_decisions", {})),
                "timeline": str(audit_data.get("timeline", []))
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}", exc_info=True)
            raise
    
    def analyze_compliance(
        self,
        policy_decisions: List[Dict[str, Any]],
        audit_logs: List[Dict[str, Any]]
    ) -> ComplianceAnalysis:
        """
        Analyze compliance based on policy decisions and audit logs.
        
        Args:
            policy_decisions: List of policy decision dictionaries
            audit_logs: List of audit log dictionaries
            
        Returns:
            ComplianceAnalysis Pydantic model
        """
        try:
            # Count policy decisions
            decision_counts = {"ALLOW": 0, "BLOCK": 0, "FLAG": 0}
            violations = []
            
            for decision in policy_decisions:
                decision_type = decision.get("decision", "ALLOW")
                decision_counts[decision_type] = decision_counts.get(decision_type, 0) + 1
                
                if decision_type in ["BLOCK", "FLAG"]:
                    violations.append({
                        "transaction_id": decision.get("transaction_id"),
                        "decision": decision_type,
                        "rule_applied": decision.get("rule_applied"),
                        "created_at": decision.get("created_at")
                    })
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a Compliance Analyst. Analyze policy decisions and audit logs to assess compliance status.

Identify:
1. Overall compliance status
2. Specific violations and their severity
3. Critical issues requiring immediate attention
4. Patterns in policy decisions"""),
                ("user", """Analyze compliance for the following data:

Policy Decisions Summary:
- ALLOW: {allow_count}
- BLOCK: {block_count}
- FLAG: {flag_count}

Violations: {violations}

Please provide:
1. Compliance Status: Overall status (COMPLIANT, NON_COMPLIANT, AT_RISK)
2. Violations: List of violations with details
3. Policy Decisions Summary: Summary of decision types
4. Critical Issues: List of critical issues""")
            ])
            
            structured_llm = self.llm.with_structured_output(ComplianceAnalysis)
            chain = prompt | structured_llm
            
            result = chain.invoke({
                "allow_count": decision_counts.get("ALLOW", 0),
                "block_count": decision_counts.get("BLOCK", 0),
                "flag_count": decision_counts.get("FLAG", 0),
                "violations": str(violations[:20])  # Limit to first 20 for context
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze compliance: {e}", exc_info=True)
            raise
    
    def generate_recommendations(
        self,
        audit_data: Dict[str, Any],
        compliance_analysis: ComplianceAnalysis,
        anomalies: List[Dict[str, Any]]
    ) -> Recommendations:
        """
        Generate recommendations based on audit data and analysis.
        
        Args:
            audit_data: Dictionary containing audit statistics
            compliance_analysis: ComplianceAnalysis results
            anomalies: List of detected anomalies
            
        Returns:
            Recommendations Pydantic model
        """
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an Audit Consultant. Generate actionable recommendations based on audit findings.

Categorize recommendations into:
1. Immediate Actions: Urgent issues requiring immediate attention
2. Short-term Improvements: Issues to address within 30-90 days
3. Long-term Strategies: Strategic improvements for 6+ months"""),
                ("user", """Generate recommendations based on:

Audit Statistics: {audit_stats}
Compliance Analysis: {compliance}
Anomalies Detected: {anomalies}

Please provide:
1. Immediate Actions: 3-5 urgent actions
2. Short-term Improvements: 5-7 improvements for next quarter
3. Long-term Strategies: 3-5 strategic recommendations""")
            ])
            
            structured_llm = self.llm.with_structured_output(Recommendations)
            chain = prompt | structured_llm
            
            result = chain.invoke({
                "audit_stats": str(audit_data),
                "compliance": compliance_analysis.model_dump_json(),
                "anomalies": str(anomalies)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}", exc_info=True)
            raise
    
    def analyze_clauses(
        self,
        clause_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ClauseAnalysis:
        """
        Analyze specific clauses in audit context.
        
        Args:
            clause_text: The clause text to analyze
            context: Optional context (audit logs, policy decisions, etc.)
            
        Returns:
            ClauseAnalysis Pydantic model
        """
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a Legal and Compliance Analyst. Analyze specific clauses from credit agreements or policy documents in the context of audit findings.

Provide:
1. Interpretation of the clause
2. Compliance status assessment
3. Risks associated with the clause
4. Recommendations for compliance"""),
                ("user", """Analyze the following clause:

Clause Text: {clause_text}

Context: {context}

Please provide:
1. Interpretation: Your interpretation of the clause
2. Compliance Status: COMPLIANT, NON_COMPLIANT, or AT_RISK
3. Risks: List of risks associated with this clause
4. Recommendations: Recommendations for ensuring compliance""")
            ])
            
            structured_llm = self.llm.with_structured_output(ClauseAnalysis)
            chain = prompt | structured_llm
            
            result = chain.invoke({
                "clause_text": clause_text,
                "context": str(context) if context else "No additional context provided"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze clause: {e}", exc_info=True)
            raise
