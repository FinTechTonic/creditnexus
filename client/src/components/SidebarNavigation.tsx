import { useState, useMemo, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuth } from '@/context/AuthContext';
import { 
  ChevronLeft, 
  ChevronRight, 
  LayoutDashboard, 
  FileText, 
  TrendingUp, 
  BarChart3, 
  ArrowLeftRight, 
  PenTool, 
  Shield, 
  FileCheck, 
  DollarSign, 
  BookOpen, 
  Sparkles, 
  Leaf, 
  Database, 
  Building2, 
  AlertTriangle, 
  Link2, 
  Bell, 
  BarChart2, 
  Calendar, 
  Users, 
  Settings, 
  Layers, 
  FileSearch,
  ShieldCheck,
  Search,
  RadioTower,
  Share2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { 
  PERMISSION_DOCUMENT_VIEW, 
  PERMISSION_DOCUMENT_CREATE,
  PERMISSION_TRADE_VIEW,
  PERMISSION_MARKET_VIEW,
  PERMISSION_COMPLIANCE_VIEW,
  PERMISSION_SIGNATURE_VIEW,
  PERMISSION_APPLICATION_VIEW,
  PERMISSION_DEAL_VIEW,
  PERMISSION_DEAL_VIEW_OWN,
  PERMISSION_SATELLITE_VIEW,
  PERMISSION_AUDIT_VIEW,
  PERMISSION_BILLING_VIEW,
  PERMISSION_TEMPLATE_VIEW,
  PERMISSION_TEMPLATE_GENERATE
} from '@/utils/permissions';

export interface SidebarApp {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
  path?: string;
  requiredPermission?: string;
  requiredPermissions?: string[];
  requireAll?: boolean;
  subscriptionTier?: 'free' | 'pro' | 'premium' | 'lifetime';
  badge?: number;
  category?: 'core' | 'trading' | 'compliance' | 'admin' | 'tools';
  isAdminOnly?: boolean;
  isInstanceAdminOnly?: boolean;
}

interface SidebarNavItemProps {
  app: SidebarApp;
  collapsed: boolean;
  isActive: boolean;
  onClick: () => void;
}

function SidebarNavItem({ app, collapsed, isActive, onClick }: SidebarNavItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group',
        isActive 
          ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/20' 
          : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
      )}
      title={collapsed ? app.name : undefined}
    >
      <span className={cn(
        'flex-shrink-0 transition-transform duration-200',
        isActive ? 'scale-110' : 'group-hover:scale-110'
      )}>
        {app.icon}
      </span>
      {!collapsed && (
        <>
          <span className="flex-1 text-left truncate">{app.name}</span>
          {app.badge && (
            <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500 text-white ring-2 ring-slate-900">
              {app.badge}
            </span>
          )}
        </>
      )}
    </button>
  );
}

export function SidebarNavigation() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { hasPermission, hasAllPermissions } = usePermissions();
  
  // Check if user is instance admin
  const isInstanceAdmin = user?.role === 'admin' && (user as any)?.is_instance_admin === true;
  // Check if user is organization/admin-level (but not necessarily instance admin)
  const isOrgAdmin = user?.role === 'admin' || (user as any)?.organization_role === 'admin';
  
  const sidebarApps: SidebarApp[] = useMemo(() => {
    const apps: SidebarApp[] = [
      // Core Applications (order: dashboard, newsfeed, link-accounts, settings, library, doc-parser, doc-generator)
      {
        id: 'dashboard',
        name: 'Dashboard',
        icon: <LayoutDashboard className="h-5 w-5" />,
        description: 'Portfolio overview & analytics',
        path: '/dashboard',
        category: 'core',
        subscriptionTier: 'free'
      },
      {
        id: 'newsfeed',
        name: 'Social Feeds',
        icon: <Share2 className="h-5 w-5" />,
        description: 'Deals & markets feed, like, comment, share',
        path: '/app/newsfeed',
        category: 'core',
        subscriptionTier: 'free'
      },
      {
        id: 'link-accounts',
        name: 'Link Accounts',
        icon: <Link2 className="h-5 w-5" />,
        description: 'Connect bank and data sources',
        path: '/app/link-accounts',
        category: 'core',
        subscriptionTier: 'free'
      },
      {
        id: 'settings',
        name: 'User Settings',
        icon: <Settings className="h-5 w-5" />,
        description: 'Profile, preferences, and linked accounts',
        path: '/settings',
        category: 'core',
        subscriptionTier: 'free'
      },
      {
        id: 'library',
        name: 'Library',
        icon: <BookOpen className="h-5 w-5" />,
        description: 'Saved documents & history',
        path: '/library',
        category: 'core',
        requiredPermission: PERMISSION_DOCUMENT_VIEW,
        subscriptionTier: 'free'
      },
      {
        id: 'document-parser',
        name: 'Document Parser',
        icon: <FileSearch className="h-5 w-5" />,
        description: 'Extract & digitize credit agreements',
        path: '/app/document-parser',
        category: 'core',
        requiredPermission: PERMISSION_DOCUMENT_CREATE,
        subscriptionTier: 'free'
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
        subscriptionTier: 'free'
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
        subscriptionTier: 'pro'
      },
      {
        id: 'polymarket',
        name: 'Polymarket',
        icon: <BarChart3 className="h-5 w-5" />,
        description: 'Credit event prediction markets',
        path: '/app/polymarket',
        category: 'trading',
        requiredPermission: PERMISSION_MARKET_VIEW,
        subscriptionTier: 'pro'
      },
      {
        id: 'bank-products',
        name: 'Bank Products',
        icon: <DollarSign className="h-5 w-5" />,
        description: 'Marketplace for bank-held products',
        path: '/app/bank-products',
        category: 'trading',
        subscriptionTier: 'free'
      },
      {
        id: 'bridge',
        name: 'Bridge',
        icon: <ArrowLeftRight className="h-5 w-5" />,
        description: 'Cross-chain asset transfers',
        path: '/app/bridge',
        category: 'trading',
        requiredPermission: PERMISSION_TRADE_VIEW,
        subscriptionTier: 'free'
      },
      {
        id: 'securitization',
        name: 'Securitization',
        icon: <Layers className="h-5 w-5" />,
        description: 'Securitization pool management',
        path: '/app/securitization',
        category: 'trading',
        requiredPermission: PERMISSION_TRADE_VIEW,
        subscriptionTier: 'pro'
      },
      {
        id: 'trade-blotter',
        name: 'Trade Blotter',
        icon: <ArrowLeftRight className="h-5 w-5" />,
        description: 'LMA trade confirmation & settlement',
        path: '/app/trade-blotter',
        category: 'trading',
        requiredPermission: PERMISSION_TRADE_VIEW,
        subscriptionTier: 'free'
      },
      {
        id: 'asset-alerts',
        name: 'Asset Alerts',
        icon: <Bell className="h-5 w-5" />,
        description: 'Maturities and amortization reminders',
        path: '/app/asset-alerts',
        category: 'trading',
        requiredPermission: PERMISSION_TRADE_VIEW,
        subscriptionTier: 'free'
      },
      {
        id: 'portfolio-risk',
        name: 'Risk Analysis',
        icon: <BarChart2 className="h-5 w-5" />,
        description: 'Portfolio risk metrics and analysis',
        path: '/app/portfolio-risk',
        category: 'trading',
        requiredPermission: PERMISSION_TRADE_VIEW,
        subscriptionTier: 'pro'
      },
      // Compliance Applications
      {
        id: 'compliance',
        name: 'Compliance',
        icon: <ShieldCheck className="h-5 w-5" />,
        description: 'Compliance monitoring and reporting',
        path: '/dashboard?tab=compliance',
        category: 'compliance',
        requiredPermission: PERMISSION_COMPLIANCE_VIEW,
        subscriptionTier: 'premium'
      },
      {
        id: 'signatures',
        name: 'Signatures',
        icon: <PenTool className="h-5 w-5" />,
        description: 'Document signature management',
        path: '/dashboard?tab=signatures',
        category: 'compliance',
        requiredPermission: PERMISSION_SIGNATURE_VIEW,
        subscriptionTier: 'free'
      },
      {
        id: 'applications',
        name: 'Applications',
        icon: <FileCheck className="h-5 w-5" />,
        description: 'Loan and credit applications',
        path: '/dashboard/applications',
        category: 'compliance',
        requiredPermission: PERMISSION_APPLICATION_VIEW,
        subscriptionTier: 'free'
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
        subscriptionTier: 'free'
      },
      {
        id: 'filings',
        name: 'Filings',
        icon: <FileText className="h-5 w-5" />,
        description: 'Regulatory filing status',
        path: '/app/filings',
        category: 'compliance',
        requiredPermission: PERMISSION_DOCUMENT_VIEW,
        subscriptionTier: 'free'
      },
      {
        id: 'green-lens',
        name: 'Green Lens',
        icon: <Leaf className="h-5 w-5" />,
        description: 'ESG analytics and sustainability',
        path: '/app/green-lens',
        category: 'compliance',
        requiredPermission: PERMISSION_SATELLITE_VIEW,
        subscriptionTier: 'pro'
      },
      {
        id: 'ground-truth',
        name: 'Ground Truth',
        icon: <Shield className="h-5 w-5" />,
        description: 'Geospatial verification for sustainability-linked loans',
        path: '/app/ground-truth',
        category: 'compliance',
        requiredPermission: PERMISSION_SATELLITE_VIEW,
        subscriptionTier: 'pro'
      },
      {
        id: 'verification-demo',
        name: 'Verification Demo',
        icon: <RadioTower className="h-5 w-5" />,
        description: 'Verification dashboard and testing',
        path: '/app/verification-demo',
        category: 'compliance',
        requiredPermission: PERMISSION_SATELLITE_VIEW,
        subscriptionTier: 'pro'
      },
      {
        id: 'auditor',
        name: 'Auditor',
        icon: <Shield className="h-5 w-5" />,
        description: 'Audit reports and compliance checks',
        path: '/auditor',
        category: 'compliance',
        requiredPermission: PERMISSION_AUDIT_VIEW,
        subscriptionTier: 'premium'
      },
      // Tools
      {
        id: 'agent-dashboard',
        name: 'Agent Dashboard',
        icon: <Sparkles className="h-5 w-5" />,
        description: 'AI agent workflows and results',
        path: '/app/agent-dashboard',
        category: 'tools',
        subscriptionTier: 'pro'
      },
      {
        id: 'calendar',
        name: 'Calendar',
        icon: <Calendar className="h-5 w-5" />,
        description: 'Deal and payment calendar',
        path: '/dashboard/calendar',
        category: 'tools',
        subscriptionTier: 'free'
      },
      {
        id: 'billing',
        name: 'Billing',
        icon: <DollarSign className="h-5 w-5" />,
        description: 'Billing and subscription management',
        path: '/dashboard?tab=billing',
        category: 'tools',
        requiredPermission: PERMISSION_BILLING_VIEW,
        subscriptionTier: 'free'
      },
      // Admin Applications
      {
        id: 'admin-settings',
        name: 'Admin Settings',
        icon: <Settings className="h-5 w-5" />,
        description: 'System and organization settings',
        path: '/admin-settings',
        category: 'admin',
        isAdminOnly: true,
        subscriptionTier: 'free'
      },
      {
        id: 'admin-signups',
        name: 'User Signups',
        icon: <Users className="h-5 w-5" />,
        description: 'Review and approve user signups',
        path: '/dashboard/admin-signups',
        category: 'admin',
        isInstanceAdminOnly: true,
        subscriptionTier: 'free'
      },
      {
        id: 'demo-data',
        name: 'Demo Data',
        icon: <Database className="h-5 w-5" />,
        description: 'Seed and manage demo data',
        path: '/app/demo-data',
        category: 'admin',
        isInstanceAdminOnly: true,
        subscriptionTier: 'free'
      },
      {
        id: 'verification-config',
        name: 'Verification Config',
        icon: <Settings className="h-5 w-5" />,
        description: 'Verification file configuration',
        path: '/app/verification-config',
        category: 'admin',
        isInstanceAdminOnly: true,
        subscriptionTier: 'free'
      },
      {
        id: 'whitelisting-dashboard',
        name: 'Whitelisting',
        icon: <Shield className="h-5 w-5" />,
        description: 'IP and file whitelist management',
        path: '/app/whitelisting-dashboard',
        category: 'admin',
        isInstanceAdminOnly: true,
        subscriptionTier: 'free'
      },
      {
        id: 'policy-editor',
        name: 'Policy Editor',
        icon: <Shield className="h-5 w-5" />,
        description: 'Edit policy rules and compliance',
        path: '/app/policy-editor',
        category: 'admin',
        isInstanceAdminOnly: true,
        subscriptionTier: 'free'
      },
      {
        id: 'risk-war-room',
        name: 'Risk War Room',
        icon: <AlertTriangle className="h-5 w-5" />,
        description: 'Risk monitoring and alerts',
        path: '/app/risk-war-room',
        category: 'admin',
        isInstanceAdminOnly: true,
        subscriptionTier: 'free'
      },
      {
        id: 'workflow-processor',
        name: 'Workflow Processor',
        icon: <Share2 className="h-5 w-5" />,
        description: 'Process workflow links',
        path: '/app/workflow/process',
        category: 'admin',
        subscriptionTier: 'free'
      },
      {
        id: 'workflow-share',
        name: 'Workflow Share',
        icon: <Share2 className="h-5 w-5" />,
        description: 'Share workflow links',
        path: '/app/workflow/share',
        category: 'admin',
        subscriptionTier: 'free'
      },
      {
        id: 'loan-recovery',
        name: 'Loan Recovery',
        icon: <ArrowLeftRight className="h-5 w-5" />,
        description: 'Loan recovery management',
        path: '/app/loan-recovery',
        category: 'admin',
        subscriptionTier: 'free'
      }
    ];
    
    // Filter apps based on permissions, subscription, and admin status
    return apps.filter(app => {
      // Instance admin only apps - instance admins bypass all other checks
      if (app.isInstanceAdminOnly) {
        return isInstanceAdmin;
      }
      
      // Admin only apps
      if (app.isAdminOnly && !isOrgAdmin) return false;
      
      // Admins (organization or instance) bypass permission and subscription checks
      // for non-instance-admin-only apps, so they always see the full console.
      if (isInstanceAdmin || isOrgAdmin) {
        return true;
      }
      
      // Permission checks
      if (app.requiredPermission && !hasPermission(app.requiredPermission)) return false;
      if (app.requiredPermissions) {
        if (app.requireAll) {
          if (!hasAllPermissions(app.requiredPermissions)) return false;
        } else {
          if (!app.requiredPermissions.some(p => hasPermission(p))) return false;
        }
      }
      
      // Subscription tier check
      const tierLevels = { free: 0, pro: 1, premium: 2, lifetime: 3 };
      const userTier = user?.subscription_tier || 'free';
      if (tierLevels[userTier as keyof typeof tierLevels] < tierLevels[app.subscriptionTier || 'free']) {
        return false;
      }
      
      return true;
    });
  }, [user, isInstanceAdmin, hasPermission, hasAllPermissions]);

  const handleAppClick = useCallback((app: SidebarApp) => {
    if (app.path) {
      if (typeof window !== 'undefined' && window.localStorage?.getItem('cn_nav_debug') === '1') {
        // eslint-disable-next-line no-console
        console.debug('[cn_nav_debug] sidebar click', { id: app.id, path: app.path, from: location.pathname + location.search });
      }
      navigate(app.path);
    }
  }, [navigate, location.pathname, location.search]);

  return (
    <aside className={cn(
      'h-full bg-slate-950 border-r border-slate-800 transition-all duration-300 ease-in-out flex-shrink-0 relative',
      collapsed ? 'w-20' : 'w-64'
    )}>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="h-16 flex items-center px-4 border-b border-slate-800">
          {!collapsed && (
            <div className="flex items-center gap-2 overflow-hidden animate-in fade-in slide-in-from-left-4 duration-300">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center flex-shrink-0">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <h2 className="text-lg font-bold text-white truncate">CreditNexus</h2>
            </div>
          )}
          {collapsed && (
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center mx-auto">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={cn(
              'absolute -right-3 top-20 w-6 h-6 bg-slate-800 border border-slate-700 rounded-full flex items-center justify-center text-slate-400 hover:text-white transition-colors z-50 shadow-md',
              collapsed ? 'rotate-0' : 'rotate-0'
            )}
          >
            {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
          </button>
        </div>
        
        {/* Navigation Items by Category */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-6 scrollbar-hide">
          {['core', 'trading', 'compliance', 'tools', 'admin'].map(category => {
            const categoryApps = sidebarApps.filter(app => app.category === category);
            if (categoryApps.length === 0) return null;
            
            return (
              <div key={category} className="space-y-1">
                {!collapsed && (
                  <h3 className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                    {category}
                  </h3>
                )}
                <div className="space-y-1">
                  {categoryApps.map(app => (
                    <SidebarNavItem
                      key={app.id}
                      app={app}
                      collapsed={collapsed}
                      isActive={
                        Boolean(location.pathname === app.path || 
                        (app.path?.includes('?tab=') && 
                         location.pathname === app.path.split('?')[0] && 
                         new URLSearchParams(location.search).get('tab') === new URLSearchParams(app.path.split('?')[1] ?? '').get('tab')))
                      }
                      onClick={() => handleAppClick(app)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </nav>

        {/* Footer / User Info */}
        {!collapsed && user && (
          <div className="p-4 border-t border-slate-800 bg-slate-950/50">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold text-xs">
                {user.display_name?.[0] || user.email?.[0]}
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="text-sm font-medium text-white truncate">{user.display_name}</p>
                <p className="text-[10px] text-slate-500 truncate">{user.email}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
