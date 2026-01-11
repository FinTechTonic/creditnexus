"""Permission constants and role-based permission mappings for CreditNexus."""

from typing import List, Dict, Set
from app.db.models import User, UserRole


# ============================================================================
# Permission Constants
# ============================================================================

# Document Permissions
PERMISSION_DOCUMENT_CREATE = "DOCUMENT_CREATE"
PERMISSION_DOCUMENT_EDIT = "DOCUMENT_EDIT"
PERMISSION_DOCUMENT_DELETE = "DOCUMENT_DELETE"
PERMISSION_DOCUMENT_VIEW = "DOCUMENT_VIEW"
PERMISSION_DOCUMENT_REVIEW = "DOCUMENT_REVIEW"
PERMISSION_DOCUMENT_APPROVE = "DOCUMENT_APPROVE"
PERMISSION_DOCUMENT_EXPORT = "DOCUMENT_EXPORT"
PERMISSION_DOCUMENT_EXTRACT = "DOCUMENT_EXTRACT"

# Deal Permissions
PERMISSION_DEAL_CREATE = "DEAL_CREATE"
PERMISSION_DEAL_EDIT = "DEAL_EDIT"
PERMISSION_DEAL_DELETE = "DEAL_DELETE"
PERMISSION_DEAL_VIEW = "DEAL_VIEW"
PERMISSION_DEAL_VIEW_OWN = "DEAL_VIEW_OWN"
PERMISSION_DEAL_APPROVE = "DEAL_APPROVE"
PERMISSION_DEAL_REJECT = "DEAL_REJECT"
PERMISSION_DEAL_CLOSE = "DEAL_CLOSE"

# Trade Permissions
PERMISSION_TRADE_CREATE = "TRADE_CREATE"
PERMISSION_TRADE_EDIT = "TRADE_EDIT"
PERMISSION_TRADE_DELETE = "TRADE_DELETE"
PERMISSION_TRADE_VIEW = "TRADE_VIEW"
PERMISSION_TRADE_EXECUTE = "TRADE_EXECUTE"
PERMISSION_TRADE_CANCEL = "TRADE_CANCEL"

# Application Permissions
PERMISSION_APPLICATION_CREATE = "APPLICATION_CREATE"
PERMISSION_APPLICATION_EDIT = "APPLICATION_EDIT"
PERMISSION_APPLICATION_DELETE = "APPLICATION_DELETE"
PERMISSION_APPLICATION_VIEW = "APPLICATION_VIEW"
PERMISSION_APPLICATION_VIEW_OWN = "APPLICATION_VIEW_OWN"
PERMISSION_APPLICATION_SUBMIT = "APPLICATION_SUBMIT"
PERMISSION_APPLICATION_APPROVE = "APPLICATION_APPROVE"
PERMISSION_APPLICATION_REJECT = "APPLICATION_REJECT"

# Inquiry Permissions
PERMISSION_INQUIRY_CREATE = "INQUIRY_CREATE"
PERMISSION_INQUIRY_EDIT = "INQUIRY_EDIT"
PERMISSION_INQUIRY_VIEW = "INQUIRY_VIEW"
PERMISSION_INQUIRY_VIEW_OWN = "INQUIRY_VIEW_OWN"
PERMISSION_INQUIRY_RESPOND = "INQUIRY_RESPOND"
PERMISSION_INQUIRY_CLOSE = "INQUIRY_CLOSE"

# Template Permissions
PERMISSION_TEMPLATE_CREATE = "TEMPLATE_CREATE"
PERMISSION_TEMPLATE_EDIT = "TEMPLATE_EDIT"
PERMISSION_TEMPLATE_DELETE = "TEMPLATE_DELETE"
PERMISSION_TEMPLATE_VIEW = "TEMPLATE_VIEW"
PERMISSION_TEMPLATE_GENERATE = "TEMPLATE_GENERATE"

# Payment Permissions
PERMISSION_PAYMENT_CREATE = "PAYMENT_CREATE"
PERMISSION_PAYMENT_EDIT = "PAYMENT_EDIT"
PERMISSION_PAYMENT_DELETE = "PAYMENT_DELETE"
PERMISSION_PAYMENT_VIEW = "PAYMENT_VIEW"
PERMISSION_PAYMENT_PROCESS = "PAYMENT_PROCESS"

# Financial Permissions
PERMISSION_FINANCIAL_VIEW = "FINANCIAL_VIEW"
PERMISSION_FINANCIAL_EDIT = "FINANCIAL_EDIT"
PERMISSION_FINANCIAL_EXPORT = "FINANCIAL_EXPORT"
PERMISSION_FINANCIAL_ANALYZE = "FINANCIAL_ANALYZE"

# Audit Permissions
PERMISSION_AUDIT_VIEW = "AUDIT_VIEW"
PERMISSION_AUDIT_EXPORT = "AUDIT_EXPORT"
PERMISSION_AUDIT_CREATE = "AUDIT_CREATE"

# User Permissions
PERMISSION_USER_VIEW = "USER_VIEW"
PERMISSION_USER_EDIT = "USER_EDIT"
PERMISSION_USER_DELETE = "USER_DELETE"
PERMISSION_USER_CREATE = "USER_CREATE"
PERMISSION_USER_MANAGE_ROLES = "USER_MANAGE_ROLES"

# Policy Permissions
PERMISSION_POLICY_VIEW = "POLICY_VIEW"
PERMISSION_POLICY_EDIT = "POLICY_EDIT"
PERMISSION_POLICY_CREATE = "POLICY_CREATE"
PERMISSION_POLICY_DELETE = "POLICY_DELETE"
PERMISSION_POLICY_APPROVE = "POLICY_APPROVE"
PERMISSION_POLICY_REJECT = "POLICY_REJECT"
PERMISSION_POLICY_VIEW_PENDING = "POLICY_VIEW_PENDING"
PERMISSION_POLICY_TEST = "POLICY_TEST"

# Satellite Verification Permissions
PERMISSION_SATELLITE_VIEW = "SATELLITE_VIEW"
PERMISSION_SATELLITE_VERIFY = "SATELLITE_VERIFY"
PERMISSION_SATELLITE_EXPORT = "SATELLITE_EXPORT"

# Export Permissions
PERMISSION_EXPORT_DATA = "EXPORT_DATA"
PERMISSION_EXPORT_REPORTS = "EXPORT_REPORTS"


# ============================================================================
# Permission Categories
# ============================================================================

PERMISSION_CATEGORIES = {
    "document": [
        PERMISSION_DOCUMENT_CREATE,
        PERMISSION_DOCUMENT_EDIT,
        PERMISSION_DOCUMENT_DELETE,
        PERMISSION_DOCUMENT_VIEW,
        PERMISSION_DOCUMENT_REVIEW,
        PERMISSION_DOCUMENT_APPROVE,
        PERMISSION_DOCUMENT_EXPORT,
        PERMISSION_DOCUMENT_EXTRACT,
    ],
    "deal": [
        PERMISSION_DEAL_CREATE,
        PERMISSION_DEAL_EDIT,
        PERMISSION_DEAL_DELETE,
        PERMISSION_DEAL_VIEW,
        PERMISSION_DEAL_VIEW_OWN,
        PERMISSION_DEAL_APPROVE,
        PERMISSION_DEAL_REJECT,
        PERMISSION_DEAL_CLOSE,
    ],
    "trade": [
        PERMISSION_TRADE_CREATE,
        PERMISSION_TRADE_EDIT,
        PERMISSION_TRADE_DELETE,
        PERMISSION_TRADE_VIEW,
        PERMISSION_TRADE_EXECUTE,
        PERMISSION_TRADE_CANCEL,
    ],
    "application": [
        PERMISSION_APPLICATION_CREATE,
        PERMISSION_APPLICATION_EDIT,
        PERMISSION_APPLICATION_DELETE,
        PERMISSION_APPLICATION_VIEW,
        PERMISSION_APPLICATION_VIEW_OWN,
        PERMISSION_APPLICATION_SUBMIT,
        PERMISSION_APPLICATION_APPROVE,
        PERMISSION_APPLICATION_REJECT,
    ],
    "inquiry": [
        PERMISSION_INQUIRY_CREATE,
        PERMISSION_INQUIRY_EDIT,
        PERMISSION_INQUIRY_VIEW,
        PERMISSION_INQUIRY_VIEW_OWN,
        PERMISSION_INQUIRY_RESPOND,
        PERMISSION_INQUIRY_CLOSE,
    ],
    "template": [
        PERMISSION_TEMPLATE_CREATE,
        PERMISSION_TEMPLATE_EDIT,
        PERMISSION_TEMPLATE_DELETE,
        PERMISSION_TEMPLATE_VIEW,
        PERMISSION_TEMPLATE_GENERATE,
    ],
    "payment": [
        PERMISSION_PAYMENT_CREATE,
        PERMISSION_PAYMENT_EDIT,
        PERMISSION_PAYMENT_DELETE,
        PERMISSION_PAYMENT_VIEW,
        PERMISSION_PAYMENT_PROCESS,
    ],
    "financial": [
        PERMISSION_FINANCIAL_VIEW,
        PERMISSION_FINANCIAL_EDIT,
        PERMISSION_FINANCIAL_EXPORT,
        PERMISSION_FINANCIAL_ANALYZE,
    ],
    "audit": [
        PERMISSION_AUDIT_VIEW,
        PERMISSION_AUDIT_EXPORT,
        PERMISSION_AUDIT_CREATE,
    ],
    "user": [
        PERMISSION_USER_VIEW,
        PERMISSION_USER_EDIT,
        PERMISSION_USER_DELETE,
        PERMISSION_USER_CREATE,
        PERMISSION_USER_MANAGE_ROLES,
    ],
    "policy": [
        PERMISSION_POLICY_VIEW,
        PERMISSION_POLICY_EDIT,
        PERMISSION_POLICY_CREATE,
        PERMISSION_POLICY_DELETE,
        PERMISSION_POLICY_APPROVE,
        PERMISSION_POLICY_REJECT,
        PERMISSION_POLICY_VIEW_PENDING,
        PERMISSION_POLICY_TEST,
    ],
    "satellite": [
        PERMISSION_SATELLITE_VIEW,
        PERMISSION_SATELLITE_VERIFY,
        PERMISSION_SATELLITE_EXPORT,
    ],
    "export": [
        PERMISSION_EXPORT_DATA,
        PERMISSION_EXPORT_REPORTS,
    ],
}


# ============================================================================
# Role Permission Mappings
# ============================================================================

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    # Auditor: Full oversight, read-only access to all
    UserRole.AUDITOR.value: [
        # View permissions
        PERMISSION_DOCUMENT_VIEW,
        PERMISSION_DEAL_VIEW,
        PERMISSION_TRADE_VIEW,
        PERMISSION_APPLICATION_VIEW,
        PERMISSION_INQUIRY_VIEW,
        PERMISSION_TEMPLATE_VIEW,
        PERMISSION_PAYMENT_VIEW,
        PERMISSION_FINANCIAL_VIEW,
        PERMISSION_USER_VIEW,
        PERMISSION_POLICY_VIEW,
        PERMISSION_SATELLITE_VIEW,
        # Audit permissions
        PERMISSION_AUDIT_VIEW,
        PERMISSION_AUDIT_EXPORT,
        PERMISSION_AUDIT_CREATE,
        # Export permissions
        PERMISSION_DOCUMENT_EXPORT,
        PERMISSION_EXPORT_DATA,
        PERMISSION_EXPORT_REPORTS,
        PERMISSION_SATELLITE_EXPORT,
    ],
    
    # Banker: Write permissions for deals, documents, trades
    UserRole.BANKER.value: [
        # Document permissions
        PERMISSION_DOCUMENT_CREATE,
        PERMISSION_DOCUMENT_EDIT,
        PERMISSION_DOCUMENT_VIEW,
        PERMISSION_DOCUMENT_EXTRACT,
        PERMISSION_DOCUMENT_EXPORT,
        # Deal permissions
        PERMISSION_DEAL_CREATE,
        PERMISSION_DEAL_EDIT,
        PERMISSION_DEAL_VIEW,
        PERMISSION_DEAL_APPROVE,
        PERMISSION_DEAL_REJECT,
        PERMISSION_DEAL_CLOSE,
        # Trade permissions
        PERMISSION_TRADE_CREATE,
        PERMISSION_TRADE_EDIT,
        PERMISSION_TRADE_VIEW,
        PERMISSION_TRADE_EXECUTE,
        PERMISSION_TRADE_CANCEL,
        # Application permissions
        PERMISSION_APPLICATION_VIEW,
        PERMISSION_APPLICATION_APPROVE,
        PERMISSION_APPLICATION_REJECT,
        # Template permissions
        PERMISSION_TEMPLATE_VIEW,
        PERMISSION_TEMPLATE_GENERATE,
        # View permissions
        PERMISSION_INQUIRY_VIEW,
        PERMISSION_PAYMENT_VIEW,
        PERMISSION_FINANCIAL_VIEW,
        PERMISSION_POLICY_VIEW,
        PERMISSION_SATELLITE_VIEW,
    ],
    
    # Law Officer: Write/edit for legal documents
    UserRole.LAW_OFFICER.value: [
        # Document permissions
        PERMISSION_DOCUMENT_CREATE,
        PERMISSION_DOCUMENT_EDIT,
        PERMISSION_DOCUMENT_VIEW,
        PERMISSION_DOCUMENT_REVIEW,
        PERMISSION_DOCUMENT_EXPORT,
        # Template permissions
        PERMISSION_TEMPLATE_CREATE,
        PERMISSION_TEMPLATE_EDIT,
        PERMISSION_TEMPLATE_VIEW,
        PERMISSION_TEMPLATE_GENERATE,
        # Deal permissions
        PERMISSION_DEAL_VIEW,
        PERMISSION_DEAL_EDIT,
        # View permissions
        PERMISSION_APPLICATION_VIEW,
        PERMISSION_INQUIRY_VIEW,
        PERMISSION_POLICY_VIEW,
    ],
    
    # Accountant: Write/edit for financial data
    UserRole.ACCOUNTANT.value: [
        # Payment permissions
        PERMISSION_PAYMENT_CREATE,
        PERMISSION_PAYMENT_EDIT,
        PERMISSION_PAYMENT_VIEW,
        PERMISSION_PAYMENT_PROCESS,
        # Financial permissions
        PERMISSION_FINANCIAL_VIEW,
        PERMISSION_FINANCIAL_EDIT,
        PERMISSION_FINANCIAL_EXPORT,
        PERMISSION_FINANCIAL_ANALYZE,
        # Document permissions
        PERMISSION_DOCUMENT_VIEW,
        PERMISSION_DOCUMENT_EXPORT,
        # Deal permissions
        PERMISSION_DEAL_VIEW,
        # View permissions
        PERMISSION_APPLICATION_VIEW,
        PERMISSION_INQUIRY_VIEW,
        PERMISSION_TEMPLATE_VIEW,
    ],
    
    # Applicant: Apply and track applications
    UserRole.APPLICANT.value: [
        # Application permissions
        PERMISSION_APPLICATION_CREATE,
        PERMISSION_APPLICATION_EDIT,
        PERMISSION_APPLICATION_VIEW_OWN,
        PERMISSION_APPLICATION_SUBMIT,
        # Deal permissions
        PERMISSION_DEAL_VIEW_OWN,
        # Inquiry permissions
        PERMISSION_INQUIRY_CREATE,
        PERMISSION_INQUIRY_VIEW_OWN,
        # View permissions
        PERMISSION_DOCUMENT_VIEW,  # Only own documents
        PERMISSION_TEMPLATE_VIEW,
    ],
    
    # Legacy roles for backward compatibility
    UserRole.VIEWER.value: [
        PERMISSION_DOCUMENT_VIEW,
        PERMISSION_DEAL_VIEW,
        PERMISSION_TRADE_VIEW,
        PERMISSION_APPLICATION_VIEW,
        PERMISSION_TEMPLATE_VIEW,
    ],
    
    UserRole.ANALYST.value: [
        PERMISSION_DOCUMENT_CREATE,
        PERMISSION_DOCUMENT_EDIT,
        PERMISSION_DOCUMENT_VIEW,
        PERMISSION_DOCUMENT_EXTRACT,
        PERMISSION_DEAL_VIEW,
        PERMISSION_TRADE_VIEW,
        PERMISSION_APPLICATION_VIEW,
        PERMISSION_TEMPLATE_VIEW,
        PERMISSION_TEMPLATE_GENERATE,
        PERMISSION_FINANCIAL_VIEW,
        PERMISSION_SATELLITE_VIEW,
    ],
    
    UserRole.REVIEWER.value: [
        PERMISSION_DOCUMENT_VIEW,
        PERMISSION_DOCUMENT_REVIEW,
        PERMISSION_DOCUMENT_APPROVE,
        PERMISSION_DEAL_VIEW,
        PERMISSION_DEAL_APPROVE,
        PERMISSION_APPLICATION_VIEW,
        PERMISSION_APPLICATION_APPROVE,
        PERMISSION_TEMPLATE_VIEW,
        PERMISSION_POLICY_VIEW,
    ],
    
    UserRole.ADMIN.value: [
        # All permissions
        *[perm for perms in PERMISSION_CATEGORIES.values() for perm in perms],
    ],
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_role_permissions(role: str) -> List[str]:
    """Get list of permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(user: User, permission: str) -> bool:
    """Check if user has a specific permission."""
    # Check explicit user permissions first (overrides role permissions)
    if user.permissions:
        if isinstance(user.permissions, list):
            if permission in user.permissions:
                return True
        elif isinstance(user.permissions, dict):
            if user.permissions.get(permission, False):
                return True
    
    # Check role permissions
    role_perms = get_role_permissions(user.role)
    if permission in role_perms:
        return True
    
    return False


def has_permissions(user: User, required_permissions: List[str]) -> bool:
    """Check if user has all required permissions."""
    return all(has_permission(user, perm) for perm in required_permissions)


def has_any_permission(user: User, permissions: List[str]) -> bool:
    """Check if user has any of the specified permissions."""
    return any(has_permission(user, perm) for perm in permissions)


def get_user_permissions(user: User) -> Set[str]:
    """Get all permissions for a user (role + explicit)."""
    permissions = set(get_role_permissions(user.role))
    
    # Add explicit user permissions
    if user.permissions:
        if isinstance(user.permissions, list):
            permissions.update(user.permissions)
        elif isinstance(user.permissions, dict):
            # If permissions is a dict, add keys where value is True
            permissions.update(
                perm for perm, granted in user.permissions.items() if granted
            )
    
    return permissions
