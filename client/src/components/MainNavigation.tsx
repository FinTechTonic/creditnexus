import { useState, useMemo } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  LayoutDashboard,
  FileText,
  BookOpen,
  Sparkles,
  Calendar,
  Building2,
  Menu,
  X,
  ChevronDown
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '@/hooks/usePermissions';
import {
  PERMISSION_DOCUMENT_VIEW,
  PERMISSION_DOCUMENT_CREATE,
  PERMISSION_TEMPLATE_VIEW,
  PERMISSION_TEMPLATE_GENERATE,
  PERMISSION_APPLICATION_VIEW,
  PERMISSION_DEAL_VIEW,
  PERMISSION_DEAL_VIEW_OWN,
} from '@/utils/permissions';

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: typeof LayoutDashboard;
  description?: string;
  children?: NavItem[];
}

interface NavItemWithPermission extends NavItem {
  requiredPermission?: string;
  requiredPermissions?: string[];
  requireAll?: boolean;
}

const mainNavItems: NavItemWithPermission[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    path: '/dashboard',
    icon: LayoutDashboard,
    description: 'Portfolio overview & analytics',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
  },
  {
    id: 'document-parser',
    label: 'Document Parser',
    path: '/app/document-parser',
    icon: FileText,
    description: 'Extract & digitize credit agreements',
    requiredPermission: PERMISSION_DOCUMENT_CREATE,
  },
  {
    id: 'library',
    label: 'Library',
    path: '/library',
    icon: BookOpen,
    description: 'Saved documents & history',
    requiredPermission: PERMISSION_DOCUMENT_VIEW,
  },
  {
    id: 'document-generator',
    label: 'Document Generator',
    path: '/app/document-generator',
    icon: Sparkles,
    description: 'Generate LMA documents from templates',
    requiredPermissions: [PERMISSION_TEMPLATE_VIEW, PERMISSION_TEMPLATE_GENERATE],
    requireAll: false,
  },
  {
    id: 'applications',
    label: 'Applications',
    path: '/dashboard/applications',
    icon: Building2,
    description: 'Loan applications & status',
    requiredPermission: PERMISSION_APPLICATION_VIEW,
  },
  {
    id: 'deals',
    label: 'Deals',
    path: '/dashboard/deals',
    icon: Building2,
    description: 'Deal management & lifecycle',
    requiredPermissions: [PERMISSION_DEAL_VIEW, PERMISSION_DEAL_VIEW_OWN],
    requireAll: false,
  },
  {
    id: 'calendar',
    label: 'Calendar',
    path: '/dashboard/calendar',
    icon: Calendar,
    description: 'Meetings & events',
    // Calendar accessible to all authenticated users
  },
];

interface MainNavigationProps {
  className?: string;
  mobileMenuOpen?: boolean;
  onMobileMenuToggle?: () => void;
}

export function MainNavigation({ 
  className = '', 
  mobileMenuOpen = false,
  onMobileMenuToggle 
}: MainNavigationProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermissions();
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Filter nav items based on permissions
  const visibleNavItems = useMemo(() => {
    return mainNavItems.filter((item) => {
      if (!item.requiredPermission && !item.requiredPermissions) {
        return true; // No permission required
      }
      
      if (item.requiredPermission) {
        return hasPermission(item.requiredPermission);
      }
      
      if (item.requiredPermissions) {
        if (item.requireAll) {
          return hasAllPermissions(item.requiredPermissions);
        } else {
          return hasAnyPermission(item.requiredPermissions);
        }
      }
      
      return false;
    });
  }, [hasPermission, hasAnyPermission, hasAllPermissions]);

  const isActive = (path: string) => {
    if (path === '/dashboard') {
      return location.pathname === '/dashboard' || location.pathname.startsWith('/dashboard/');
    }
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  const handleNavClick = (item: NavItem) => {
    navigate(item.path);
    if (onMobileMenuToggle) {
      onMobileMenuToggle();
    }
  };

  const toggleExpand = (itemId: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  return (
    <>
      {/* Desktop Navigation */}
      <nav className={`hidden md:block ${className}`}>
        <ul className="space-y-1">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            const hasChildren = item.children && item.children.length > 0;
            const isExpanded = expandedItems.has(item.id);

            return (
              <li key={item.id}>
                {hasChildren ? (
                  <div>
                    <button
                      onClick={() => toggleExpand(item.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                        active
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                      }`}
                    >
                      <Icon className="h-5 w-5 flex-shrink-0" />
                      <span className="flex-1 text-left font-medium">{item.label}</span>
                      <ChevronDown
                        className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      />
                    </button>
                    {isExpanded && item.children && (
                      <ul className="mt-1 ml-4 space-y-1 border-l border-slate-700 pl-4">
                        {item.children.map((child) => {
                          const ChildIcon = child.icon;
                          const childActive = isActive(child.path);
                          return (
                            <li key={child.id}>
                              <button
                                onClick={() => handleNavClick(child)}
                                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                                  childActive
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                                }`}
                              >
                                <ChildIcon className="h-4 w-4 flex-shrink-0" />
                                <span>{child.label}</span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                ) : (
                  <button
                    onClick={() => handleNavClick(item)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      active
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`}
                  >
                    <Icon className="h-5 w-5 flex-shrink-0" />
                    <div className="flex-1 text-left">
                      <div className="font-medium">{item.label}</div>
                      {item.description && (
                        <div className="text-xs text-slate-500 mt-0.5">{item.description}</div>
                      )}
                    </div>
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Mobile Navigation */}
      <div className={`md:hidden ${className}`}>
        {/* Mobile Menu Button */}
        <button
          onClick={onMobileMenuToggle}
          className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? (
            <X className="h-6 w-6" />
          ) : (
            <Menu className="h-6 w-6" />
          )}
        </button>

        {/* Mobile Menu Overlay */}
        {mobileMenuOpen && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={onMobileMenuToggle}
            />
            <nav className="fixed top-0 left-0 h-full w-64 bg-slate-900 border-r border-slate-700 z-50 overflow-y-auto">
              <div className="p-4 border-b border-slate-700">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">Navigation</h2>
                  <button
                    onClick={onMobileMenuToggle}
                    className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>
              <ul className="p-4 space-y-2">
                {visibleNavItems.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.path);
                  const hasChildren = item.children && item.children.length > 0;
                  const isExpanded = expandedItems.has(item.id);

                  return (
                    <li key={item.id}>
                      {hasChildren ? (
                        <div>
                          <button
                            onClick={() => toggleExpand(item.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                              active
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : 'text-slate-300 hover:bg-slate-800'
                            }`}
                          >
                            <Icon className="h-5 w-5 flex-shrink-0" />
                            <span className="flex-1 text-left font-medium">{item.label}</span>
                            <ChevronDown
                              className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                            />
                          </button>
                          {isExpanded && item.children && (
                            <ul className="mt-1 ml-4 space-y-1 border-l border-slate-700 pl-4">
                              {item.children.map((child) => {
                                const ChildIcon = child.icon;
                                const childActive = isActive(child.path);
                                return (
                                  <li key={child.id}>
                                    <button
                                      onClick={() => handleNavClick(child)}
                                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                                        childActive
                                          ? 'bg-emerald-500/20 text-emerald-400'
                                          : 'text-slate-400 hover:bg-slate-800'
                                      }`}
                                    >
                                      <ChildIcon className="h-4 w-4 flex-shrink-0" />
                                      <span>{child.label}</span>
                                    </button>
                                  </li>
                                );
                              })}
                            </ul>
                          )}
                        </div>
                      ) : (
                        <button
                          onClick={() => handleNavClick(item)}
                          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                            active
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'text-slate-300 hover:bg-slate-800'
                          }`}
                        >
                          <Icon className="h-5 w-5 flex-shrink-0" />
                          <div className="flex-1 text-left">
                            <div className="font-medium">{item.label}</div>
                            {item.description && (
                              <div className="text-xs text-slate-500 mt-0.5">{item.description}</div>
                            )}
                          </div>
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            </nav>
          </>
        )}
      </div>
    </>
  );
}
