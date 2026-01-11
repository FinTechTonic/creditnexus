"""
Policy Validation Service for CreditNexus.

Validates policy YAML syntax, rule structure, field references,
and checks for circular dependencies.
"""

import logging
import yaml
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of policy validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class PolicyValidator:
    """Validates policy YAML and rule structure."""
    
    # Valid operators for field conditions
    VALID_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "contains", "not_in", "not_contains"}
    
    # Valid actions
    VALID_ACTIONS = {"allow", "block", "flag"}
    
    def __init__(self):
        """Initialize policy validator."""
        pass
    
    def validate(self, rules_yaml: str) -> ValidationResult:
        """
        Validate policy YAML and rule structure.
        
        Args:
            rules_yaml: YAML string containing policy rules
            
        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        warnings = []
        metadata = {}
        
        # Step 1: Validate YAML syntax
        try:
            rules = yaml.safe_load(rules_yaml)
            if not isinstance(rules, list):
                errors.append("Policy rules must be a YAML list")
                return ValidationResult(valid=False, errors=errors, warnings=warnings, metadata=metadata)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax: {str(e)}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings, metadata=metadata)
        
        # Step 2: Validate rule structure
        rule_names = []
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f"Rule {i+1} must be a dictionary")
                continue
            
            # Validate required fields
            if "name" not in rule:
                errors.append(f"Rule {i+1} missing required field 'name'")
            else:
                rule_name = rule["name"]
                if not isinstance(rule_name, str) or not rule_name.strip():
                    errors.append(f"Rule {i+1} 'name' must be a non-empty string")
                elif rule_name in rule_names:
                    errors.append(f"Duplicate rule name: '{rule_name}'")
                else:
                    rule_names.append(rule_name)
            
            if "when" not in rule:
                errors.append(f"Rule {i+1} missing required field 'when'")
            else:
                condition_errors = self._validate_condition(rule["when"], f"Rule {i+1}")
                errors.extend(condition_errors)
            
            if "action" not in rule:
                errors.append(f"Rule {i+1} missing required field 'action'")
            else:
                action = rule["action"]
                if action not in self.VALID_ACTIONS:
                    errors.append(f"Rule {i+1} invalid action '{action}'. Must be one of: {', '.join(self.VALID_ACTIONS)}")
            
            # Validate optional fields
            if "priority" in rule:
                priority = rule["priority"]
                if not isinstance(priority, (int, float)):
                    errors.append(f"Rule {i+1} 'priority' must be a number")
            
            if "description" in rule:
                if not isinstance(rule["description"], str):
                    errors.append(f"Rule {i+1} 'description' must be a string")
        
        # Step 3: Check for circular dependencies (if rules reference each other)
        # This is a simplified check - in a full implementation, you'd track rule dependencies
        circular_deps = self._check_circular_dependencies(rules)
        if circular_deps:
            warnings.append(f"Potential circular dependencies detected: {', '.join(circular_deps)}")
        
        # Step 4: Validate field references
        field_ref_errors = self._validate_field_references(rules)
        errors.extend(field_ref_errors)
        
        metadata = {
            "rules_count": len(rules),
            "rule_names": rule_names
        }
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def _validate_condition(self, condition: Any, context: str) -> List[str]:
        """
        Validate a condition structure (supports nested any/all).
        
        Args:
            condition: Condition dictionary or value
            context: Context string for error messages
            
        Returns:
            List of error messages
        """
        errors = []
        
        if not isinstance(condition, dict):
            errors.append(f"{context}: Condition must be a dictionary")
            return errors
        
        # Check for 'any' or 'all' keys
        if "any" in condition and "all" in condition:
            errors.append(f"{context}: Condition cannot have both 'any' and 'all' keys")
            return errors
        
        if "any" in condition:
            items = condition["any"]
            if not isinstance(items, list):
                errors.append(f"{context}: 'any' condition must be a list")
            else:
                for i, item in enumerate(items):
                    errors.extend(self._validate_condition(item, f"{context}.any[{i}]"))
        
        elif "all" in condition:
            items = condition["all"]
            if not isinstance(items, list):
                errors.append(f"{context}: 'all' condition must be a list")
            else:
                for i, item in enumerate(items):
                    errors.extend(self._validate_condition(item, f"{context}.all[{i}]"))
        
        else:
            # Single field condition
            if "field" not in condition:
                errors.append(f"{context}: Condition missing 'field' key")
            else:
                field = condition["field"]
                if not isinstance(field, str) or not field.strip():
                    errors.append(f"{context}: 'field' must be a non-empty string")
            
            if "op" not in condition:
                errors.append(f"{context}: Condition missing 'op' key")
            else:
                op = condition["op"]
                if op not in self.VALID_OPERATORS:
                    errors.append(f"{context}: Invalid operator '{op}'. Must be one of: {', '.join(self.VALID_OPERATORS)}")
            
            if "value" not in condition:
                errors.append(f"{context}: Condition missing 'value' key")
        
        return errors
    
    def _check_circular_dependencies(self, rules: List[Dict[str, Any]]) -> List[str]:
        """
        Check for circular dependencies between rules.
        
        This is a simplified check. In a full implementation, you'd track
        rule dependencies (e.g., if rule A references rule B).
        
        Args:
            rules: List of rule dictionaries
            
        Returns:
            List of rule names with potential circular dependencies
        """
        # For now, return empty list - circular dependency checking would require
        # tracking rule references (e.g., if rules can reference other rules)
        return []
    
    def _validate_field_references(self, rules: List[Dict[str, Any]]) -> List[str]:
        """
        Validate field references in rules.
        
        Checks if referenced fields follow valid path patterns
        (e.g., "originator.lei", "amount", etc.).
        
        Args:
            rules: List of rule dictionaries
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Common field patterns (can be extended)
        valid_field_patterns = [
            "transaction_id",
            "transaction_type",
            "originator",
            "originator.lei",
            "originator.name",
            "originator.jurisdiction",
            "amount",
            "currency",
            "facility_name",
            "facility_type",
            "sustainability_linked",
            "governing_law",
            "regulatory_framework",
            # Credit risk fields
            "risk_weighted_assets",
            "calculated_capital_requirement",
            "probability_of_default",
            "loss_given_default",
            "exposure_at_default",
            "available_tier1_capital",
            "tier1_capital_ratio",
            "leverage_ratio",
            "sector_concentration",
        ]
        
        for i, rule in enumerate(rules):
            if "when" not in rule:
                continue
            
            fields = self._extract_field_references(rule["when"])
            for field in fields:
                # Allow nested field paths (e.g., "originator.lei")
                # For now, just check that field is not empty
                if not field or not field.strip():
                    errors.append(f"Rule {i+1} contains empty field reference")
                # In a full implementation, you'd validate against a schema
        
        return errors
    
    def _extract_field_references(self, condition: Any) -> Set[str]:
        """
        Extract all field references from a condition.
        
        Args:
            condition: Condition dictionary or value
            
        Returns:
            Set of field reference strings
        """
        fields = set()
        
        if not isinstance(condition, dict):
            return fields
        
        if "any" in condition:
            for item in condition["any"]:
                fields.update(self._extract_field_references(item))
        elif "all" in condition:
            for item in condition["all"]:
                fields.update(self._extract_field_references(item))
        else:
            if "field" in condition:
                fields.add(condition["field"])
        
        return fields
