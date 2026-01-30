import { createBrowserRouter, createHashRouter, Navigate, Link } from 'react-router-dom';
import { DesktopAppLayout } from '@/components/DesktopAppLayout';
import { LoginPage } from '@/pages/LoginPage';
import { SignupFlow } from '@/components/SignupFlow';
import { useAuth } from '@/context/AuthContext';

// BusinessApplicationForm removed - unused
import { BusinessApplicationFlow } from '@/sites/businesses/BusinessApplicationFlow';

import { IndividualLanding } from '@/sites/individuals/IndividualLanding';
import { IndividualApplicationFlow } from '@/sites/individuals/IndividualApplicationFlow';
import { BusinessLanding } from '@/sites/businesses/BusinessLanding';

import { DisbursementPage } from '@/sites/payments/DisbursementPage';
import { ReceiptPage } from '@/sites/payments/ReceiptPage';
import { MetaMaskLogin } from '@/sites/metamask/MetaMaskLogin';
import { SignerPortal } from '@/sites/signers/SignerPortal';
import { VerificationPage } from '@/apps/verification/VerificationPage';
import { VerificationFileConfigEditor } from '@/apps/verification-config/VerificationFileConfigEditor';
import { WorkflowProcessingPage } from '@/components/WorkflowProcessingPage';
import { WorkflowShareInterface } from '@/components/WorkflowShareInterface';
import { LicenseViewer } from '@/components/LicenseViewer';
import { UserSettings } from '@/pages/UserSettings';
import { PrivacyPolicy } from '@/components/PrivacyPolicy';

// Placeholder components for microsites (to be implemented)
// Note: /project and /docs are deployed separately (GitHub Pages and Mintlify)

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen bg-slate-900 text-white">Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// Admin Route Component
const AdminRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  if (user.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <>{children}</>;
};

// Use HashRouter when loaded via file:// (Electron loadFile) so /dashboard doesn't become file:///C:/dashboard
const createAppRouter = typeof window !== 'undefined' && window.location.protocol === 'file:'
  ? createHashRouter
  : createBrowserRouter;

export const router = createAppRouter([
    // Public routes
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/signup',
    element: <SignupFlow />,
  },
  {
    path: '/privacy-policy',
    element: <PrivacyPolicy />,
  },
  {
    path: '/signers/:token',
    element: <SignerPortal />,
  },
  
  // Application selection
  {
    path: '/apply',
    element: (
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-4">Apply</h1>
        <div className="space-y-4">
          <Link to="/apply/individual" className="block p-4 border rounded hover:bg-gray-100">
            Individual Application
          </Link>
          <Link to="/apply/business" className="block p-4 border rounded hover:bg-gray-100">
            Business Application
          </Link>
        </div>
      </div>
    ),
  },
  
  // Protected routes (main app - desktop layout)
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/document-parser',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/document-generator',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/trade-blotter',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/trading',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/link-accounts',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/asset-alerts',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/portfolio-risk',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/polymarket',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/bridge',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/green-lens',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/ground-truth',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/verification-demo',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/demo-data',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/risk-war-room',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/policy-editor',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/verification-config',
    element: (
      <AdminRoute>
        <DesktopAppLayout />
      </AdminRoute>
    ),
  },
  {
    path: '/app/whitelisting-dashboard',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/securitization',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/securitization/pools/:poolId',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/securitization/pools/:poolId/tranches/:trancheId/purchase',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/policy-editor/:policyId',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/library',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  
  // Auditor routes
  {
    path: '/auditor',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/auditor/logs/:id',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/auditor/deals/:dealId',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/auditor/loans/:loanId',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/auditor/filings/:filingId',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/auditor/reports',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/auditor/logs',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/auditor/policy',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/auditor/cdm-events',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/loan-recovery',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/agent-dashboard',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/filings',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  
  // Application routes
  {
    path: '/apply/individual',
    element: <IndividualApplicationFlow />,
  },
  {
    path: '/apply/business',
    element: <BusinessApplicationFlow />,
  },
  
  // Dashboard sub-routes
  {
    path: '/dashboard/applications',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/dashboard/admin-signups',
    element: (
      <AdminRoute>
        <DesktopAppLayout />
      </AdminRoute>
    ),
  },
  {
    path: '/dashboard/calendar',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/dashboard/deals',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/dashboard/deals/:dealId',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/apply/individual',
    element: <IndividualApplicationFlow />,
  },
  {
    path: '/apply/business',
    element: <BusinessApplicationFlow />,
  },
  {
    path: '/dashboard/inbox',
    element: (
      <AdminRoute>
        <div className="p-8">Inbox (Coming Soon)</div>
      </AdminRoute>
    ),
  },
  {
    path: '/settings',
    element: (
      <ProtectedRoute>
        <DesktopAppLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin-settings',
    element: (
      <AdminRoute>
        <DesktopAppLayout />
      </AdminRoute>
    ),
  },
  
  // Microsite routes
  // Note: /project and /docs are deployed separately (GitHub Pages and Mintlify)
  {
    path: '/individuals',
    element: <IndividualLanding />,
  },
  {
    path: '/businesses',
    element: <BusinessLanding />,
  },
  {
    path: '/disbursement',
    element: (
      <ProtectedRoute>
        <DisbursementPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/receipt',
    element: (
      <ProtectedRoute>
        <ReceiptPage />
      </ProtectedRoute>
    ),
  },
{
    path: '/metamask',
    element: <MetaMaskLogin />,
  },
  
  // Verification routes (public - no auth required for link viewing)
  {
    path: '/verify/:payload',
    element: <VerificationPage />,
  },
  
  // Workflow routes
  {
    path: '/app/workflow/process',
    element: (
      <ProtectedRoute>
        <WorkflowProcessingPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/app/workflow/share',
    element: (
      <ProtectedRoute>
        <WorkflowShareInterface />
      </ProtectedRoute>
    ),
  },
  
  // Admin configuration routes
  {
    path: '/config/verification-files',
    element: (
      <AdminRoute>
        <VerificationFileConfigEditor />
      </AdminRoute>
    ),
  },
  
  // License routes (public)
  {
    path: '/license',
    element: <LicenseViewer licenseType="license" />,
  },
  {
    path: '/licence',
    element: <LicenseViewer licenseType="license" />,
  },
  {
    path: '/rail',
    element: <LicenseViewer licenseType="rail" />,
  },
  
  // 404 route
  {
    path: '*',
    element: (
      <div className="p-8">
        <h1 className="text-2xl font-bold">404 - Page Not Found</h1>
        <Link to="/dashboard" className="text-blue-600 hover:underline">Go to Dashboard</Link>
      </div>
    ),
  },
]);
