import React, { useState, useEffect, useMemo } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuth } from '@/context/AuthContext';
import { Dashboard } from '@/components/Dashboard';
import { DocumentHistory } from '@/components/DocumentHistory';
import { ApplicationDashboard } from '@/components/ApplicationDashboard';
import { TradeBlotter } from '@/apps/trade-blotter/TradeBlotter';
import type { CreditAgreementData } from '@/context/FDC3Context';
import { SignaturePad } from '@/components/ui/SignaturePad';
import { SignatureButton } from '@/components/SignatureButton';
import { SignatureStatus } from '@/components/SignatureStatus';
import { MyPendingSignatures } from '@/components/dashboard-tabs/MyPendingSignatures';
import { SignatureCoordinationPanel } from '@/components/dashboard-tabs/SignatureCoordinationPanel';
import { SignatureAuditTrail } from '@/components/dashboard-tabs/SignatureAuditTrail';
import { TradingDashboard } from '@/components/trading/TradingDashboard';
import { MarketDashboard } from '@/components/polymarket/MarketDashboard';
import { BridgeBuilder } from '@/components/BridgeBuilder';
import { PortfolioDashboard } from '@/components/PortfolioDashboard';
import { UnifiedInvestmentDashboard } from '@/components/investment/UnifiedInvestmentDashboard';
import { GDPRDashboard } from '@/components/dashboard-tabs/GDPRDashboard';
import {
  LayoutDashboard,
  TrendingUp,
  BarChart3,
  FileText,
  PenTool,
  Shield,
  PieChart,
  FileCheck,
  DollarSign,
  ArrowLeftRight,
  ExternalLink,
} from 'lucide-react';
import {
  PERMISSION_DOCUMENT_VIEW,
  PERMISSION_APPLICATION_VIEW,
} from '@/utils/permissions';

function SignatureDashboard() {
  const [activeTab, setActiveTab] = React.useState('pending');

  return (
    <div className="p-6 space-y-6 flex flex-col h-full overflow-hidden">
      <div>
        <h2 className="text-2xl font-bold mb-2 text-slate-100">Signature Dashboard</h2>
        <p className="text-muted-foreground max-w-2xl text-sm">
          Manage digital signatures for your documents. Open any document from the Documents tab to request a
          signature, then track its status here or on the deal view.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
        <TabsList className="bg-slate-900 border-slate-800 self-start">
          <TabsTrigger value="pending" className="data-[state=active]:bg-slate-800">My Pending</TabsTrigger>
          <TabsTrigger value="coordinated" className="data-[state=active]:bg-slate-800">Coordination</TabsTrigger>
          <TabsTrigger value="audit" className="data-[state=active]:bg-slate-800">Global Audit</TabsTrigger>
          <TabsTrigger value="guide" className="data-[state=active]:bg-slate-800">Help Guide</TabsTrigger>
        </TabsList>

        <TabsContent value="pending" className="flex-1 overflow-auto mt-4 bg-slate-950/20 rounded-xl border border-slate-800/50">
          <MyPendingSignatures />
        </TabsContent>

        <TabsContent value="coordinated" className="flex-1 overflow-auto mt-4 bg-slate-950/20 rounded-xl border border-slate-800/50">
          <SignatureCoordinationPanel />
        </TabsContent>

        <TabsContent value="audit" className="flex-1 overflow-auto mt-4 p-6 bg-slate-950/20 rounded-xl border border-slate-800/50">
          <SignatureAuditTrail />
        </TabsContent>

        <TabsContent value="guide" className="flex-1 overflow-auto mt-4 p-6 bg-slate-950/20 rounded-xl border border-slate-800/50">
          <div className="grid gap-8 md:grid-cols-2">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                <PenTool className="h-5 w-5 text-blue-400" />
                Workflow Instructions
              </h3>
              <ol className="list-decimal list-inside text-sm text-slate-300 space-y-3 leading-relaxed">
                <li>Go to the <span className="text-blue-400 font-semibold">Documents</span> tab and select any document.</li>
                <li>Use the <span className="text-emerald-400 font-semibold">“Sign”</span> button in the top toolbar to open the request modal.</li>
                <li>Verify signer details (names, roles, and emails).</li>
                <li>Submit the request. Our system will generate a secure, token-based link.</li>
                <li>The signer receives an email notification with their unique link.</li>
              </ol>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                <ExternalLink className="h-5 w-5 text-emerald-400" />
                Native Signer Portal
              </h3>
              <p className="text-sm text-slate-300 leading-relaxed">
                External signers do not need a CreditNexus account. They can use their secure token links to access
                the <span className="text-emerald-400 italic">Signer Portal</span>, where they can:
              </p>
              <ul className="list-disc list-inside text-sm text-slate-400 space-y-1 ml-2">
                <li>Preview the document content</li>
                <li>Draw or type their signature</li>
                <li>Provide MetaMask verification (if required)</li>
                <li>Download a signed copy instantly</li>
              </ul>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ComplianceDashboard() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Compliance Dashboard</h2>
      <p className="text-muted-foreground">Compliance monitoring and reporting will be implemented here.</p>
    </div>
  );
}

function BillingDashboard() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Billing Dashboard</h2>
      <p className="text-muted-foreground">Billing and subscription management will be implemented here.</p>
    </div>
  );
}

interface DashboardTab {
  id: string;
  label: string;
  icon: React.ReactNode;
  component: React.ComponentType;
  requiredPermission?: string;
  requiredPermissions?: string[];
  requireAll?: boolean;
  subscriptionTier?: 'free' | 'pro' | 'premium' | 'lifetime';
}

export function UnifiedDashboard() {
  const { user } = useAuth();
  const { hasPermission, hasAllPermissions } = usePermissions();
  const [activeTab, setActiveTab] = useState<string>('overview');
  
  // Get user subscription tier (from user model or API)
  // TODO: Update User interface to include subscription_tier when subscription system is implemented
  const subscriptionTier = (user as any)?.subscription_tier || 'free';
  
  const dashboardTabs: DashboardTab[] = useMemo(() => {
    const tabs: DashboardTab[] = [
      {
        id: 'overview',
        label: 'Overview',
        icon: <LayoutDashboard className="h-4 w-4" />,
        component: Dashboard,
        subscriptionTier: 'free'
      },
      {
        id: 'trading',
        label: 'Trading',
        icon: <TrendingUp className="h-4 w-4" />,
        component: () => <UnifiedInvestmentDashboard />,
        // requiredPermission removed: tab always visible; UnifiedInvestmentDashboard gates content
        subscriptionTier: 'free'
      },
      {
        id: 'polymarket',
        label: 'Polymarket',
        icon: <BarChart3 className="h-4 w-4" />,
        component: () => <MarketDashboard />,
        requiredPermission: 'MARKET_VIEW',
        subscriptionTier: 'pro'
      },
      {
        id: 'bridge',
        label: 'Bridge',
        icon: <ArrowLeftRight className="h-4 w-4" />,
        component: () => <BridgeBuilder />,
        requiredPermission: 'TRADE_VIEW',
        subscriptionTier: 'free'
      },
      {
        id: 'documents',
        label: 'Documents',
        icon: <FileText className="h-4 w-4" />,
        component: () => <DocumentHistory />,
        requiredPermission: PERMISSION_DOCUMENT_VIEW,
        subscriptionTier: 'free'
      },
      {
        id: 'signatures',
        label: 'Signatures',
        icon: <PenTool className="h-4 w-4" />,
        component: SignatureDashboard,
        requiredPermission: 'SIGNATURE_VIEW', // Will be added to permissions.ts
        subscriptionTier: 'free'
      },
      {
        id: 'compliance',
        label: 'Compliance',
        icon: <Shield className="h-4 w-4" />,
        component: ComplianceDashboard,
        requiredPermission: 'COMPLIANCE_VIEW', // Will be added to permissions.ts
        subscriptionTier: 'premium'
      },
      // Portfolio tab removed - now integrated into Trading tab (UnifiedInvestmentDashboard)
      {
        id: 'applications',
        label: 'Applications',
        icon: <FileCheck className="h-4 w-4" />,
        component: ApplicationDashboard,
        requiredPermission: PERMISSION_APPLICATION_VIEW,
        subscriptionTier: 'free'
      },
      {
        id: 'billing',
        label: 'Billing',
        icon: <DollarSign className="h-4 w-4" />,
        component: BillingDashboard,
        requiredPermission: 'BILLING_VIEW', // Will be added to permissions.ts
        subscriptionTier: 'free'  // All tiers can view their billing
      },
      {
        id: 'privacy',
        label: 'Privacy',
        icon: <Shield className="h-4 w-4" />,
        component: GDPRDashboard,
        subscriptionTier: 'free'
      }
    ];
    
    // Filter tabs based on permissions and subscription
    return tabs.filter(tab => {
      // Check subscription tier
      const tierLevels: Record<string, number> = { free: 0, pro: 1, premium: 2, lifetime: 3 };
      const userTierLevel = tierLevels[subscriptionTier as string] || 0;
      const tabTierLevel = tierLevels[tab.subscriptionTier || 'free'];
      if (userTierLevel < tabTierLevel) {
        return false;
      }
      
      // Check permissions (admin bypass: always allow if role is admin)
      if (tab.requiredPermission) {
        const isAdmin = (user?.role || '').toLowerCase() === 'admin';
        if (!isAdmin && !hasPermission(tab.requiredPermission)) {
          return false;
        }
      }
      if (tab.requiredPermissions) {
        if (!hasAllPermissions(tab.requiredPermissions)) {
          return false;
        }
      }
      
      return true;
    });
  }, [user, subscriptionTier, hasPermission, hasAllPermissions]);
  
  // Set active tab to first available tab if current tab is not available
  useEffect(() => {
    if (dashboardTabs.length > 0 && !dashboardTabs.find(tab => tab.id === activeTab)) {
      setActiveTab(dashboardTabs[0].id);
    }
  }, [dashboardTabs, activeTab]);

  return (
    <div className="flex flex-col h-full space-y-4">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start border-b rounded-none">
          {dashboardTabs.map(tab => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              className="flex items-center gap-2"
            >
              {tab.icon}
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
        
        {dashboardTabs.map(tab => {
          const TabComponent = tab.component;
          return (
            <TabsContent key={tab.id} value={tab.id} className="flex-1 overflow-auto mt-0">
              <TabComponent />
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}
