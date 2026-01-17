import { useState, useEffect, useMemo } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuth } from '@/context/AuthContext';
import { Dashboard } from '@/components/Dashboard';
import { DocumentHistory } from '@/components/DocumentHistory';
import { ApplicationDashboard } from '@/components/ApplicationDashboard';
import { TradeBlotter } from '@/apps/trade-blotter/TradeBlotter';
import type { CreditAgreementData } from '@/context/FDC3Context';
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
} from 'lucide-react';
import {
  PERMISSION_DOCUMENT_VIEW,
  PERMISSION_APPLICATION_VIEW,
} from '@/utils/permissions';

interface TradeBlotterState {
  loanData: CreditAgreementData | null;
  tradeStatus: 'pending' | 'confirmed' | 'settled';
  settlementDate: string;
  tradePrice: string;
  tradeAmount: string;
  tradeId: string | null;
  policyDecision: any | null;
  policyLoading: boolean;
  policyError: string | null;
  paymentRequest: any | null;
  paymentLoading: boolean;
  paymentError: string | null;
  paymentStatus: 'idle' | 'requested' | 'processing' | 'completed' | 'failed';
}

// Trading Dashboard wrapper that manages TradeBlotter state
function TradingDashboard() {
  const [tradeBlotterState, setTradeBlotterState] = useState<TradeBlotterState>({
    loanData: null,
    tradeStatus: 'pending',
    settlementDate: '',
    tradePrice: '100.00',
    tradeAmount: '',
    tradeId: null,
    policyDecision: null,
    policyLoading: false,
    policyError: null,
    paymentRequest: null,
    paymentLoading: false,
    paymentError: null,
    paymentStatus: 'idle',
  });

  return (
    <TradeBlotter
      state={tradeBlotterState}
      setState={setTradeBlotterState}
    />
  );
}

function MarketDashboard() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Polymarket Dashboard</h2>
      <p className="text-muted-foreground">Polymarket integration will be implemented here.</p>
    </div>
  );
}

function SignatureDashboard() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Signature Dashboard</h2>
      <p className="text-muted-foreground">DigiSign signature coordination will be implemented here.</p>
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

function PortfolioDashboard() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Portfolio Dashboard</h2>
      <p className="text-muted-foreground">Portfolio management and analytics will be implemented here.</p>
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
        component: TradingDashboard,
        requiredPermission: 'TRADING_VIEW', // Will be added to permissions.ts
        subscriptionTier: 'pro'
      },
      {
        id: 'polymarket',
        label: 'Polymarket',
        icon: <BarChart3 className="h-4 w-4" />,
        component: MarketDashboard,
        requiredPermission: 'MARKET_VIEW', // Will be added to permissions.ts
        subscriptionTier: 'pro'
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
      {
        id: 'portfolio',
        label: 'Portfolio',
        icon: <PieChart className="h-4 w-4" />,
        component: PortfolioDashboard,
        requiredPermission: 'PORTFOLIO_VIEW', // Will be added to permissions.ts
        subscriptionTier: 'pro'
      },
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
      
      // Check permissions
      if (tab.requiredPermission) {
        if (!hasPermission(tab.requiredPermission)) {
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
    <div className="flex flex-col h-full">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
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
