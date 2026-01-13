"""
Clause Analysis Chain for CreditNexus.

Advanced LLM-powered clause analysis, comparison, and violation detection
for audit reporting and compliance monitoring.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_client import get_chat_model

logger = logging.getLogger(__name__)


class ClauseAnalysisResult(BaseModel):
    """Result of clause analysis."""
    clause_text: str = Field(description="The clause text that was analyzed")
    interpretation: str = Field(description="Legal interpretation of the clause")
    compliance_status: str = Field(description="Compliance status: COMPLIANT, NON_COMPLIANT, or AT_RISK")
    risks: List[str] = Field(description="List of risks associated with this clause")
    recommendations: List[str] = Field(description="Recommendations for ensuring compliance")
    legal_implications: List[str] = Field(description="Legal implications and considerations")
    regulatory_references: List[str] = Field(description="Relevant regulations and standards referenced")
    severity_score: float = Field(description="Severity score from 0.0 (low) to 1.0 (critical)", ge=0.0, le=1.0)


class ClauseComparisonResult(BaseModel):
    """Result of clause comparison."""
    clause_1_text: str = Field(description="First clause text")
    clause_2_text: str = Field(description="Second clause text")
    similarity_score: float = Field(description="Similarity score from 0.0 (different) to 1.0 (identical)", ge=0.0, le=1.0)
    differences: List[Dict[str, Any]] = Field(description="List of differences between clauses")
    compliance_impact: str = Field(description="Impact on compliance status")
    risk_changes: List[str] = Field(description="Changes in risk profile")
    recommendations: List[str] = Field(description="Recommendations based on comparison")


class ViolationDetectionResult(BaseModel):
    """Result of violation detection."""
    clause_text: str = Field(description="The clause text analyzed for violations")
    violations: List[Dict[str, Any]] = Field(description="List of detected violations with details")
    violation_count: int = Field(description="Total number of violations detected", ge=0)
    severity: str = Field(description="Overall severity: LOW, MEDIUM, HIGH, or CRITICAL")
    affected_regulations: List[str] = Field(description="Regulations affected by violations")
    remediation_actions: List[str] = Field(description="Actions required to remediate violations")


class ClauseAnalysisChain:
    """LangChain chain for advanced clause analysis, comparison, and violation detection."""
    
    def __init__(self, temperature: float = 0.2):
        """
        Initialize clause analysis chain.
        
        Args:
            temperature: LLM temperature (default: 0.2 for consistency in legal analysis)
        """
        self.llm = get_chat_model(temperature=temperature)
        self.temperature = temperature
    
    def analyze_clause(
        self,
        clause_text: str,
        context: Optional[Dict[str, Any]] = None,
        policy_rules: Optional[List[str]] = None
    ) -> ClauseAnalysisResult:
        """
        Analyze a single clause with comprehensive legal and compliance insights.
        
        Args:
            clause_text: The clause text to analyze
            context: Optional context (audit logs, policy decisions, related entities)
            policy_rules: Optional list of policy rules to check against
            
        Returns:
            ClauseAnalysisResult Pydantic model with comprehensive analysis
            
        Raises:
            Exception: If LLM chain execution fails
        """
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert Legal and Compliance Analyst specializing in credit agreement clauses.

Analyze clauses with focus on:
1. Legal interpretation and meaning
2. Compliance status against financial regulations (MiCA, Basel III, FATF)
3. Risk identification and assessment
4. Regulatory references and standards
5. Actionable recommendations

Provide detailed, professional analysis suitable for audit reports."""),
                ("user", """Analyze the following clause:

Clause Text: {clause_text}

Context: {context}

Policy Rules: {policy_rules}

Please provide:
1. Interpretation: Detailed legal interpretation of the clause
2. Compliance Status: COMPLIANT, NON_COMPLIANT, or AT_RISK
3. Risks: List of specific risks associated with this clause
4. Recommendations: Actionable recommendations for compliance
5. Legal Implications: Legal considerations and implications
6. Regulatory References: Relevant regulations (MiCA, Basel III, FATF, etc.)
7. Severity Score: Numerical score from 0.0 (low risk) to 1.0 (critical risk)""")
            ])
            
            structured_llm = self.llm.with_structured_output(ClauseAnalysisResult)
            chain = prompt | structured_llm
            
            result = chain.invoke({
                "clause_text": clause_text,
                "context": str(context) if context else "No additional context provided",
                "policy_rules": "\n".join(policy_rules) if policy_rules else "No specific policy rules provided"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze clause: {e}", exc_info=True)
            raise
    
    def compare_clauses(
        self,
        clause_1_text: str,
        clause_2_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ClauseComparisonResult:
        """
        Compare two clauses for differences, similarities, and compliance implications.
        
        Useful for:
        - Document version comparison
        - Cross-deal clause analysis
        - Change impact assessment
        
        Args:
            clause_1_text: First clause text to compare
            clause_2_text: Second clause text to compare
            context: Optional context (document versions, dates, entities)
            
        Returns:
            ClauseComparisonResult Pydantic model with comparison analysis
            
        Raises:
            Exception: If LLM chain execution fails
        """
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert Legal Analyst comparing credit agreement clauses.

Compare clauses focusing on:
1. Similarity and differences
2. Compliance impact of changes
3. Risk profile changes
4. Recommendations for handling differences

Provide detailed comparison suitable for audit reports and compliance reviews."""),
                ("user", """Compare the following two clauses:

Clause 1: {clause_1_text}

Clause 2: {clause_2_text}

Context: {context}

Please provide:
1. Similarity Score: Numerical score from 0.0 (completely different) to 1.0 (identical)
2. Differences: List of specific differences with descriptions
3. Compliance Impact: How differences affect compliance status
4. Risk Changes: Changes in risk profile due to differences
5. Recommendations: Recommendations based on the comparison""")
            ])
            
            structured_llm = self.llm.with_structured_output(ClauseComparisonResult)
            chain = prompt | structured_llm
            
            result = chain.invoke({
                "clause_1_text": clause_1_text,
                "clause_2_text": clause_2_text,
                "context": str(context) if context else "No additional context provided"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to compare clauses: {e}", exc_info=True)
            raise
    
    def detect_violations(
        self,
        clause_text: str,
        policy_rules: List[str],
        regulations: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ViolationDetectionResult:
        """
        Detect compliance violations in a clause against policy rules and regulations.
        
        Args:
            clause_text: The clause text to analyze for violations
            policy_rules: List of policy rules to check against (from policy engine)
            regulations: Optional list of regulations (MiCA, Basel III, FATF, etc.)
            context: Optional context (audit history, related violations)
            
        Returns:
            ViolationDetectionResult Pydantic model with violation details
            
        Raises:
            Exception: If LLM chain execution fails
        """
        try:
            # Default regulations if not provided
            if regulations is None:
                regulations = [
                    "MiCA (Markets in Crypto-Assets Regulation)",
                    "Basel III Capital Requirements",
                    "FATF Anti-Money Laundering Standards",
                    "EU Sustainable Finance Disclosure Regulation"
                ]
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a Compliance Officer detecting violations in credit agreement clauses.

Detect violations focusing on:
1. Policy rule violations
2. Regulatory non-compliance
3. Severity assessment
4. Remediation requirements

Provide detailed violation analysis suitable for compliance reporting and remediation planning."""),
                ("user", """Detect violations in the following clause:

Clause Text: {clause_text}

Policy Rules to Check:
{policy_rules}

Regulations to Check:
{regulations}

Context: {context}

Please provide:
1. Violations: List of specific violations with details (rule/regulation, description, severity)
2. Violation Count: Total number of violations
3. Severity: Overall severity (LOW, MEDIUM, HIGH, CRITICAL)
4. Affected Regulations: List of regulations affected
5. Remediation Actions: Specific actions required to remediate each violation""")
            ])
            
            structured_llm = self.llm.with_structured_output(ViolationDetectionResult)
            chain = prompt | structured_llm
            
            result = chain.invoke({
                "clause_text": clause_text,
                "policy_rules": "\n".join([f"- {rule}" for rule in policy_rules]),
                "regulations": "\n".join([f"- {reg}" for reg in regulations]),
                "context": str(context) if context else "No additional context provided"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to detect violations: {e}", exc_info=True)
            raise
