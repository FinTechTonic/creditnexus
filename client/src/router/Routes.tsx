import { createBrowserRouter, Navigate } from 'react-router-dom';
import { DesktopAppLayout } from '@/components/DesktopAppLayout';
import { LoginPage } from '@/pages/LoginPage';
import { SignupFlow } from '@/components/SignupFlow';
import { useAuth } from '@/context/AuthContext';

import { BusinessApplicationForm } from '@/apps/application/BusinessApplicationForm';
import { BusinessApplicationFlow } from '@/sites/businesses/BusinessApplicationFlow';

import { IndividualLanding } from '@/sites/individuals/IndividualLanding';
import { IndividualApplicationFlow } from '@/sites/individuals/IndividualApplicationFlow';
import { BusinessLanding } from '@/sites/businesses/BusinessLanding';

import { DisbursementPage } from '@/sites/payments/DisbursementPage';
import { ReceiptPage } from '@/sites/payments/ReceiptPage';
import { MetaMaskLogin } from '@/sites/metamask/MetaMaskLogin';

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

// Router configuration
export const router = createBrowserRouter(
  [
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
  
  // Application selection
  {
    path: '/apply',
    element: (
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-4">Apply</h1>
        <div className="space-y-4">
          <a href="/apply/individual" className="block p-4 border rounded hover:bg-gray-100">
            Individual Application
          </a>
          <a href="/apply/business" className="block p-4 border rounded hover:bg-gray-100">
            Business Application
          </a>
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
    path: '/dashboard/inbox',
    element: (
      <AdminRoute>
        <div className="p-8">Inbox (Coming Soon)</div>
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
  
  // 404 route
  {
    path: '*',
    element: (
      <div className="p-8">
        <h1 className="text-2xl font-bold">404 - Page Not Found</h1>
        <a href="/dashboard" className="text-blue-600 hover:underline">Go to Dashboard</a>
      </div>
    ),
  },
  ],
  {
    future: {
      v7_startTransition: true,
    },
  }
);
