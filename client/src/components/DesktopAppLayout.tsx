import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { DocumentParser } from '@/apps/docu-digitizer/DocumentParser';
import { TradeBlotter } from '@/apps/trade-blotter/TradeBlotter';
import { GreenLens } from '@/apps/green-lens/GreenLens';
import { DocumentGenerator } from '@/apps/document-generator/DocumentGenerator';
import { PolicyEditor } from '@/apps/policy-editor/PolicyEditor';
import { DocumentHistory } from '@/components/DocumentHistory';
// Dashboard removed - unused
import { UnifiedDashboard } from '@/components/UnifiedDashboard';
import { GroundTruthDashboard } from '@/components/GroundTruthDashboard';
import { ApplicationDashboard } from '@/components/ApplicationDashboard';
import { AdminSignupDashboard } from '@/components/AdminSignupDashboard';
import { CalendarView } from '@/components/CalendarView';
import { DealDashboard } from '@/components/DealDashboard';
import { DealDetail } from '@/components/DealDetail';
import { LoginForm } from '@/components/LoginForm';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { QuickAccessSettings } from '@/components/QuickAccessSettings';
import { Breadcrumb, BreadcrumbContainer } from '@/components/ui/Breadcrumb';
import { Button } from '@/components/ui/button';
import { FileText, ArrowLeftRight, Leaf, Sparkles, Radio, LogIn, LogOut, User, Loader2, BookOpen, LayoutDashboard, ChevronLeft, ChevronRight, Shield, RadioTower, Building2, Database, Share2, AlertTriangle, Link2, Bell, BarChart2, TrendingUp, BarChart3, PieChart, PenTool, FileCheck, DollarSign, Calendar, Users, Settings, Layers, FileSearch, MessageSquare, Headphones } from 'lucide-react';
import { UserMenu } from '@/components/UserMenu';
import { SidebarNavigation } from '@/components/SidebarNavigation';
import { CookieBanner } from '@/components/CookieBanner';
import { useAuth } from '@/context/AuthContext';
import { useFDC3 } from '@/context/FDC3Context';
import type { CreditAgreementData, IntentName, DocumentContext, AgreementContext, WorkflowLinkContext } from '@/context/FDC3Context';
import VerificationDashboard from '@/components/VerificationDashboard';
import { DemoDataDashboard } from '@/components/DemoDataDashboard';
import RiskWarRoom from '@/components/RiskWarRoom';
import { AuditorRouter } from '@/apps/auditor/AuditorRouter';
import { SecuritizationWorkflow } from '@/apps/securitization/SecuritizationWorkflow';
import { SecuritizationPoolDetail } from '@/components/SecuritizationPoolDetail';
import { TranchePurchase } from '@/components/TranchePurchase';
import { VerificationFileConfigEditor } from '@/apps/verification-config/VerificationFileConfigEditor';
import { WhitelistingDashboard } from '@/apps/whitelisting-dashboard/WhitelistingDashboard';
import { WorkflowShareInterface } from '@/components/WorkflowShareInterface';
// WorkflowDelegationDashboard removed - unused
import { WorkflowProcessingPage } from '@/components/WorkflowProcessingPage';
import { LoanRecoverySidebar } from '@/components/LoanRecoverySidebar';
import { AgentDashboard } from '@/apps/agent-dashboard/AgentDashboard';
import { LinkAccounts } from '@/components/LinkAccounts';
import { AssetAlertsView } from '@/apps/asset-alerts/AssetAlertsView';
import { PortfolioRiskView } from '@/apps/portfolio-risk/PortfolioRiskView';
import { FilingStatusDashboard } from '@/components/FilingStatusDashboard';
import { MarketDashboard } from '@/components/polymarket/MarketDashboard';
import { PolymarketTrading } from '@/components/polymarket/PolymarketTrading';
import { PolymarketFunding } from '@/components/polymarket/PolymarketFunding';
import { Newsfeed } from '@/components/dashboard-tabs/Newsfeed';
import { BankProductsMarketplace } from '@/components/BankProductsMarketplace';
import { BridgeBuilder } from '@/components/BridgeBuilder';
import { TradingDashboard } from '@/components/trading/TradingDashboard';
import { UserSettings } from '@/pages/UserSettings';
import { AdminSettings } from '@/pages/AdminSettings';
import { BillingDashboard } from '@/components/UnifiedDashboard';
import { DashboardChatbotPanel } from '@/components/DashboardChatbotPanel';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { usePermissions } from '@/hooks/usePermissions';
import { useThemeClasses } from '@/utils/themeUtils';
import { Link } from 'react-router-dom';
import {
  PERMISSION_DOCUMENT_VIEW,
  PERMISSION_DOCUMENT_CREATE,
  PERMISSION_TEMPLATE_VIEW,
  PERMISSION_TEMPLATE_GENERATE,
  PERMISSION_TRADE_VIEW,
  PERMISSION_SATELLITE_VIEW,
  // PERMISSION_APPLICATION_VIEW removed - unused
  PERMISSION_USER_VIEW,
  PERMISSION_DEAL_VIEW,
  PERMISSION_DEAL_VIEW_OWN,
  PERMISSION_AUDIT_VIEW,
  PERMISSION_MARKET_VIEW,
  PERMISSION_COMPLIANCE_VIEW,
  PERMISSION_SIGNATURE_VIEW,
  PERMISSION_APPLICATION_VIEW,
  PERMISSION_BILLING_VIEW,
} from '@/utils/permissions';

type AppView = 'dashboard' | 'document-parser' | 'trade-blotter' | 'green-lens' | 'library' | 'ground-truth' | 'verification-demo' | 'demo-data' | 'risk-war-room' | 'document-generator' | 'applications' | 'calendar' | 'admin-signups' | 'policy-editor' | 'deals' | 'auditor' | 'securitization' | 'verification-config' | 'whitelisting-dashboard' | 'workflow-processor' | 'workflow-share' | 'loan-recovery' | 'agent-dashboard' | 'filings' | 'link-accounts' | 'asset-alerts' | 'portfolio-risk' | 'trading' | 'polymarket' | 'newsfeed' | 'bank-products' | 'bridge' | 'signatures' | 'compliance' | 'billing' | 'settings' | 'admin-settings';

interface AppConfig {
  id: AppView;
  name: string;
  icon: React.ReactNode;
  description: string;
  requiredPermission?: string;
  requiredPermissions?: string[];
  requireAll?: boolean;
  subscriptionTier?: 'free' | 'pro' | 'premium' | 'lifetime';
  category?: 'core' | 'trading' | 'compliance' | 'admin' | 'tools';
  isInstanceAdminOnly?: boolean;
  path?: string;
}

// All apps consolidated into sidebar - mainApps removed, everything goes to sidebarApps
const mainApps: AppConfig[] = [];

const sidebarApps: AppConfig[] = [
  // Core Applications (order: dashboard, newsfeed, link-accounts, settings, library, doc-parser, doc-generator)
  {
    id: 'dashboard',
    name: 'Dashboard',
    icon: <LayoutDashboard className="h-5 w-5" />,
    description: 'Portfolio overview & analytics',
    path: '/dashboard',
    category: 'core',
    subscriptionTier: 'free',
  },
  {
    id: 'newsfeed',
    name: 'Social Feeds',
    icon: <Share2 className="h-5 w-5" />,
    description: 'Deals & markets feed, like, comment, share',
    path: '/app/newsfeed',
    category: 'core',
    subscriptionTier: 'free',
  },
  {
    id: 'link-accounts',
    name: 'Link Accounts',
    icon: <Link2 className="h-5 w-5" />,
    description: 'Connect bank and data sources',
    path: '/app/link-accounts',
    category: 'core',
    subscriptionTier: 'free',
  },
  {
    id: 'settings',
    name: 'User Settings',
    icon: <Settings className="h-5 w-5" />,
    description: 'Manage your account preferences',
    path: '/settings',
    category: 'core',
    subscriptionTier: 'free',
  },
  {
    id: 'library',
    name: 'Library',
    icon: <BookOpen className="h-5 w-5" />,
    description: 'Saved documents & history',
    path: '/library',
    category: 'core',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
    subscriptionTier: 'free',
  },
  {
    id: 'document-parser',
    name: 'Document Parser',
    icon: <FileText className="h-5 w-5" />,
    description: 'Extract & digitize credit agreements',
    path: '/app/document-parser',
    category: 'core',
    requiredPermission: PERMISSION_DOCUMENT_CREATE,
    subscriptionTier: 'free',
  },
  {
    id: 'document-generator',
    name: 'Document Generator',
    icon: <Sparkles className="h-5 w-5" />,
    description: 'Generate LMA documents from templates',
    path: '/app/document-generator',
    category: 'core',
    requiredPermissions: [PERMISSION_TEMPLATE_VIEW, PERMISSION_TEMPLATE_GENERATE],
    requireAll: false,
    subscriptionTier: 'free',
  },
  // Trading Applications
  {
    id: 'trading',
    name: 'Trading',
    icon: <TrendingUp className="h-5 w-5" />,
    description: 'Execute trades and manage positions',
    path: '/app/trading',
    category: 'trading',
    requiredPermission: PERMISSION_TRADE_VIEW,
    subscriptionTier: 'pro',
  },
  {
    id: 'polymarket',
    name: 'Polymarket',
    icon: <BarChart3 className="h-5 w-5" />,
    description: 'Credit event prediction markets',
    path: '/app/polymarket',
    category: 'trading',
    requiredPermission: PERMISSION_MARKET_VIEW,
    subscriptionTier: 'pro',
  },
  {
    id: 'bridge',
    name: 'Bridge',
    icon: <ArrowLeftRight className="h-5 w-5" />,
    description: 'Cross-chain asset transfers',
    path: '/app/bridge',
    category: 'trading',
    requiredPermission: PERMISSION_TRADE_VIEW,
    subscriptionTier: 'free',
  },
  {
    id: 'trade-blotter',
    name: 'Trade Blotter',
    icon: <ArrowLeftRight className="h-5 w-5" />,
    description: 'LMA trade confirmation & settlement',
    path: '/app/trade-blotter',
    category: 'trading',
    requiredPermission: PERMISSION_TRADE_VIEW,
    subscriptionTier: 'free',
  },
  {
    id: 'link-accounts',
    name: 'Link Accounts',
    icon: <Link2 className="h-5 w-5" />,
    description: 'Connect bank and data sources',
    path: '/app/link-accounts',
    category: 'trading',
    requiredPermission: PERMISSION_TRADE_VIEW,
    subscriptionTier: 'free',
  },
  {
    id: 'asset-alerts',
    name: 'Asset Alerts',
    icon: <Bell className="h-5 w-5" />,
    description: 'Maturities and amortization reminders',
    path: '/app/asset-alerts',
    category: 'trading',
    requiredPermission: PERMISSION_TRADE_VIEW,
    subscriptionTier: 'free',
  },
  {
    id: 'portfolio-risk',
    name: 'Risk Analysis',
    icon: <BarChart2 className="h-5 w-5" />,
    description: 'Portfolio risk metrics and analysis',
    path: '/app/portfolio-risk',
    category: 'trading',
    requiredPermission: PERMISSION_TRADE_VIEW,
    subscriptionTier: 'pro',
  },
  // Compliance Applications
  {
    id: 'compliance',
    name: 'Compliance',
    icon: <Shield className="h-5 w-5" />,
    description: 'Compliance monitoring and reporting',
    path: '/dashboard?tab=compliance',
    category: 'compliance',
    requiredPermission: PERMISSION_COMPLIANCE_VIEW,
    subscriptionTier: 'premium',
  },
  {
    id: 'signatures',
    name: 'Signatures',
    icon: <PenTool className="h-5 w-5" />,
    description: 'Document signature management',
    path: '/dashboard?tab=signatures',
    category: 'compliance',
    requiredPermission: PERMISSION_SIGNATURE_VIEW,
    subscriptionTier: 'free',
  },
  {
    id: 'applications',
    name: 'Applications',
    icon: <FileCheck className="h-5 w-5" />,
    description: 'Loan and credit applications',
    path: '/dashboard/applications',
    category: 'compliance',
    requiredPermission: PERMISSION_APPLICATION_VIEW,
    subscriptionTier: 'free',
  },
  {
    id: 'deals',
    name: 'Deals',
    icon: <FileSearch className="h-5 w-5" />,
    description: 'Deal management and tracking',
    path: '/dashboard/deals',
    category: 'compliance',
    requiredPermissions: [PERMISSION_DEAL_VIEW, PERMISSION_DEAL_VIEW_OWN],
    requireAll: false,
    subscriptionTier: 'free',
  },
  {
    id: 'filings',
    name: 'Filings',
    icon: <FileText className="h-5 w-5" />,
    description: 'Regulatory filing status',
    path: '/app/filings',
    category: 'compliance',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
    subscriptionTier: 'free',
  },
  {
    id: 'green-lens',
    name: 'Green Lens',
    icon: <Leaf className="h-5 w-5" />,
    description: 'ESG analytics and sustainability',
    path: '/app/green-lens',
    category: 'compliance',
    requiredPermission: PERMISSION_SATELLITE_VIEW,
    subscriptionTier: 'pro',
  },
  {
    id: 'ground-truth',
    name: 'Ground Truth',
    icon: <Shield className="h-5 w-5" />,
    description: 'Geospatial verification for sustainability-linked loans',
    path: '/app/ground-truth',
    category: 'compliance',
    requiredPermission: PERMISSION_SATELLITE_VIEW,
    subscriptionTier: 'pro',
  },
  {
    id: 'auditor',
    name: 'Auditor',
    icon: <Shield className="h-5 w-5" />,
    description: 'Audit reports and compliance checks',
    path: '/auditor',
    category: 'compliance',
    requiredPermission: PERMISSION_AUDIT_VIEW,
    subscriptionTier: 'premium',
  },
  // Tools
  {
    id: 'agent-dashboard',
    name: 'Agent Dashboard',
    icon: <Sparkles className="h-5 w-5" />,
    description: 'AI agent workflows and results',
    path: '/app/agent-dashboard',
    category: 'tools',
    subscriptionTier: 'pro',
  },
  {
    id: 'securitization',
    name: 'Securitization',
    icon: <Layers className="h-5 w-5" />,
    description: 'Securitization pool management',
    path: '/app/securitization',
    category: 'tools',
    requiredPermission: PERMISSION_TRADE_VIEW,
    subscriptionTier: 'pro',
  },
  {
    id: 'calendar',
    name: 'Calendar',
    icon: <Calendar className="h-5 w-5" />,
    description: 'Deal and payment calendar',
    path: '/dashboard/calendar',
    category: 'tools',
    subscriptionTier: 'free',
  },
  {
    id: 'billing',
    name: 'Billing',
    icon: <DollarSign className="h-5 w-5" />,
    description: 'Billing and subscription management',
    path: '/dashboard?tab=billing',
    category: 'tools',
    requiredPermission: PERMISSION_BILLING_VIEW,
    subscriptionTier: 'free',
  },
  // Admin Applications (Instance Admin Only)
  {
    id: 'admin-signups',
    name: 'User Signups',
    icon: <Users className="h-5 w-5" />,
    description: 'Review and approve user signups',
    path: '/dashboard/admin-signups',
    category: 'admin',
    isInstanceAdminOnly: true,
    subscriptionTier: 'free',
  },
  {
    id: 'demo-data',
    name: 'Demo Data',
    icon: <Database className="h-5 w-5" />,
    description: 'Seed and manage demo data',
    path: '/app/demo-data',
    category: 'admin',
    isInstanceAdminOnly: true,
    subscriptionTier: 'free',
  },
  {
    id: 'verification-config',
    name: 'Verification Config',
    icon: <Settings className="h-5 w-5" />,
    description: 'Verification file configuration',
    path: '/app/verification-config',
    category: 'admin',
    isInstanceAdminOnly: true,
    subscriptionTier: 'free',
  },
  {
    id: 'whitelisting-dashboard',
    name: 'Whitelisting',
    icon: <Shield className="h-5 w-5" />,
    description: 'IP and file whitelist management',
    path: '/app/whitelisting-dashboard',
    category: 'admin',
    isInstanceAdminOnly: true,
    subscriptionTier: 'free',
  },
  {
    id: 'policy-editor',
    name: 'Policy Editor',
    icon: <Shield className="h-5 w-5" />,
    description: 'Edit policy rules and compliance',
    path: '/app/policy-editor',
    category: 'admin',
    isInstanceAdminOnly: true,
    subscriptionTier: 'free',
  },
  {
    id: 'risk-war-room',
    name: 'Risk War Room',
    icon: <AlertTriangle className="h-5 w-5" />,
    description: 'Risk monitoring and alerts',
    path: '/app/risk-war-room',
    category: 'admin',
    isInstanceAdminOnly: true,
    subscriptionTier: 'free',
  },
  {
    id: 'workflow-processor',
    name: 'Workflow Processor',
    icon: <Share2 className="h-5 w-5" />,
    description: 'Process workflow links',
    path: '/app/workflow/process',
    category: 'admin',
    subscriptionTier: 'free',
  },
  {
    id: 'workflow-share',
    name: 'Workflow Share',
    icon: <Share2 className="h-5 w-5" />,
    description: 'Share workflow links',
    path: '/app/workflow/share',
    category: 'admin',
    subscriptionTier: 'free',
  },
  {
    id: 'loan-recovery',
    name: 'Loan Recovery',
    icon: <ArrowLeftRight className="h-5 w-5" />,
    description: 'Loan recovery management',
    path: '/app/loan-recovery',
    category: 'admin',
    subscriptionTier: 'free',
  },
  {
    id: 'admin-settings',
    name: 'Admin Settings',
    icon: <Settings className="h-5 w-5" />,
    description: 'System and organization settings',
    path: '/admin-settings',
    category: 'admin',
    subscriptionTier: 'free',
  },
];

interface PolicyDecision {
  decision: 'ALLOW' | 'BLOCK' | 'FLAG';
  rule_applied?: string;
  trace_id?: string;
  requires_review?: boolean;
}

interface PaymentRequest {
  amount: string;
  currency: string;
  payer: { id: string; name: string; lei?: string };
  receiver: { id: string; name: string; lei?: string };
  facilitator_url: string;
}

interface TradeBlotterState {
  loanData: CreditAgreementData | null;
  tradeStatus: 'pending' | 'confirmed' | 'settled';
  settlementDate: string;
  tradePrice: string;
  tradeAmount: string;
  tradeId: string | null;
  policyDecision: PolicyDecision | null;
  policyLoading: boolean;
  policyError: string | null;
  paymentRequest: PaymentRequest | null;
  paymentLoading: boolean;
  paymentError: string | null;
  paymentStatus: 'idle' | 'requested' | 'processing' | 'completed' | 'failed';
}

interface QuickAccessPreferences {
  audio_input_mode?: boolean;
  investment_mode?: boolean;
  loan_mode?: boolean;
  bank_mode?: boolean;
  trading_mode?: boolean;
}

function pickAppFromPreferences(prefs: QuickAccessPreferences | null): AppView | null {
  if (!prefs) return null;
  // Trading / investment modes should take the user
  // directly to a trading-focused view.
  if (prefs.trading_mode || prefs.investment_mode) return 'portfolio-risk';
  // Loan mode should emphasize loan applications and
  // related workflows.
  if (prefs.loan_mode) return 'applications';
  // Bank mode should surface bank account connectivity.
  if (prefs.bank_mode) return 'link-accounts';
  return null;
}

export function DesktopAppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const classes = useThemeClasses();
  
  // Intentionally start blank so the first sync effect run can reconcile route → activeApp.
  const previousPathnameRef = useRef<string>('');
  
  // Initialize activeApp from current route to avoid mismatches
  // CRITICAL: Persist activeApp in sessionStorage to survive component re-mounts
  const getInitialApp = (): AppView => {
    // Route-based detection (preferred over persisted state)
    const pathToApp: Record<string, AppView> = {
      '/dashboard': 'dashboard',
      '/dashboard/applications': 'applications',
      '/dashboard/admin-signups': 'admin-signups',
      '/dashboard/calendar': 'calendar',
      '/dashboard/deals': 'deals',
      '/app/document-parser': 'document-parser',
      '/app/document-generator': 'document-generator',
      '/app/trade-blotter': 'trade-blotter',
      '/app/trading': 'trading',
      '/app/link-accounts': 'link-accounts',
      '/app/asset-alerts': 'asset-alerts',
      '/app/portfolio-risk': 'portfolio-risk',
      '/app/polymarket': 'polymarket',
      '/app/bridge': 'bridge',
      '/app/securitization': 'securitization',
      '/app/workflow/share': 'workflow-share',
      '/app/workflow/process': 'workflow-processor',
      '/app/green-lens': 'green-lens',
      '/app/ground-truth': 'ground-truth',
      '/app/verification-demo': 'verification-demo',
      '/app/demo-data': 'demo-data',
      '/app/risk-war-room': 'risk-war-room',
      '/app/policy-editor': 'policy-editor',
      '/app/verification-config': 'verification-config',
      '/app/whitelisting-dashboard': 'whitelisting-dashboard',
      '/app/agent-dashboard': 'agent-dashboard',
      '/app/filings': 'filings',
      '/library': 'library',
      '/auditor': 'auditor',
      '/settings': 'settings',
      '/admin-settings': 'admin-settings',
    };

    const basePathname = location.pathname.split('?')[0];

    // Handle special route prefixes
    if (basePathname.startsWith('/app/policy-editor')) return 'policy-editor';
    if (basePathname.startsWith('/dashboard/deals/')) return 'deals';
    if (basePathname.startsWith('/auditor')) return 'auditor';
    if (basePathname.startsWith('/app/securitization')) return 'securitization';

    // Handle policy-editor routes with policyId parameter
    if (location.pathname.startsWith('/app/policy-editor')) {
      return 'policy-editor';
    }
    // Handle deal detail routes
    if (location.pathname.startsWith('/dashboard/deals/')) {
      return 'deals';
    }
    // Handle auditor routes
    if (location.pathname.startsWith('/auditor')) {
      return 'auditor';
    }
    // Handle dashboard tabs
    const urlParams = new URLSearchParams(location.search);
    const tab = urlParams.get('tab');
    if (tab === 'trading') return 'trading';
    if (tab === 'polymarket') return 'polymarket';
    if (tab === 'bridge') return 'bridge';
    if (tab === 'signatures') return 'signatures';
    if (tab === 'compliance') return 'compliance';
    if (tab === 'billing') return 'billing';
    
    const routeApp = pathToApp[basePathname] || pathToApp[location.pathname];
    if (routeApp) return routeApp;

    // Fall back to persisted state only if we couldn't infer from the route.
    const validApps: AppView[] = [
      'dashboard', 'applications', 'admin-signups', 'calendar', 'deals',
      'document-parser', 'document-generator', 'trade-blotter', 'green-lens',
      'ground-truth', 'verification-demo', 'demo-data', 'risk-war-room',
      'policy-editor', 'library', 'auditor', 'securitization', 'verification-config', 'whitelisting-dashboard',
      'workflow-processor', 'workflow-share', 'loan-recovery', 'agent-dashboard', 'filings', 'link-accounts', 'asset-alerts', 'portfolio-risk',
      'trading', 'polymarket', 'newsfeed', 'bank-products', 'bridge', 'signatures', 'compliance', 'billing', 'settings', 'admin-settings'
    ];

    if (typeof window !== 'undefined') {
      const persisted = sessionStorage.getItem('creditnexus_activeApp');
      if (persisted && validApps.includes(persisted as AppView)) {
        return persisted as AppView;
      }
    }

    return 'dashboard';
  };
  
  const [activeAppState, setActiveAppState] = useState<AppView>(getInitialApp());
  
  // Wrap setActiveApp to persist to sessionStorage
  const setActiveApp = useCallback((value: AppView | ((prev: AppView) => AppView)) => {
    setActiveAppState((prev) => {
      const newValue = typeof value === 'function' ? value(prev) : value;
      // Persist to sessionStorage
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('creditnexus_activeApp', newValue);
        // Also store tab state if applicable (for apps that support tabs)
        // Tab state is typically stored in URL params, but we can also store in sessionStorage as backup
        const currentUrl = new URL(window.location.href);
        const tabParam = currentUrl.searchParams.get('tab');
        if (tabParam) {
          sessionStorage.setItem(`creditnexus_${newValue}_tab`, tabParam);
        }
      }
      return newValue;
    });
  }, []);
  
  const activeApp = activeAppState;
  
  // Track unexpected route changes (moved here to avoid TDZ error)
  // NOTE: Do NOT update previousPathnameRef here - let the sync useEffect handle it
  useEffect(() => {
    if (location.pathname !== previousPathnameRef.current) {
      // DO NOT update previousPathnameRef here - the sync useEffect will handle it
    }
  }, [location.pathname, activeApp]);
  
  const [hasBroadcast, setHasBroadcast] = useState(false);
  const [viewData, setViewData] = useState<CreditAgreementData | null>(null);
  const [extractionContent, setExtractionContent] = useState<string | null>(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
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
  const [globalChatOpen, setGlobalChatOpen] = useState(false);
  const [supportChatOpen, setSupportChatOpen] = useState(false);
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const { isAvailable, pendingIntent, clearPendingIntent, onIntentReceived } = useFDC3();
  const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermissions();
  
  // Check if user is instance admin
  const isInstanceAdmin = user?.role === 'admin' && user?.is_instance_admin === true;
  // Check if user is organization admin
  const isOrgAdmin = user?.role === 'admin' || user?.organization_role === 'admin';
  const isNavigatingRef = useRef(false);
  const lastNavigatedPathRef = useRef<string | null>(null);
  const visibleMainAppsRef = useRef<typeof mainApps>([]);
  const visibleSidebarAppsRef = useRef<typeof sidebarApps>([]);

  // Filter apps based on permissions
  const visibleMainApps = useMemo(() => {
    return mainApps.filter((app) => {
      if (!app.requiredPermission && !app.requiredPermissions) {
        return true; // No permission required
      }
      
      if (app.requiredPermission) {
        return hasPermission(app.requiredPermission);
      }
      
      if (app.requiredPermissions) {
        if (app.requireAll) {
          return hasAllPermissions(app.requiredPermissions);
        } else {
          return hasAnyPermission(app.requiredPermissions);
        }
      }
      
      return false;
    });
  }, [hasPermission, hasAnyPermission, hasAllPermissions]);

  const visibleSidebarApps = useMemo(() => {
    return sidebarApps.filter((app) => {
      // Instance admin only apps
      if (app.isInstanceAdminOnly && !isInstanceAdmin) {
        return false;
      }

      // Admins (org or instance) can always access non-instance-admin-only apps.
      if (isInstanceAdmin || isOrgAdmin) {
        return true;
      }
      
      // Permission checks
      if (app.requiredPermission && !hasPermission(app.requiredPermission)) {
        return false;
      }
      if (app.requiredPermissions) {
        if (app.requireAll) {
          if (!hasAllPermissions(app.requiredPermissions)) {
            return false;
          }
        } else {
          if (!app.requiredPermissions.some(p => hasPermission(p))) {
            return false;
          }
        }
      }
      
      // Subscription tier check
      const tierLevels = { free: 0, pro: 1, premium: 2, lifetime: 3 };
      const userTier = user?.subscription_tier || 'free';
      if (tierLevels[userTier] < tierLevels[app.subscriptionTier || 'free']) {
        return false;
      }
      
      return true;
    });
  }, [hasPermission, hasAnyPermission, hasAllPermissions, user, isInstanceAdmin, isOrgAdmin]);

  // Keep refs in sync with current values
  useEffect(() => {
    visibleMainAppsRef.current = visibleMainApps;
    visibleSidebarAppsRef.current = visibleSidebarApps;
  }, [visibleMainApps, visibleSidebarApps]);

  // Helper function to check if user has permission for an app
  const hasPermissionForApp = useCallback((appId: AppView): boolean => {
    const allApps = [...mainApps, ...sidebarApps];
    const appConfig = allApps.find(a => a.id === appId);
    if (!appConfig) {
      return false;
    }

    // Instance-admin-only apps require instance admin.
    if (appConfig.isInstanceAdminOnly && !isInstanceAdmin) {
      return false;
    }

    // Admins (org or instance) can access all non-instance-admin-only apps.
    if (isInstanceAdmin || isOrgAdmin) {
      return true;
    }
    
    if (!appConfig.requiredPermission && !appConfig.requiredPermissions) {
      return true; // No permission required
    }
    
    let hasPerm = false;
    if (appConfig.requiredPermission) {
      hasPerm = hasPermission(appConfig.requiredPermission);
      return hasPerm;
    }
    
    if (appConfig.requiredPermissions) {
      if (appConfig.requireAll) {
        hasPerm = hasAllPermissions(appConfig.requiredPermissions);
      } else {
        hasPerm = hasAnyPermission(appConfig.requiredPermissions);
      }
      return hasPerm;
    }
    
    return false;
  }, [hasPermission, hasAnyPermission, hasAllPermissions, isInstanceAdmin, isOrgAdmin]);

  // Sync activeApp with route
  useEffect(() => {
    // Skip if pathname hasn't actually changed (prevents unnecessary re-runs)
    if (location.pathname === previousPathnameRef.current) {
      return;
    }
    
    // Update ref to track previous pathname
    previousPathnameRef.current = location.pathname;
    
    const pathToApp: Record<string, AppView> = {
      '/dashboard': 'dashboard',
      '/dashboard/applications': 'applications',
      '/dashboard/admin-signups': 'admin-signups',
      '/dashboard/calendar': 'calendar',
      '/dashboard/deals': 'deals',
      '/app/document-parser': 'document-parser',
      '/app/document-generator': 'document-generator',
      '/app/trade-blotter': 'trade-blotter',
      '/app/trading': 'trading',
      '/app/link-accounts': 'link-accounts',
      '/app/asset-alerts': 'asset-alerts',
      '/app/portfolio-risk': 'portfolio-risk',
      '/app/polymarket': 'polymarket',
      '/app/newsfeed': 'newsfeed',
      '/app/bank-products': 'bank-products',
      '/app/bridge': 'bridge',
      '/app/green-lens': 'green-lens',
      '/app/ground-truth': 'ground-truth',
      '/app/verification-demo': 'verification-demo',
      '/app/demo-data': 'demo-data',
      '/app/risk-war-room': 'risk-war-room',
      '/app/policy-editor': 'policy-editor',
      '/app/verification-config': 'verification-config',
      '/app/whitelisting-dashboard': 'whitelisting-dashboard',
      '/app/agent-dashboard': 'agent-dashboard',
      '/app/loan-recovery': 'loan-recovery',
      '/library': 'library',
      '/auditor': 'auditor',
      '/settings': 'settings',
      '/admin-settings': 'admin-settings',
    };
    
    // Get base pathname (without query parameters)
    const basePathname = location.pathname.split('?')[0];

    // Legacy dashboard tab URLs: redirect to real app routes.
    // This ensures old tab-style nav still works (and updates URL).
    if (basePathname === '/dashboard' && location.search) {
      const params = new URLSearchParams(location.search);
      const tab = params.get('tab');
      const tabRedirects: Record<string, string> = {
        trading: '/app/trading',
        polymarket: '/app/polymarket',
        bridge: '/app/bridge',
        applications: '/dashboard/applications',
      };
      const redirectTo = tab ? tabRedirects[tab] : undefined;
      if (redirectTo && redirectTo !== location.pathname) {
        isNavigatingRef.current = true;
        lastNavigatedPathRef.current = redirectTo;
        navigate(redirectTo, { replace: true });
        return;
      }
    }
    
    // Handle policy-editor routes with policyId parameter
    let app = pathToApp[basePathname];
    if (!app && basePathname.startsWith('/app/policy-editor')) {
      app = 'policy-editor';
    }
    // Handle routes that start with /app/ (for query parameters) - use basePathname
    if (!app && basePathname.startsWith('/app/')) {
      app = pathToApp[basePathname];
    }
    // Handle deal detail routes (must come after checking exact path)
    // IMPORTANT: Check for deal detail routes BEFORE checking exact path matches
    if (!app && basePathname.startsWith('/dashboard/deals/') && basePathname !== '/dashboard/deals') {
      app = 'deals';  // Set app to 'deals' but don't navigate away from detail page
    }
    // Handle auditor routes
    if (!app && basePathname.startsWith('/auditor')) {
      app = 'auditor';
    }
    // Handle securitization routes (pool detail, tranche purchase)
    if (!app && basePathname.startsWith('/app/securitization')) {
      app = 'securitization';
    }
    
    // Only sync if the pathname is actually in our mapping (not a route we don't handle)
    if (!app) {
      return; // Don't update activeApp if pathname doesn't map to an app
    }
    
    // CRITICAL: Skip sync only if we're still navigating AND haven't reached the target path yet
    // This allows sync to proceed once we've reached the target path
    if (isNavigatingRef.current && lastNavigatedPathRef.current) {
      const targetBasePath = lastNavigatedPathRef.current.split('?')[0];
      if (basePathname !== targetBasePath) {
        return; // Still navigating to target, don't sync yet
      }
      // We've reached the target path, clear the flag and proceed with sync
      // Clear flags BEFORE proceeding with sync to avoid race conditions
      isNavigatingRef.current = false;
      lastNavigatedPathRef.current = null;
    }
    
    // CRITICAL: Check permissions before syncing - redirect to dashboard if user doesn't have permission
    const hasPerm = hasPermissionForApp(app);
    if (!hasPerm) {
      if (location.pathname !== '/dashboard') {
        isNavigatingRef.current = true;
        lastNavigatedPathRef.current = '/dashboard';
        navigate('/dashboard', { replace: true });
      }
      if (activeApp !== 'dashboard') {
        setActiveApp('dashboard');
      }
      return;
    }
    
    // CRITICAL: If we're on a route with query parameters that matches the app, just update activeApp
    // This prevents redirects when navigating to routes with query parameters
    if (location.pathname.includes('?') && basePathname in pathToApp && pathToApp[basePathname] === app) {
      // We're on a route with query parameters that matches the app - just update activeApp without navigation
      if (app !== activeApp) {
        setActiveApp(app);
      }
      return; // Don't proceed with normal sync logic
    }
    
    // Only update if different to avoid unnecessary re-renders and potential loops
    // CRITICAL: Don't trigger navigation when on a deal detail page
    if (app !== activeApp) {
      // CRITICAL: Check if app is in visible apps before setting (permission check)
      // Use refs to avoid dependency on visibleMainApps/visibleSidebarApps which change on re-render
      const allVisibleApps = [...visibleMainAppsRef.current, ...visibleSidebarAppsRef.current];
      const isAppVisible = allVisibleApps.some(visibleApp => visibleApp.id === app);
      if (!isAppVisible) {
        if (location.pathname !== '/dashboard') {
          isNavigatingRef.current = true;
          lastNavigatedPathRef.current = '/dashboard';
          navigate('/dashboard', { replace: true });
        }
        if (activeApp !== 'dashboard') {
          setActiveApp('dashboard');
        }
        return;
      }
      // CRITICAL: Use functional update to ensure we're using the latest state
      setActiveApp((_prevApp) => { // Prefix with _ - unused
        return app;
      });
    }
  }, [location.pathname, navigate, activeApp, hasPermissionForApp]); // CRITICAL: Include activeApp and hasPermissionForApp since they're used in the effect

  // Update route when activeApp changes
  const handleAppChange = (app: AppView) => {
    // Save current tab state before switching apps
    if (typeof window !== 'undefined' && activeApp) {
      const currentUrl = new URL(window.location.href);
      const tabParam = currentUrl.searchParams.get('tab');
      if (tabParam) {
        sessionStorage.setItem(`creditnexus_${activeApp}_tab`, tabParam);
      }
    }
    
    // CRITICAL: Check permissions before navigating - redirect to dashboard if user doesn't have permission
    if (!hasPermissionForApp(app)) {
      if (location.pathname !== '/dashboard') {
        isNavigatingRef.current = true;
        lastNavigatedPathRef.current = '/dashboard';
        navigate('/dashboard', { replace: true });
      }
      if (activeApp !== 'dashboard') {
        setActiveApp('dashboard');
      }
      return;
    }
    
    // Don't navigate if we're on a deal detail route and trying to go to deals list
    // This prevents redirecting away from deal detail pages
    if (app === 'deals' && location.pathname.startsWith('/dashboard/deals/') && location.pathname !== '/dashboard/deals') {
      return; // Stay on the detail page
    }
    
    // Save current tab state before switching apps
    if (typeof window !== 'undefined' && activeApp) {
      const currentUrl = new URL(window.location.href);
      const tabParam = currentUrl.searchParams.get('tab');
      if (tabParam) {
        sessionStorage.setItem(`creditnexus_${activeApp}_tab`, tabParam);
      }
    }
    
    // Find app config to get path
    const allApps = [...mainApps, ...sidebarApps];
    const appConfig = allApps.find(a => a.id === app);
    const path = appConfig?.path;
    
    // Restore tab state for the new app if available
    const savedTab = typeof window !== 'undefined' ? sessionStorage.getItem(`creditnexus_${app}_tab`) : null;
    
    // Build target path with tab parameter if saved tab exists
    let targetPath = path || '';
    if (savedTab && targetPath) {
      const url = new URL(targetPath, window.location.origin);
      url.searchParams.set('tab', savedTab);
      targetPath = url.pathname + url.search;
    }
    
    // CRITICAL: Don't navigate if we're already on the correct base path (even with query params)
    // This prevents redirects when navigating to routes with query parameters
    const currentBasePath = location.pathname.split('?')[0];
    if (path && path === currentBasePath) {
      // We're already on the correct route (possibly with query params) - just update activeApp
      // But restore tab if we have a saved tab and it's not in the URL
      if (savedTab && !location.search.includes('tab=')) {
        const url = new URL(window.location.href);
        url.searchParams.set('tab', savedTab);
        navigate(url.pathname + url.search, { replace: true });
      }
      if (app !== activeApp) {
        setActiveApp(app);
      }
      return; // Don't navigate
    }
    
    // Use targetPath if we have tab restoration, otherwise use path
    const finalPath = targetPath || path;
    
    if (finalPath && finalPath.split('?')[0] !== location.pathname) {
      // CRITICAL FIX: Set activeApp BEFORE navigating to ensure UI updates immediately
      // This fixes the issue where the sync effect was skipping due to ref timing
      setActiveApp(app);
      
      isNavigatingRef.current = true;
      lastNavigatedPathRef.current = finalPath;
      navigate(finalPath, { replace: false });
      // Flags will be cleared by the useEffect when the route changes
    }
  };

  const processIntent = (intent: IntentName, context: unknown) => {
    switch (intent) {
      case 'GenerateLMATemplate': {
        const cdmData = context as CreditAgreementData;
        if (cdmData) {
          setViewData(cdmData);
          handleAppChange('document-generator');
        }
        break;
      }
      case 'ViewLoanAgreement': {
        const agreementCtx = context as AgreementContext;
        if (agreementCtx.id?.agreementId) {
          const agreementData: CreditAgreementData = {
            deal_id: agreementCtx.id.agreementId,
            agreement_date: agreementCtx.agreementDate,
            parties: agreementCtx.parties,
            facilities: agreementCtx.facilities,
          };
          setViewData(agreementData);
          handleAppChange('library');
        }
        break;
      }
      case 'ApproveLoanAgreement': {
        const approvalCtx = context as AgreementContext;
        if (approvalCtx.id?.agreementId) {
          const agreementData: CreditAgreementData = {
            deal_id: approvalCtx.id.agreementId,
            agreement_date: approvalCtx.agreementDate,
            parties: approvalCtx.parties,
            facilities: approvalCtx.facilities,
          };
          setViewData(agreementData);
          handleAppChange('library');
        }
        break;
      }
      case 'ViewESGAnalytics': {
        handleAppChange('green-lens');
        break;
      }
      case 'ExtractCreditAgreement': {
        const docCtx = context as DocumentContext;
        if (docCtx.content) {
          setExtractionContent(docCtx.content);
          handleAppChange('document-parser');
        }
        break;
      }
      case 'ViewPortfolio': {
        handleAppChange('dashboard');
        break;
      }
      case 'ShareWorkflowLink': {
        const workflowCtx = context as WorkflowLinkContext;
        if (workflowCtx && workflowCtx.linkPayload) {
          // Will be handled by the workflow share interface.
        }
        break;
      }
      case 'ProcessWorkflowLink': {
        const workflowCtx = context as WorkflowLinkContext;
        if (workflowCtx && workflowCtx.linkPayload) {
          // Navigate to workflow processing page
          navigate(`/app/workflow/process?payload=${encodeURIComponent(workflowCtx.linkPayload)}`);
          handleAppChange('workflow-processor' as AppView);
        }
        break;
      }
      default:
        // ignore unknown intents
    }
  };

  useEffect(() => {
    onIntentReceived((intent, context) => {
      processIntent(intent, context);
    });
  }, [onIntentReceived]);

  useEffect(() => {
    if (pendingIntent) {
      const { intent, context } = pendingIntent;
      clearPendingIntent();
      processIntent(intent, context);
    }
  }, [pendingIntent, clearPendingIntent]);

  useEffect(() => {
    const handleNavigate = (event: CustomEvent) => {
      const app = (event.detail as { app?: AppView })?.app;
      if (app) {
        handleAppChange(app);
      }
    };

    window.addEventListener('navigateToApp', handleNavigate as EventListener);
    return () => {
      window.removeEventListener('navigateToApp', handleNavigate as EventListener);
    };
  }, []);

  const handleBroadcast = () => {
    setHasBroadcast(true);
  };

  const handleViewData = (data: Record<string, unknown>) => {
    setViewData(data as CreditAgreementData);
    handleAppChange('document-parser');
  };

  const handleSaveToLibrary = () => {
    setExtractionContent(null);
  };

  const breadcrumbItems = useMemo(() => {
    const currentApp = [...visibleMainApps, ...visibleSidebarApps].find(app => app.id === activeApp);
    if (!currentApp) return [];

    return [
      {
        label: currentApp.name,
        icon: currentApp.icon
      }
    ];
  }, [activeApp, visibleMainApps, visibleSidebarApps]);

  const handleBreadcrumbHome = () => {
    handleAppChange('dashboard');
  };

  // Listen for quick-access mode changes and route to the
  // appropriate app instead of using nested dashboard tabs.
  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<QuickAccessPreferences>).detail;
      if (!detail) return;

      const targetApp = pickAppFromPreferences(detail);
      if (!targetApp) return;
      handleAppChange(targetApp);
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('userPreferencesUpdated', handler as EventListener);
      return () => {
        window.removeEventListener('userPreferencesUpdated', handler as EventListener);
      };
    }
  }, [handleAppChange]);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <header className="sticky top-0 z-50 border-b border-slate-700 bg-slate-900/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">CreditNexus</h1>
              <p className="text-xs text-slate-400">FINOS CDM Compliant</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <QuickAccessSettings variant="inline" />
            <ThemeToggle />

            <div className="flex items-center gap-2 text-sm text-slate-400" title={isAvailable ? 'FDC3 Desktop Agent Connected' : 'FDC3 Mock Mode (No Desktop Agent)'}>
              <Radio className={`h-4 w-4 ${isAvailable ? 'text-emerald-500' : 'text-slate-500'}`} />
              <span className="hidden sm:inline">FDC3</span>
              {isAvailable && (
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
              )}
            </div>

            {isLoading ? (
              <div className="flex items-center gap-2 text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            ) : isAuthenticated && user ? (
              <>
                <button
                  type="button"
                  onClick={() => setSupportChatOpen(true)}
                  className="flex items-center justify-center w-9 h-9 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
                  aria-label="Customer service"
                  title="Customer service"
                >
                  <Headphones className="h-5 w-5" />
                </button>
                <UserMenu />
              </>
            ) : (
              <button
                onClick={() => navigate('/login')}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <LogIn className="h-4 w-4" />
                <span>Log in</span>
              </button>
            )}
          </div>
        </div>
      </header>

      <LoginForm isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} />

      {/* Customer service modal (placeholder) – top-right entry */}
      <Dialog open={supportChatOpen} onOpenChange={setSupportChatOpen}>
        <DialogContent className="max-w-sm p-6 bg-slate-800 border-slate-700" onClose={() => setSupportChatOpen(false)}>
          <div className="flex items-center gap-3 text-slate-300">
            <Headphones className="h-8 w-8 text-emerald-500" />
            <div>
              <h3 className="font-semibold text-slate-100">Customer service</h3>
              <p className="text-sm text-slate-400 mt-1">Live support and help – coming soon.</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <div className="flex flex-1 overflow-hidden">
        <SidebarNavigation />

        <main className="flex-1 max-w-6xl mx-auto px-6 py-8 overflow-y-auto">
          <BreadcrumbContainer>
            <Breadcrumb
              items={breadcrumbItems}
              onHomeClick={handleBreadcrumbHome}
            />
          </BreadcrumbContainer>

          {activeApp === 'dashboard' && <UnifiedDashboard />}
          {activeApp === 'applications' && <ApplicationDashboard />}
          {activeApp === 'admin-signups' && <AdminSignupDashboard />}
          {activeApp === 'calendar' && <CalendarView />}
          {activeApp === 'deals' && (() => {
            const isDetailRoute = location.pathname.startsWith('/dashboard/deals/') && location.pathname !== '/dashboard/deals';
            return isDetailRoute ? <DealDetail /> : <DealDashboard />;
          })()}
          {activeApp === 'document-parser' && (
            <DocumentParser
              onBroadcast={handleBroadcast}
              onSaveToLibrary={handleSaveToLibrary}
              onGenerateFromTemplate={(data) => {
                setViewData(data);
                handleAppChange('document-generator');
              }}
              initialData={viewData}
              initialContent={extractionContent}
            />
          )}
          {activeApp === 'library' && (
            <DocumentHistory 
              onViewData={handleViewData} 
              onGenerateFromTemplate={(cdmData: Record<string, unknown>) => {
                setViewData(cdmData as CreditAgreementData);
                handleAppChange('document-generator');
              }}
            />
          )}
          {activeApp === 'trade-blotter' && (
            <TradeBlotter
              state={tradeBlotterState}
              setState={setTradeBlotterState}
            />
          )}
          {activeApp === 'link-accounts' && <LinkAccounts />}
          {activeApp === 'asset-alerts' && <AssetAlertsView />}
          {activeApp === 'portfolio-risk' && <PortfolioRiskView />}
          {activeApp === 'trading' && <TradingDashboard />}
          {activeApp === 'newsfeed' && <Newsfeed />}
          {activeApp === 'bank-products' && <BankProductsMarketplace />}
          {activeApp === 'polymarket' && (() => {
            const tab = new URLSearchParams(location.search).get('tab') || 'markets';
            return (
              <div className="h-full flex flex-col">
                <div className="flex gap-1 border-b border-border/50 px-2 py-1 shrink-0">
                  <Button
                    variant={tab === 'markets' ? 'secondary' : 'ghost'}
                    size="sm"
                    asChild
                  >
                    <Link to="/app/polymarket?tab=markets">Markets</Link>
                  </Button>
                  <Button
                    variant={tab === 'trading' ? 'secondary' : 'ghost'}
                    size="sm"
                    asChild
                  >
                    <Link to="/app/polymarket?tab=trading">Trading</Link>
                  </Button>
                  <Button
                    variant={tab === 'funding' ? 'secondary' : 'ghost'}
                    size="sm"
                    asChild
                  >
                    <Link to="/app/polymarket?tab=funding">Funding</Link>
                  </Button>
                </div>
                <div className="flex-1 min-h-0 overflow-auto">
                  {tab === 'markets' && <MarketDashboard />}
                  {tab === 'trading' && <PolymarketTrading />}
                  {tab === 'funding' && <PolymarketFunding />}
                </div>
              </div>
            );
          })()}
          {activeApp === 'bridge' && <BridgeBuilder />}
          {activeApp === 'green-lens' && <GreenLens />}
          {activeApp === 'document-generator' && (
            <DocumentGenerator
              initialCdmData={viewData || undefined}
              onDocumentGenerated={(doc) => {
                void doc;
              }}
            />
          )}
          {activeApp === 'ground-truth' && <GroundTruthDashboard />}
          {activeApp === 'verification-demo' && <VerificationDashboard />}
          {activeApp === 'demo-data' && <DemoDataDashboard />}
          {activeApp === 'risk-war-room' && <RiskWarRoom />}
          {activeApp === 'policy-editor' && <PolicyEditor />}
          {activeApp === 'verification-config' && <VerificationFileConfigEditor />}
          {activeApp === 'whitelisting-dashboard' && <WhitelistingDashboard />}
          {activeApp === 'workflow-share' && <WorkflowShareInterface />}
          {activeApp === 'workflow-processor' && <WorkflowProcessingPage />}
          {activeApp === 'auditor' && <AuditorRouter />}
          {activeApp === 'loan-recovery' && (
            <div className="h-full">
              <LoanRecoverySidebar />
            </div>
          )}
          {activeApp === 'agent-dashboard' && <AgentDashboard />}
          {activeApp === 'filings' && <FilingStatusDashboard />}
          {activeApp === 'billing' && <BillingDashboard />}
          {activeApp === 'securitization' && (() => {
            // Check if we're on a tranche purchase page
            if (location.pathname.includes('/tranches/') && location.pathname.includes('/purchase')) {
              const poolIdMatch = location.pathname.match(/\/pools\/([^/]+)/);
              const trancheIdMatch = location.pathname.match(/\/tranches\/([^/]+)/);
              if (poolIdMatch && trancheIdMatch) {
                return <TranchePurchase poolId={poolIdMatch[1]} trancheId={trancheIdMatch[1]} />;
              }
            }
            // Check if we're on a pool detail page
            if (location.pathname.startsWith('/app/securitization/pools/')) {
              return <SecuritizationPoolDetail />;
            }
            // Default to workflow
            return <SecuritizationWorkflow />;
          })()}
          {activeApp === 'settings' && <UserSettings />}
          {activeApp === 'admin-settings' && <AdminSettings />}
        </main>
      </div>

      {/* Global chatbot: circular button bottom-right, single assistant for all apps */}
      {isAuthenticated && (
        <>
          <button
            type="button"
            onClick={() => setGlobalChatOpen((v) => !v)}
            className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full shadow-lg bg-emerald-600 hover:bg-emerald-700 text-white border-0 transition-all duration-200 hover:scale-110 active:scale-95 flex items-center justify-center"
            aria-label={globalChatOpen ? 'Close assistant' : 'Open assistant'}
            title={globalChatOpen ? 'Close assistant' : 'Open assistant'}
          >
            <MessageSquare className="h-6 w-6" />
          </button>
          <Dialog open={globalChatOpen} onOpenChange={setGlobalChatOpen}>
            <DialogContent className="max-w-2xl max-h-[85vh] p-0 overflow-hidden bg-slate-800 border-slate-700" onClose={() => setGlobalChatOpen(false)}>
              <div className="h-[75vh] min-h-[320px]">
                <DashboardChatbotPanel className="h-full" />
              </div>
            </DialogContent>
          </Dialog>
        </>
      )}

      <CookieBanner />

      <footer className={`border-t ${classes.border.default} mt-auto`}>
        <div className={`max-w-7xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm ${classes.text.secondary}`}>
          <p>Price & create structured financial products</p>
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                // Get current context (dealId, documentId) from URL or FDC3
                const currentPath = location.pathname
                let shareUrl = '/app/workflow/share?view=dashboard'
                
                // Try to extract dealId or documentId from current route
                const dealMatch = currentPath.match(/\/deals\/(\d+)/)
                const docMatch = currentPath.match(/\/documents\/(\d+)/)
                
                if (dealMatch) {
                  shareUrl = `/app/workflow/share?view=create&dealId=${dealMatch[1]}`
                } else if (docMatch) {
                  shareUrl = `/app/workflow/share?view=create&documentId=${docMatch[1]}`
                }
                
                navigate(shareUrl, { 
                  state: { from: currentPath } 
                })
                handleAppChange('workflow-share' as AppView)
              }}
              className={`${classes.text.secondary} ${classes.interactive.hover.text} ${classes.interactive.hover.background}`}
              title="Open Workflow Share Interface"
            >
              <Share2 className="h-4 w-4 mr-2" />
              Workflow Links
            </Button>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Radio className="h-3 w-3 text-emerald-500" />
                FDC3 Desktop Interoperability
              </span>
              <span>FINOS CDM Compliant</span>
              <div className="flex items-center gap-2 ml-2 pl-2 border-l border-slate-600">
                <Link 
                  to="/license" 
                  className={`text-xs ${classes.text.muted} ${classes.interactive.hover.text} transition-colors`}
                >
                  License
                </Link>
                <span className={classes.text.muted}>•</span>
                <Link 
                  to="/rail" 
                  className={`text-xs ${classes.text.muted} ${classes.interactive.hover.text} transition-colors`}
                >
                  RAIL
                </Link>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
