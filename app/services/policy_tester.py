"""
Policy Testing Service for CreditNexus.

Tests policies against sample transactions and generates test results.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single policy test."""
    test_name: str
    passed: bool
    expected_decision: str
    actual_decision: str
    matched_rules: List[str]
    trace: List[Dict[str, Any]]
    error: Optional[str] = None


@dataclass
class BatchTestResult:
    """Result of batch policy testing."""
    total_tests: int
    passed: int
    failed: int
    results: List[TestResult]
    summary: Dict[str, Any]


class PolicyTester:
    """Tests policies against sample transactions."""
    
    def __init__(self, policy_engine_factory=None):
        """
        Initialize policy tester.
        
        Args:
            policy_engine_factory: Factory function to create policy engine instances
        """
        self.policy_engine_factory = policy_engine_factory
    
    def test_policy(
        self,
        rules_yaml: str,
        test_transactions: List[Dict[str, Any]],
        policy_engine=None
    ) -> BatchTestResult:
        """
        Test policy against sample transactions.
        
        Args:
            rules_yaml: Policy rules YAML
            test_transactions: List of test transaction dictionaries with 'transaction' and 'expected_decision'
            policy_engine: Optional policy engine instance (will create if not provided)
            
        Returns:
            BatchTestResult with test results
        """
        if policy_engine is None:
            if self.policy_engine_factory:
                policy_engine = self.policy_engine_factory()
            else:
                from app.services.policy_engine_factory import create_policy_engine
                policy_engine = create_policy_engine(vendor="default")
        
        # Load rules into engine
        policy_engine.load_rules(rules_yaml)
        
        results = []
        passed = 0
        failed = 0
        
        for i, test_case in enumerate(test_transactions):
            test_name = test_case.get("test_name", f"Test {i+1}")
            transaction = test_case.get("transaction", {})
            expected_decision = test_case.get("expected_decision", "ALLOW").upper()
            
            try:
                # Evaluate transaction
                result = policy_engine.evaluate(transaction)
                
                actual_decision = result.get("decision", "ALLOW").upper()
                matched_rules = result.get("matched_rules", [])
                trace = result.get("trace", [])
                
                # Check if decision matches expected
                test_passed = actual_decision == expected_decision
                
                if test_passed:
                    passed += 1
                else:
                    failed += 1
                
                test_result = TestResult(
                    test_name=test_name,
                    passed=test_passed,
                    expected_decision=expected_decision,
                    actual_decision=actual_decision,
                    matched_rules=matched_rules,
                    trace=trace
                )
                results.append(test_result)
            
            except Exception as e:
                failed += 1
                logger.error(f"Error testing transaction {i+1}: {e}", exc_info=True)
                test_result = TestResult(
                    test_name=test_name,
                    passed=False,
                    expected_decision=expected_decision,
                    actual_decision="ERROR",
                    matched_rules=[],
                    trace=[],
                    error=str(e)
                )
                results.append(test_result)
        
        summary = {
            "pass_rate": (passed / len(test_transactions) * 100) if test_transactions else 0.0,
            "total_rules_matched": sum(len(r.matched_rules) for r in results),
            "average_rules_per_test": sum(len(r.matched_rules) for r in results) / len(test_transactions) if test_transactions else 0.0
        }
        
        return BatchTestResult(
            total_tests=len(test_transactions),
            passed=passed,
            failed=failed,
            results=results,
            summary=summary
        )
    
    def create_test_transaction(
        self,
        transaction_type: str = "facility_creation",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a test transaction with default values.
        
        Args:
            transaction_type: Type of transaction
            **kwargs: Additional transaction fields
            
        Returns:
            Test transaction dictionary
        """
        default_transaction = {
            "transaction_id": kwargs.get("transaction_id", "TEST_001"),
            "transaction_type": transaction_type,
            "timestamp": "2024-01-01T00:00:00Z",
            "originator": {
                "id": kwargs.get("originator_id", "TEST_ORIGINATOR"),
                "name": kwargs.get("originator_name", "Test Originator"),
                "lei": kwargs.get("originator_lei", "TEST1234567890123456"),
                "jurisdiction": kwargs.get("jurisdiction", "US"),
                "kyc_status": kwargs.get("kyc_status", True)
            },
            "amount": kwargs.get("amount", 1000000.0),
            "currency": kwargs.get("currency", "USD"),
            "facility_type": kwargs.get("facility_type", "SyndicatedLoan"),
            "sustainability_linked": kwargs.get("sustainability_linked", False),
            "governing_law": kwargs.get("governing_law", "NY"),
            "regulatory_framework": kwargs.get("regulatory_framework", ["US_Regulations", "FATF"]),
        }
        
        # Merge with kwargs
        default_transaction.update(kwargs)
        
        return default_transaction
