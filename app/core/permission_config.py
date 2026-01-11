"""Permission configuration for seeding permission definitions and role mappings."""

from typing import Dict, List, Tuple
from app.core.permissions import (
    PERMISSION_CATEGORIES,
    ROLE_PERMISSIONS,
    # Document permissions
    PERMISSION_DOCUMENT_CREATE,
    PERMISSION_DOCUMENT_EDIT,
    PERMISSION_DOCUMENT_DELETE,
    PERMISSION_DOCUMENT_VIEW,
    PERMISSION_DOCUMENT_REVIEW,
    PERMISSION_DOCUMENT_APPROVE,
    PERMISSION_DOCUMENT_EXPORT,
    PERMISSION_DOCUMENT_EXTRACT,
    # Deal permissions
    PERMISSION_DEAL_CREATE,
    PERMISSION_DEAL_EDIT,
    PERMISSION_DEAL_DELETE,
    PERMISSION_DEAL_VIEW,
    PERMISSION_DEAL_VIEW_OWN,
    PERMISSION_DEAL_APPROVE,
    PERMISSION_DEAL_REJECT,
    PERMISSION_DEAL_CLOSE,
    # Trade permissions
    PERMISSION_TRADE_CREATE,
    PERMISSION_TRADE_EDIT,
    PERMISSION_TRADE_DELETE,
    PERMISSION_TRADE_VIEW,
    PERMISSION_TRADE_EXECUTE,
    PERMISSION_TRADE_CANCEL,
    # Application permissions
    PERMISSION_APPLICATION_CREATE,
    PERMISSION_APPLICATION_EDIT,
    PERMISSION_APPLICATION_DELETE,
    PERMISSION_APPLICATION_VIEW,
    PERMISSION_APPLICATION_VIEW_OWN,
    PERMISSION_APPLICATION_SUBMIT,
    PERMISSION_APPLICATION_APPROVE,
    PERMISSION_APPLICATION_REJECT,
    # Inquiry permissions
    PERMISSION_INQUIRY_CREATE,
    PERMISSION_INQUIRY_EDIT,
    PERMISSION_INQUIRY_VIEW,
    PERMISSION_INQUIRY_VIEW_OWN,
    PERMISSION_INQUIRY_RESPOND,
    PERMISSION_INQUIRY_CLOSE,
    # Template permissions
    PERMISSION_TEMPLATE_CREATE,
    PERMISSION_TEMPLATE_EDIT,
    PERMISSION_TEMPLATE_DELETE,
    PERMISSION_TEMPLATE_VIEW,
    PERMISSION_TEMPLATE_GENERATE,
    # Payment permissions
    PERMISSION_PAYMENT_CREATE,
    PERMISSION_PAYMENT_EDIT,
    PERMISSION_PAYMENT_DELETE,
    PERMISSION_PAYMENT_VIEW,
    PERMISSION_PAYMENT_PROCESS,
    # Financial permissions
    PERMISSION_FINANCIAL_VIEW,
    PERMISSION_FINANCIAL_EDIT,
    PERMISSION_FINANCIAL_EXPORT,
    PERMISSION_FINANCIAL_ANALYZE,
    # Audit permissions
    PERMISSION_AUDIT_VIEW,
    PERMISSION_AUDIT_EXPORT,
    PERMISSION_AUDIT_CREATE,
    # User permissions
    PERMISSION_USER_VIEW,
    PERMISSION_USER_EDIT,
    PERMISSION_USER_DELETE,
    PERMISSION_USER_CREATE,
    PERMISSION_USER_MANAGE_ROLES,
    # Policy permissions
    PERMISSION_POLICY_VIEW,
    PERMISSION_POLICY_EDIT,
    PERMISSION_POLICY_CREATE,
    PERMISSION_POLICY_DELETE,
    PERMISSION_POLICY_APPROVE,
    PERMISSION_POLICY_TEST,
    # Satellite permissions
    PERMISSION_SATELLITE_VIEW,
    PERMISSION_SATELLITE_VERIFY,
    PERMISSION_SATELLITE_EXPORT,
    # Export permissions
    PERMISSION_EXPORT_DATA,
    PERMISSION_EXPORT_REPORTS,
)


# Permission definitions with descriptions
PERMISSION_DEFINITIONS: List[Tuple[str, str, str]] = [
    # Document permissions
    (PERMISSION_DOCUMENT_CREATE, "Create new documents", "document"),
    (PERMISSION_DOCUMENT_EDIT, "Edit existing documents", "document"),
    (PERMISSION_DOCUMENT_DELETE, "Delete documents", "document"),
    (PERMISSION_DOCUMENT_VIEW, "View documents", "document"),
    (PERMISSION_DOCUMENT_REVIEW, "Review documents for approval", "document"),
    (PERMISSION_DOCUMENT_APPROVE, "Approve documents", "document"),
    (PERMISSION_DOCUMENT_EXPORT, "Export documents", "document"),
    (PERMISSION_DOCUMENT_EXTRACT, "Extract data from documents", "document"),
    
    # Deal permissions
    (PERMISSION_DEAL_CREATE, "Create new deals", "deal"),
    (PERMISSION_DEAL_EDIT, "Edit existing deals", "deal"),
    (PERMISSION_DEAL_DELETE, "Delete deals", "deal"),
    (PERMISSION_DEAL_VIEW, "View all deals", "deal"),
    (PERMISSION_DEAL_VIEW_OWN, "View own deals only", "deal"),
    (PERMISSION_DEAL_APPROVE, "Approve deals", "deal"),
    (PERMISSION_DEAL_REJECT, "Reject deals", "deal"),
    (PERMISSION_DEAL_CLOSE, "Close deals", "deal"),
    
    # Trade permissions
    (PERMISSION_TRADE_CREATE, "Create new trades", "trade"),
    (PERMISSION_TRADE_EDIT, "Edit existing trades", "trade"),
    (PERMISSION_TRADE_DELETE, "Delete trades", "trade"),
    (PERMISSION_TRADE_VIEW, "View trades", "trade"),
    (PERMISSION_TRADE_EXECUTE, "Execute trades", "trade"),
    (PERMISSION_TRADE_CANCEL, "Cancel trades", "trade"),
    
    # Application permissions
    (PERMISSION_APPLICATION_CREATE, "Create new applications", "application"),
    (PERMISSION_APPLICATION_EDIT, "Edit existing applications", "application"),
    (PERMISSION_APPLICATION_DELETE, "Delete applications", "application"),
    (PERMISSION_APPLICATION_VIEW, "View all applications", "application"),
    (PERMISSION_APPLICATION_VIEW_OWN, "View own applications only", "application"),
    (PERMISSION_APPLICATION_SUBMIT, "Submit applications", "application"),
    (PERMISSION_APPLICATION_APPROVE, "Approve applications", "application"),
    (PERMISSION_APPLICATION_REJECT, "Reject applications", "application"),
    
    # Inquiry permissions
    (PERMISSION_INQUIRY_CREATE, "Create new inquiries", "inquiry"),
    (PERMISSION_INQUIRY_EDIT, "Edit existing inquiries", "inquiry"),
    (PERMISSION_INQUIRY_VIEW, "View all inquiries", "inquiry"),
    (PERMISSION_INQUIRY_VIEW_OWN, "View own inquiries only", "inquiry"),
    (PERMISSION_INQUIRY_RESPOND, "Respond to inquiries", "inquiry"),
    (PERMISSION_INQUIRY_CLOSE, "Close inquiries", "inquiry"),
    
    # Template permissions
    (PERMISSION_TEMPLATE_CREATE, "Create new templates", "template"),
    (PERMISSION_TEMPLATE_EDIT, "Edit existing templates", "template"),
    (PERMISSION_TEMPLATE_DELETE, "Delete templates", "template"),
    (PERMISSION_TEMPLATE_VIEW, "View templates", "template"),
    (PERMISSION_TEMPLATE_GENERATE, "Generate documents from templates", "template"),
    
    # Payment permissions
    (PERMISSION_PAYMENT_CREATE, "Create new payments", "payment"),
    (PERMISSION_PAYMENT_EDIT, "Edit existing payments", "payment"),
    (PERMISSION_PAYMENT_DELETE, "Delete payments", "payment"),
    (PERMISSION_PAYMENT_VIEW, "View payments", "payment"),
    (PERMISSION_PAYMENT_PROCESS, "Process payments", "payment"),
    
    # Financial permissions
    (PERMISSION_FINANCIAL_VIEW, "View financial data", "financial"),
    (PERMISSION_FINANCIAL_EDIT, "Edit financial data", "financial"),
    (PERMISSION_FINANCIAL_EXPORT, "Export financial data", "financial"),
    (PERMISSION_FINANCIAL_ANALYZE, "Analyze financial data", "financial"),
    
    # Audit permissions
    (PERMISSION_AUDIT_VIEW, "View audit logs", "audit"),
    (PERMISSION_AUDIT_EXPORT, "Export audit logs", "audit"),
    (PERMISSION_AUDIT_CREATE, "Create audit entries", "audit"),
    
    # User permissions
    (PERMISSION_USER_VIEW, "View users", "user"),
    (PERMISSION_USER_EDIT, "Edit users", "user"),
    (PERMISSION_USER_DELETE, "Delete users", "user"),
    (PERMISSION_USER_CREATE, "Create users", "user"),
    (PERMISSION_USER_MANAGE_ROLES, "Manage user roles", "user"),
    
    # Policy permissions
    (PERMISSION_POLICY_VIEW, "View policies", "policy"),
    (PERMISSION_POLICY_EDIT, "Edit policies", "policy"),
    (PERMISSION_POLICY_CREATE, "Create policies", "policy"),
    (PERMISSION_POLICY_DELETE, "Delete policies", "policy"),
    (PERMISSION_POLICY_APPROVE, "Approve policies", "policy"),
    (PERMISSION_POLICY_TEST, "Test policies", "policy"),
    
    # Satellite permissions
    (PERMISSION_SATELLITE_VIEW, "View satellite imagery", "satellite"),
    (PERMISSION_SATELLITE_VERIFY, "Verify satellite imagery", "satellite"),
    (PERMISSION_SATELLITE_EXPORT, "Export satellite imagery", "satellite"),
    
    # Export permissions
    (PERMISSION_EXPORT_DATA, "Export data", "export"),
    (PERMISSION_EXPORT_REPORTS, "Export reports", "export"),
]


def get_permission_definitions() -> List[Tuple[str, str, str]]:
    """Get all permission definitions for seeding."""
    return PERMISSION_DEFINITIONS


def get_role_permission_mappings() -> Dict[str, List[str]]:
    """Get role-permission mappings for seeding."""
    return ROLE_PERMISSIONS
