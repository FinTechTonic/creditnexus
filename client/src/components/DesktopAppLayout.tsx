import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { DocumentParser } from '@/apps/docu-digitizer/DocumentParser';
import { TradeBlotter } from '@/apps/trade-blotter/TradeBlotter';
import { GreenLens } from '@/apps/green-lens/GreenLens';
import { DocumentGenerator } from '@/apps/document-generator/DocumentGenerator';
import { PolicyEditor } from '@/apps/policy-editor/PolicyEditor';
import { DocumentHistory } from '@/components/DocumentHistory';
import { Dashboard } from '@/components/Dashboard';
import { GroundTruthDashboard } from '@/components/GroundTruthDashboard';
import { ApplicationDashboard } from '@/components/ApplicationDashboard';
import { AdminSignupDashboard } from '@/components/AdminSignupDashboard';
import { CalendarView } from '@/components/CalendarView';
import { DealDashboard } from '@/components/DealDashboard';
import { DealDetail } from '@/components/DealDetail';
import { LoginForm } from '@/components/LoginForm';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { Breadcrumb, BreadcrumbContainer } from '@/components/ui/Breadcrumb';
import { FileText, ArrowLeftRight, Leaf, Sparkles, Radio, LogIn, LogOut, User, Loader2, BookOpen, LayoutDashboard, ChevronLeft, ChevronRight, Shield, RadioTower, Building2, Database } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useFDC3 } from '@/context/FDC3Context';
import type { CreditAgreementData, IntentName, DocumentContext, AgreementContext } from '@/context/FDC3Context';
import VerificationDashboard from '@/components/VerificationDashboard';
import { DemoDataDashboard } from '@/components/DemoDataDashboard';
import RiskWarRoom from '@/components/RiskWarRoom';
import { usePermissions } from '@/hooks/usePermissions';
import {
  PERMISSION_DOCUMENT_VIEW,
  PERMISSION_DOCUMENT_CREATE,
  PERMISSION_TEMPLATE_VIEW,
  PERMISSION_TEMPLATE_GENERATE,
  PERMISSION_TRADE_VIEW,
  PERMISSION_SATELLITE_VIEW,
  PERMISSION_APPLICATION_VIEW,
  PERMISSION_USER_VIEW,
  PERMISSION_DEAL_VIEW,
  PERMISSION_DEAL_VIEW_OWN,
} from '@/utils/permissions';

type AppView = 'dashboard' | 'document-parser' | 'trade-blotter' | 'green-lens' | 'library' | 'ground-truth' | 'verification-demo' | 'demo-data' | 'risk-war-room' | 'document-generator' | 'applications' | 'calendar' | 'admin-signups' | 'policy-editor' | 'deals';

interface AppConfig {
  id: AppView;
  name: string;
  icon: React.ReactNode;
  description: string;
  requiredPermission?: string;
  requiredPermissions?: string[];
  requireAll?: boolean;
}

const mainApps: AppConfig[] = [
  {
    id: 'dashboard',
    name: 'Dashboard',
    icon: <LayoutDashboard className="h-5 w-5" />,
    description: 'Portfolio overview & analytics',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
  },
  {
    id: 'document-parser',
    name: 'Document Parser',
    icon: <FileText className="h-5 w-5" />,
    description: 'Extract & digitize credit agreements',
    requiredPermission: PERMISSION_DOCUMENT_CREATE,
  },
  {
    id: 'library',
    name: 'Library',
    icon: <BookOpen className="h-5 w-5" />,
    description: 'Saved documents & history',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
  },
  {
    id: 'document-generator',
    name: 'Document Generator',
    icon: <Sparkles className="h-5 w-5" />,
    description: 'Generate LMA documents from templates',
    requiredPermissions: [PERMISSION_TEMPLATE_VIEW, PERMISSION_TEMPLATE_GENERATE],
    requireAll: false,
  },
];

const sidebarApps: AppConfig[] = [
  {
    id: 'demo-data',
    name: 'Demo Data',
    icon: <Database className="h-5 w-5 text-indigo-400" />,
    description: 'Seed and manage demo data',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
  },
  {
    id: 'verification-demo',
    name: 'Verification Demo',
    icon: <Sparkles className="h-5 w-5 text-indigo-400" />,
    description: 'Live Verification Workflow',
    requiredPermission: PERMISSION_SATELLITE_VIEW,
  },
  {
    id: 'ground-truth',
    name: 'Ground Truth',
    icon: <Shield className="h-5 w-5" />,
    description: 'Geospatial verification for sustainability-linked loans',
    requiredPermission: PERMISSION_SATELLITE_VIEW,
  },
  {
    id: 'trade-blotter',
    name: 'Trade Blotter',
    icon: <ArrowLeftRight className="h-5 w-5" />,
    description: 'LMA trade confirmation & settlement',
    requiredPermission: PERMISSION_TRADE_VIEW,
  },
  {
    id: 'risk-war-room',
    name: 'Risk War Room',
    icon: <RadioTower className="h-5 w-5 text-red-500" />,
    description: 'Global Portfolio Surveillance',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
  },
  {
    id: 'green-lens',
    name: 'GreenLens',
    icon: <Leaf className="h-5 w-5" />,
    description: 'ESG performance & margin ratchet',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
  },
  {
    id: 'policy-editor',
    name: 'Policy Editor',
    icon: <Shield className="h-5 w-5 text-purple-400" />,
    description: 'Create and manage policy rules',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
  },
  {
    id: 'admin-signups',
    name: 'User Signups',
    icon: <User className="h-5 w-5 text-blue-400" />,
    description: 'Review platform user account signups (admin only)',
    requiredPermission: PERMISSION_USER_VIEW,
  },
  {
    id: 'deals',
    name: 'Deals',
    icon: <Building2 className="h-5 w-5 text-emerald-400" />,
    description: 'Deal management & lifecycle',
    requiredPermissions: [PERMISSION_DEAL_VIEW, PERMISSION_DEAL_VIEW_OWN],
    requireAll: false,
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

export function DesktopAppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Track component instance to detect re-mounts
  const componentInstanceRef = useRef<string>(Math.random().toString(36).substring(7));
  const mountCountRef = useRef(0);
  const previousPathnameRef = useRef<string>(location.pathname);
  
  // Track unexpected route changes
  // NOTE: This useEffect is moved after activeApp declaration to avoid TDZ error
  
  // Initialize activeApp from current route to avoid mismatches
  // CRITICAL: Persist activeApp in sessionStorage to survive component re-mounts
  const getInitialApp = (): AppView => {
    // Valid app names for validation
    const validApps: AppView[] = [
      'dashboard', 'applications', 'admin-signups', 'calendar', 'deals',
      'document-parser', 'document-generator', 'trade-blotter', 'green-lens',
      'ground-truth', 'verification-demo', 'demo-data', 'risk-war-room',
      'policy-editor', 'library'
    ];
    
    // Try to restore from sessionStorage first
    if (typeof window !== 'undefined') {
      const persisted = sessionStorage.getItem('creditnexus_activeApp');
      if (persisted && validApps.includes(persisted as AppView)) {
        return persisted as AppView;
      }
    }
    
    // Fall back to route-based detection
    const pathToApp: Record<string, AppView> = {
      '/dashboard': 'dashboard',
      '/dashboard/applications': 'applications',
      '/dashboard/admin-signups': 'admin-signups',
      '/dashboard/calendar': 'calendar',
      '/dashboard/deals': 'deals',
      '/app/document-parser': 'document-parser',
      '/app/document-generator': 'document-generator',
      '/app/trade-blotter': 'trade-blotter',
      '/app/green-lens': 'green-lens',
      '/app/ground-truth': 'ground-truth',
      '/app/verification-demo': 'verification-demo',
      '/app/demo-data': 'demo-data',
      '/app/risk-war-room': 'risk-war-room',
      '/app/policy-editor': 'policy-editor',
      '/library': 'library',
    };
    // Handle policy-editor routes with policyId parameter
    if (location.pathname.startsWith('/app/policy-editor')) {
      return 'policy-editor';
    }
    // Handle deal detail routes
    if (location.pathname.startsWith('/dashboard/deals/')) {
      return 'deals';
    }
    const result = pathToApp[location.pathname] || 'dashboard';
    return result;
  };
  
  const [activeAppState, setActiveAppState] = useState<AppView>(getInitialApp());
  
  // Wrap setActiveApp to persist to sessionStorage
  const setActiveApp = useCallback((value: AppView | ((prev: AppView) => AppView)) => {
    setActiveAppState((prev) => {
      const newValue = typeof value === 'function' ? value(prev) : value;
      // Persist to sessionStorage
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('creditnexus_activeApp', newValue);
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
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const { isAvailable, pendingIntent, clearPendingIntent, onIntentReceived } = useFDC3();
  const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermissions();
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
  }, [hasPermission, hasAnyPermission, hasAllPermissions]);

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
      '/dashboard/deals': 'deals',  // Add explicit mapping for deals list
      '/app/document-parser': 'document-parser',
      '/app/document-generator': 'document-generator',
      '/app/trade-blotter': 'trade-blotter',
      '/app/green-lens': 'green-lens',
      '/app/ground-truth': 'ground-truth',
      '/app/verification-demo': 'verification-demo',
      '/app/demo-data': 'demo-data',
      '/app/risk-war-room': 'risk-war-room',
      '/app/policy-editor': 'policy-editor',
      '/library': 'library',
    };
    
    // Get base pathname (without query parameters)
    const basePathname = location.pathname.split('?')[0];
    
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
      setActiveApp((prevApp) => {
        return app;
      });
    }
  }, [location.pathname, navigate, activeApp, hasPermissionForApp]); // CRITICAL: Include activeApp and hasPermissionForApp since they're used in the effect

  // Update route when activeApp changes
  const handleAppChange = (app: AppView) => {
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
    
    const appToPath: Record<AppView, string> = {
      'dashboard': '/dashboard',
      'applications': '/dashboard/applications',
      'admin-signups': '/dashboard/admin-signups',
      'calendar': '/dashboard/calendar',
      'deals': '/dashboard/deals',
      'document-parser': '/app/document-parser',
      'document-generator': '/app/document-generator',
      'trade-blotter': '/app/trade-blotter',
      'green-lens': '/app/green-lens',
      'ground-truth': '/app/ground-truth',
      'verification-demo': '/app/verification-demo',
      'demo-data': '/app/demo-data',
      'risk-war-room': '/app/risk-war-room',
      'policy-editor': '/app/policy-editor',
      'library': '/library',
    };
    const path = appToPath[app];
    
    // CRITICAL: Don't navigate if we're already on the correct base path (even with query params)
    // This prevents redirects when navigating to routes with query parameters
    const currentBasePath = location.pathname.split('?')[0];
    if (path && path === currentBasePath) {
      // We're already on the correct route (possibly with query params) - just update activeApp
      if (app !== activeApp) {
        setActiveApp(app);
      }
      return; // Don't navigate
    }
    
    if (path && path !== location.pathname) {
      // CRITICAL FIX: Set activeApp BEFORE navigating to ensure UI updates immediately
      // This fixes the issue where the sync effect was skipping due to ref timing
      setActiveApp(app);
      
      isNavigatingRef.current = true;
      lastNavigatedPathRef.current = path;
      navigate(path, { replace: false });
      // Flags will be cleared by the useEffect when the route changes
    }
  };

  const processIntent = (intent: IntentName, context: unknown) => {
    console.log('[DesktopAppLayout] Processing FDC3 intent:', intent, context);

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
      console.log('[DesktopAppLayout] Processing pending intent:', intent, context);
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

          <nav className="flex items-center gap-1 bg-slate-800 rounded-lg p-1">
            {visibleMainApps.map((app) => (
              <button
                key={app.id}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleAppChange(app.id);
                }}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${activeApp === app.id
                  ? 'bg-emerald-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
                  }`}
              >
                {app.icon}
                <span className="hidden md:inline">{app.name}</span>
                {app.id !== 'document-parser' && hasBroadcast && (
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                )}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-4">
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
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  {user.profile_image ? (
                    <img
                      src={user.profile_image}
                      alt={user.display_name}
                      className="w-8 h-8 rounded-full object-cover border-2 border-emerald-500"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center border-2 border-emerald-500">
                      <User className="h-4 w-4 text-slate-300" />
                    </div>
                  )}
                  <div className="hidden md:block">
                    <p className="text-sm font-medium text-slate-100">{user.display_name}</p>
                    <p className="text-xs text-slate-400 capitalize">{user.role}</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    logout();
                    navigate('/login');
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
                  title="Log out"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden lg:inline">Log out</span>
                </button>
              </div>
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

      <div className="flex flex-1">
        <aside className={`${sidebarOpen ? 'w-56' : 'w-14'} bg-slate-800/50 border-r border-slate-700 transition-all duration-200 flex-shrink-0`}>
          <div className="p-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="w-full flex items-center justify-center p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
              title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              {sidebarOpen ? <ChevronLeft className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
            </button>
          </div>
          <nav className="px-3 space-y-1">
            <p className={`text-xs text-slate-500 uppercase tracking-wider px-2 py-2 ${!sidebarOpen && 'sr-only'}`}>
              Tools
            </p>
            {visibleSidebarApps.map((app) => (
              <button
                key={app.id}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleAppChange(app.id);
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${activeApp === app.id
                  ? 'bg-emerald-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
                  }`}
                title={app.description}
              >
                {app.icon}
                {sidebarOpen && <span>{app.name}</span>}
                {hasBroadcast && (
                  <span className="relative flex h-2 w-2 ml-auto">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                )}
              </button>
            ))}
            <div className={`mt-4 pt-4 border-t border-slate-700 ${!sidebarOpen && 'hidden'}`}>
              <div className="flex items-center gap-2 px-2 py-2 text-sm text-slate-400" title={isAvailable ? 'FDC3 Desktop Agent Connected' : 'FDC3 Mock Mode'}>
                <Radio className={`h-4 w-4 ${isAvailable ? 'text-emerald-500' : 'text-slate-500'}`} />
                {sidebarOpen && <span>FDC3 {isAvailable ? 'Connected' : 'Mock'}</span>}
              </div>
            </div>
          </nav>
        </aside>

        <main className="flex-1 max-w-6xl mx-auto px-6 py-8">
          <BreadcrumbContainer>
            <Breadcrumb
              items={breadcrumbItems}
              onHomeClick={handleBreadcrumbHome}
            />
          </BreadcrumbContainer>

          {activeApp === 'dashboard' && <Dashboard />}
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
          {activeApp === 'green-lens' && <GreenLens />}
          {activeApp === 'document-generator' && (
            <DocumentGenerator
              initialCdmData={viewData || undefined}
              onDocumentGenerated={(doc) => {
                console.log('Document generated:', doc);
              }}
            />
          )}
          {activeApp === 'ground-truth' && <GroundTruthDashboard />}
          {activeApp === 'verification-demo' && <VerificationDashboard />}
          {activeApp === 'demo-data' && <DemoDataDashboard />}
          {activeApp === 'risk-war-room' && <RiskWarRoom />}
          {activeApp === 'policy-editor' && <PolicyEditor />}
        </main>
      </div>

      <footer className="border-t border-slate-700 mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-400">
          <p>Powered by OpenAI GPT-4o and LangChain</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <Radio className="h-3 w-3 text-emerald-500" />
              FDC3 Desktop Interoperability
            </span>
            <span>FINOS CDM Compliant</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
