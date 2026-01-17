# DigiSign Native & Hybrid Implementation Plan

## Executive Summary

This document proposes a unified implementation for **DigiSign**, a hybrid signing service that transitions CreditNexus from an external dependency (DigiSigner) to a **completely vendored-in native signing infrastructure**. The solution combines a native HTML5 Canvas signature pad, backend PDF injection logic, role-based dashboard management, and immutable on-chain notarization (via the Base network).

**Key Objectives:**
1.  **Internalize Signature Services**: Eliminate external API dependencies by building native capture and injection logic.
2.  **Native PDF Signing**: Use `PyMuPDF` / `fitz` to overlay signature images onto documents at defined coordinates.
3.  **Role-Based Management**: Provide specific interfaces for Bankers (coordinators), Applicants (signers), and Auditors (verifiers).
4.  **Blockchain Proof of Execution**: Anchor native signature hashes to the `SecuritizationNotarization` smart contract.
5.  **Unified Portal**: Provide a native signer portal for both internal users and external parties.

**Status**: Proposed Implementation Plan
**Priority**: High
**Complexity**: High

---

## Current State Assessment

### 1. Existing Assets
*   **PDF Libraries**: `PyMuPDF` (fitz) and `pypdf` are already installed in the Python environment.
*   **Blockchain Infrastructure**: `SecuritizationNotarization.sol` is deployed and supports multi-party on-chain signing.
*   **User Roles**: Established roles (`banker`, `law_officer`, `applicant`, `auditor`) with permission mappings.
*   **AI/LLM**: LangChain models exist for extracting signers from credit agreements.

### 2. Gap Analysis (The "Complete Vendor-In" Requirements)
*   **Signature Capture**: No native frontend component for drawing signatures.
*   **PDF Injection**: No backend logic to burn signature images into PDF byte streams.
*   **Role-Specific Dashboards**: No centralized view for a user to see all documents awaiting their signature.
*   **Audit Trail**: No native generation of "Certificate of Completion" pages.

---

## Project 1: Native Signature Engine (Backend)

### Activity 1.1: Internal Signature Service
**File**: `app/services/internal_signature_service.py` (NEW)

**File-Level Task 1.1.1**: Create `InternalSignatureService` class.
*   **Subtask 1**: Implement `create_signature_request()`:
    *   Generates a unique access token for the signer.
    *   Stores coordinate metadata (page, x, y) for where the signature should appear.
    *   **Optional**: Apply commission for signature coordination (if configured).
*   **Subtask 2**: Implement `inject_signature_into_pdf()`:
    *   Use `fitz` (PyMuPDF) to open the document.
    *   Overlay the base64-encoded signature image at the specified coordinates.
    *   Save the resulting PDF to `storage/signed/`.
*   **Subtask 3**: Implement `generate_audit_trail()`:
    *   Create a new PDF page summarizing: Signer Name, Email, IP Address, Timestamp, Document Hash, and Blockchain TX ID.

**Commission Integration** (Optional):
```python
# In create_signature_request method, if commission is configured:
from app.services.commission_service import CommissionService
from decimal import Decimal

if charge_for_coordination:
    commission_service = CommissionService(db)
    commission_service.apply_commission(
        transaction_id=f"signature_{signature_request_id}",
        transaction_type="signature_coordination",
        transaction_amount=Decimal("0"),  # Or fixed fee from config
        payer_id=coordinator_user_id,
        transaction_metadata={"document_id": document_id}
    )
```

### Activity 1.2: Signature Model Updates
**File**: `app/db/models.py` (UPDATE)

**File-Level Task 1.2.1**: Update `DocumentSignature` model.
*   **Subtask 1**: Add `access_token` field for portal access.
*   **Subtask 2**: Add `coordinates` field (JSONB) to store `{"page": 1, "x": 100, "y": 200}`.
*   **Subtask 3**: Add `audit_data` field (JSONB) for IP, browser, and execution metadata.

---

## Project 2: API Endpoints & Permissions

### Activity 2.1: Native Signature Endpoints
**File**: `app/api/signature_routes.py` (NEW)

**File-Level Task 2.1.1**: Implement role-aware routes.
*   **Subtask 1**: `GET /api/signatures/my-pending`: For `APPLICANT` and `BANKER` to see what they need to sign (filtered by email).
*   **Subtask 2**: `GET /api/signatures/coordinated`: For `BANKER` and `LAW_OFFICER` to track requests they've sent.
*   **Subtask 3**: `POST /api/signatures/portal/{token}/sign`: Public endpoint for the signer portal.

### Activity 2.2: Permission Definitions
**File**: `app/core/permissions.py` & `client/src/utils/permissions.ts`

**File-Level Task 2.2.1**: Add signature management permissions.
*   **Subtask 1**: Add `SIGNATURE_COORDINATE` (for Bankers to send requests).
*   **Subtask 2**: Add `SIGNATURE_EXECUTE` (for any user to sign a document).
*   **Subtask 3**: Add `SIGNATURE_AUDIT` (for Auditors to view trails).

---

## Project 3: Unified Dashboard Integration

### Activity 3.1: Signature Dashboard Component
**File**: `client/src/components/dashboard-tabs/SignatureDashboard.tsx` (NEW)

**Note**: This component is integrated into the UnifiedDashboard as a tab. See `ELECTRON_REFACTORING_PLAN.md` for unified dashboard architecture.

**File-Level Task 3.1.1**: Create Signature Dashboard with role-based views.
*   **Subtask 1**: Create main SignatureDashboard component that conditionally renders sections based on permissions.
*   **Subtask 2**: Import and render `MyPendingSignatures` component (for all users).
*   **Subtask 3**: Conditionally render `SignatureCoordinationPanel` for users with `PERMISSION_SIGNATURE_COORDINATE`.
*   **Subtask 4**: Conditionally render `SignatureAuditTrail` for users with `PERMISSION_SIGNATURE_AUDIT`.
*   **Subtask 5**: Use `usePermissions` hook to check permissions.

**Implementation Pattern**:
```typescript
export function SignatureDashboard() {
  const { user } = useAuth();
  const { hasPermission } = usePermissions();
  
  return (
    <div className="space-y-6">
      {/* For all users */}
      <MyPendingSignatures />
      
      {/* For Bankers and Law Officers */}
      {hasPermission(PERMISSION_SIGNATURE_COORDINATE) && (
        <SignatureCoordinationPanel />
      )}
      
      {/* For Auditors */}
      {hasPermission(PERMISSION_SIGNATURE_AUDIT) && (
        <SignatureAuditTrail />
      )}
    </div>
  );
}
```

### Activity 3.2: Sub-Components
**File**: `client/src/components/dashboard-tabs/MyPendingSignatures.tsx` (NEW)

**File-Level Task 3.2.1**: Create User Signature Tracker.
*   **Subtask 1**: Fetch `my-pending` signatures from `/api/signatures/my-pending`.
*   **Subtask 2**: Display list with "Sign Now" buttons that open the `SignerPortal` or a modal.
*   **Subtask 3**: Show signature status and document information.

**File**: `client/src/components/dashboard-tabs/SignatureCoordinationPanel.tsx` (NEW)

**File-Level Task 3.2.2**: Implement Coordination view.
*   **Subtask 1**: Display all signature requests created by the user or their team.
*   **Subtask 2**: Show real-time progress (e.g., "2 of 3 signed").
*   **Subtask 3**: Provide "Remind Signer" button (triggers email).

**File**: `client/src/components/dashboard-tabs/SignatureAuditTrail.tsx` (NEW)

**File-Level Task 3.2.3**: Implement Audit Trail view.
*   **Subtask 1**: Display all signature events with timestamps.
*   **Subtask 2**: Show blockchain transaction hashes for verification.
*   **Subtask 3**: Provide download links for signed documents.

---

## Project 4: Native Signature UI (Frontend)

### Activity 4.1: Signature Capture Components
**File**: `client/src/components/ui/SignaturePad.tsx` (NEW)

**File-Level Task 4.1.1**: Implement HTML5 Canvas Signature Pad.
*   **Subtask 1**: Native Canvas drawing with "Smooth Line" smoothing.
*   **Subtask 2**: provide "Clear", "Undo", and "Adopt Typed" (standard font) options.

### Activity 4.2: The Signer Portal
**File**: `client/src/sites/signers/SignerPortal.tsx` (NEW)

**File-Level Task 4.2.1**: Create the signing experience.
*   **Subtask 1**: Token-based authentication (secure public route).
*   **Subtask 2**: PDF Preview with interactive "Sign Here" indicators.
*   **Subtask 3**: Final "I Agree" checkbox and legal disclaimer.

---

## Project 5: Smart Contract & Orchestration

### Activity 5.1: SecuritizationNotarization Enhancement
**File**: `contracts/SecuritizationNotarization.sol`

**File-Level Task 5.1.1**: Add Native Signature Fields.
*   **Subtask 1**: Add `documentRootHash` and `internalSignatureId` to `NotarizationRecord`.
*   **Subtask 2**: Implement `anchorInternalSignature()` called by the backend service.

### Activity 5.2: DigiSign Orchestrator
**File**: `app/services/digisign_service.py` (NEW)

**File-Level Task 5.2.1**: Unified workflow manager.
*   **Subtask 1**: Link the Native Engine completion to the Blockchain Notarization trigger.

---

## Integration with Unified Dashboard

### Overview
The DigiSign integration is designed to work within the UnifiedDashboard architecture. The SignatureDashboard component is accessible as a tab in the unified dashboard, with role-based views for different user types.

### Key Integration Points

1. **Component Location**: `client/src/components/dashboard-tabs/SignatureDashboard.tsx`
2. **Tab Configuration**: Added to UnifiedDashboard tabs array with:
   - Tab ID: `signatures`
   - Required Permission: `PERMISSION_SIGNATURE_VIEW`
   - Subscription Tier: `free` (Free tier can sign documents)
3. **Role-Based Views**: Component conditionally renders sections based on permissions:
   - All users: MyPendingSignatures
   - Bankers/Law Officers: SignatureCoordinationPanel
   - Auditors: SignatureAuditTrail
4. **Permission Checks**: All coordination and audit features check permissions
5. **Optional Commission**: Signature coordination can charge commission (configurable)
6. **Billing Integration**: Signature coordination costs (if enabled) are automatically tracked in the billing system (see `BILLING_DASHBOARD_PLAN.md`)

### Billing Integration Details

Signature coordination activities (if commission is enabled) automatically generate billing records:

1. **Signature Coordination Costs**: Tracked as `usage_cost` in billing periods (if commission is configured)
2. **Commission Charges**: Tracked as `commission_revenue` (for CreditNexus) in billing periods
3. **Cost Allocation**: Costs are allocated to organizations and roles via `CostAllocation` records
4. **Billing Dashboard**: Users can view their signature-related costs in the `BillingDashboard` component

**Code Reference**: See `BILLING_DASHBOARD_PLAN.md` for complete billing system details.

### References
- See `PLAN_INTEGRATION_ADDENDUM.md` for detailed integration patterns
- See `ELECTRON_REFACTORING_PLAN.md` for unified dashboard architecture
- See `MASTER_IMPLEMENTATION_PLAN.md` for overall implementation overview
- See `BILLING_DASHBOARD_PLAN.md` for billing system integration

---

## Implementation Roadmap (Role-Focused)

| Phase | Activity | Duration | Primary User |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Native PDF Injection & Internal Engine | 3 Days | Backend |
| **Phase 2** | Signer Portal & Signature Pad | 4 Days | Signer (Applicant) |
| **Phase 3** | Unified Dashboard Integration & Permissions | 3 Days | All Users |
| **Phase 4** | Smart Contract Anchoring & Audit Trail | 2 Days | Auditor |
| **Phase 5** | End-to-End Hybrid Flow | 2 Days | All |

**Note**: Phase 3 now includes integration with UnifiedDashboard. The SignatureDashboard component replaces separate widget components and is accessible as a tab in the unified dashboard.

---

## Success Criteria
1.  **Bankers** can track the lifecycle of every signature request from the unified dashboard Signature tab.
2.  **Applicants** receive a link and can sign on their mobile device without logging in.
3.  **Auditors** can download a signed document and verify its hash on the Base explorer.
4.  **No External Costs**: All signing logic is self-hosted and open-source compliant.
5.  **Unified Dashboard Integration**: SignatureDashboard is accessible as a tab in UnifiedDashboard with proper permission filtering.
6.  **Subscription Tier**: Signature execution is available to Free tier users (no subscription required for basic signing).

## Integration with Unified Dashboard

### Tab Configuration
**File**: `client/src/components/UnifiedDashboard.tsx` (UPDATE)

Add to dashboardTabs array:
```typescript
{
  id: 'signatures',
  label: 'Signatures',
  icon: <PenTool />,
  component: SignatureDashboard,
  requiredPermission: PERMISSION_SIGNATURE_VIEW,
  subscriptionTier: 'free'  // Free tier can sign documents
}
```

**Note**: See `PLAN_INTEGRATION_ADDENDUM.md` for complete integration details.
