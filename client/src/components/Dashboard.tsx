import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Leaf,
  FileText,
  Clock,
  DollarSign,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Calendar,
  Building2,
  Activity,
  Eye,
  Edit,
  Trash2,
  Send,
  Download,
  LogIn,
  LogOut,
  FileCheck,
  Sparkles,
  Zap,
  ArrowRight
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { SkeletonDashboard } from '@/components/ui/skeleton'; // EmptyState removed - unused
import { useNavigate } from 'react-router-dom';
import { ClauseEditor } from '@/components/ClauseEditor';
import { PermissionGate } from '@/components/PermissionGate';
import {
  PERMISSION_DOCUMENT_VIEW,
  // PERMISSION_FINANCIAL_VIEW removed - unused
  PERMISSION_AUDIT_VIEW,
  PERMISSION_TEMPLATE_VIEW,
  PERMISSION_TEMPLATE_GENERATE,
  PERMISSION_DEAL_VIEW,
  PERMISSION_DEAL_VIEW_OWN,
  PERMISSION_SATELLITE_VIEW,
} from '@/utils/permissions';
import { VerificationWidget } from '@/components/VerificationWidget';
import { FilingDeadlineAlerts } from '@/components/FilingDeadlineAlerts';

interface PortfolioAnalytics {
  summary: {
    total_documents: number;
    total_commitment_usd: number;
    commitments_by_currency: Record<string, number>;
    sustainability_linked_count: number;
    sustainability_percentage: number;
  };
  workflow_distribution: Record<string, number>;
  esg_breakdown: {
    sustainability_linked: number;
    non_sustainability: number;
    esg_score_distribution: Record<string, number>;
  };
  maturity_timeline: Array<{
    id: number;
    title: string;
    borrower_name: string;
    agreement_date: string;
    total_commitment: number | null;
    currency: string;
    sustainability_linked: boolean;
  }>;
  recent_activity: Array<{
    id: number;
    title: string;
    borrower_name: string;
    workflow_state: string | null;
    updated_at: string;
  }>;
}

interface DashboardMetrics {
  key_metrics: {
    total_documents: number;
    docs_this_week: number;
    docs_trend_percent: number;
    pending_review: number;
    approved_this_week: number;
    published_count: number;
    draft_count: number;
    total_commitment_usd: number;
    sustainability_count: number;
    sustainability_percentage: number;
  };
  activity_feed: Array<{
    id: number;
    action: string;
    action_text: string;
    target_type: string;
    target_id: number | null;
    target_name: string | null;
    user_name: string;
    user_id: number | null;
    occurred_at: string;
    metadata: Record<string, unknown> | null;
  }>;
  template_metrics?: {
    total_generations: number;
    success_rate: number;
    average_generation_time_seconds: number;
    most_used_templates: Array<{
      template_id: number;
      template_name: string;
      template_category: string;
      usage_count: number;
    }>;
  };
  last_updated: string;
}

const workflowStateColors: Record<string, { bg: string; text: string; label: string }> = {
  draft: { bg: 'bg-[var(--color-slate-500)]/20', text: 'text-[var(--color-slate-400)]', label: 'Draft' },
  under_review: { bg: 'bg-[var(--color-amber-500)]/20', text: 'text-[var(--color-amber-400)]', label: 'Under Review' },
  approved: { bg: 'bg-[var(--color-emerald-500)]/20', text: 'text-[var(--color-emerald-400)]', label: 'Approved' },
  published: { bg: 'bg-[var(--color-blue-500)]/20', text: 'text-[var(--color-blue-400)]', label: 'Published' },
  archived: { bg: 'bg-[var(--color-gray-500)]/20', text: 'text-[var(--color-gray-400)]', label: 'Archived' },
};

const actionIcons: Record<string, typeof FileText> = {
  create: FileText,
  update: Edit,
  delete: Trash2,
  approve: CheckCircle,
  reject: AlertCircle,
  publish: Send,
  export: Download,
  submit_review: Eye,
  login: LogIn,
  logout: LogOut,
  broadcast: Activity
};

const actionColors: Record<string, { bg: string; text: string }> = {
  create: { bg: 'bg-[var(--color-info-bg)]', text: 'text-[var(--color-info)]' },
  update: { bg: 'bg-[var(--color-warning-bg)]', text: 'text-[var(--color-warning)]' },
  delete: { bg: 'bg-[var(--color-error-bg)]', text: 'text-[var(--color-error)]' },
  approve: { bg: 'bg-[var(--color-emerald-500)]/20', text: 'text-[var(--color-emerald-400)]' },
  reject: { bg: 'bg-[var(--color-red-500)]/20', text: 'text-[var(--color-red-400)]' },
  publish: { bg: 'bg-[var(--color-purple-500)]/20', text: 'text-[var(--color-purple-400)]' },
  export: { bg: 'bg-[var(--color-cyan-500)]/20', text: 'text-[var(--color-cyan-400)]' },
  submit_review: { bg: 'bg-[var(--color-amber-500)]/20', text: 'text-[var(--color-amber-400)]' },
  login: { bg: 'bg-[var(--color-green-500)]/20', text: 'text-[var(--color-green-400)]' },
  logout: { bg: 'bg-[var(--color-slate-500)]/20', text: 'text-[var(--color-slate-400)]' },
  broadcast: { bg: 'bg-[var(--color-indigo-500)]/20', text: 'text-[var(--color-indigo-400)]' }
};

function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(amount);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return 'Just now';
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: typeof FileText;
  iconBg: string;
  iconColor: string;
  trend?: number;
  trendLabel?: string;
}

function MetricCard({ title, value, subtitle, icon: Icon, iconBg, iconColor, trend, trendLabel }: MetricCardProps) {
  return (
    <div className="bg-[var(--surface-panel)] border border-[var(--surface-panel-border)] rounded-xl p-6 hover:border-[var(--color-primary)]/60 transition-colors">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-lg ${iconBg} flex items-center justify-center`}>
          <Icon className={`h-5 w-5 ${iconColor}`} />
        </div>
        <span className="text-sm text-[var(--color-muted-foreground)]">{title}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <p className="text-3xl font-bold text-[var(--color-foreground)]">{value}</p>
        {trend !== undefined && (
          <span className={`flex items-center gap-1 text-sm ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {trend >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {Math.abs(trend)}%
          </span>
        )}
      </div>
      {subtitle && <p className="text-sm text-[var(--color-muted-foreground)] mt-1">{subtitle}</p>}
      {trendLabel && <p className="text-xs text-[var(--color-muted-foreground)] mt-1">{trendLabel}</p>}
    </div>
  );
}

interface ActivityItemProps {
  activity: DashboardMetrics['activity_feed'][0];
}

function ActivityItem({ activity }: ActivityItemProps) {
  const Icon = actionIcons[activity.action] || Activity;
  const colors = actionColors[activity.action] || { bg: 'bg-[var(--color-slate-500)]/20', text: 'text-[var(--color-slate-400)]' };
  
  return (
    <div className="flex items-start gap-3 p-3 bg-[var(--surface-panel-secondary)] rounded-lg hover:bg-[var(--surface-panel-hover)] transition-colors">
      <div className={`w-8 h-8 rounded-lg ${colors.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
        <Icon className={`h-4 w-4 ${colors.text}`} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-[var(--color-foreground)]">
          <span className="font-medium">{activity.user_name}</span>
          <span className="text-[var(--color-muted-foreground)]"> {activity.action_text} </span>
          {activity.target_name && (
            <span className="font-medium text-[var(--color-muted-foreground)]">{activity.target_name}</span>
          )}
          {!activity.target_name && activity.target_type && activity.target_type !== 'user' && (
            <span className="text-[var(--color-muted-foreground)]">{activity.target_type}</span>
          )}
        </p>
        <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
          {activity.occurred_at ? formatTimeAgo(activity.occurred_at) : ''}
        </p>
      </div>
    </div>
  );
}

export function Dashboard() {
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [dashboardMetrics, setDashboardMetrics] = useState<DashboardMetrics | null>(null);
  // Application, Inquiry, Meeting types are defined locally in other components
  // Using any[] temporarily - these should be imported from shared types
  const [_applications, setApplications] = useState<any[]>([]); // Prefix with _ - unused
  const [_inquiries, setInquiries] = useState<any[]>([]); // Prefix with _ - unused
  const [_meetings, setMeetings] = useState<any[]>([]); // Prefix with _ - unused
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchData = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) setIsLoading(true);
      else setIsRefreshing(true);
      setError(null);
      
      const [portfolioRes, dashboardRes, applicationsRes, inquiriesRes, meetingsRes] = await Promise.all([
        fetchWithAuth('/api/analytics/portfolio'),
        fetchWithAuth('/api/analytics/dashboard'),
        fetchWithAuth('/api/applications?limit=5&sort=created_at&order=desc').catch(() => null),
        fetchWithAuth('/api/inquiries?limit=5&sort=created_at&order=desc').catch(() => null),
        fetchWithAuth('/api/meetings?limit=5&sort=scheduled_at&order=asc').catch(() => null)
      ]);
      
      const portfolioData = await portfolioRes.json();
      const dashboardData = await dashboardRes.json();
      
      if (!portfolioRes.ok) {
        throw new Error(portfolioData.detail?.message || 'Failed to fetch portfolio analytics');
      }
      
      setAnalytics(portfolioData.analytics);
      
      if (dashboardRes.ok && dashboardData.dashboard) {
        const dashboard = dashboardData.dashboard;
        
        // Merge template metrics if available
        try {
          const templateMetricsRes = await fetchWithAuth('/api/analytics/template-metrics');
          if (templateMetricsRes.ok) {
            const templateData = await templateMetricsRes.json();
            if (templateData.template_metrics) {
              dashboard.template_metrics = templateData.template_metrics;
            }
          }
        } catch (err) {
          // Template metrics are optional, don't fail if unavailable
          console.warn('Failed to fetch template metrics:', err);
        }
        
        setDashboardMetrics(dashboard);
      }

      // Fetch applications
      if (applicationsRes && applicationsRes.ok) {
        const appsData = await applicationsRes.json();
        setApplications(Array.isArray(appsData) ? appsData : appsData.applications || []);
      }

      // Fetch inquiries
      if (inquiriesRes && inquiriesRes.ok) {
        const inqData = await inquiriesRes.json();
        setInquiries(Array.isArray(inqData) ? inqData : inqData.inquiries || []);
      }

      // Fetch upcoming meetings
      if (meetingsRes && meetingsRes.ok) {
        const meetData = await meetingsRes.json();
        setMeetings(Array.isArray(meetData) ? meetData : meetData.meetings || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      fetchData(false);
    }, 30000);
    
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  if (isLoading) {
    return <SkeletonDashboard />;
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <p className="text-[var(--color-muted-foreground)] mb-4">{error}</p>
          <button
            onClick={() => fetchData()}
            className="flex items-center gap-2 px-4 py-2 bg-[var(--surface-panel)] hover:bg-[var(--surface-panel-hover)] rounded-lg text-sm mx-auto"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return null;
  }

  const { summary, workflow_distribution, esg_breakdown, maturity_timeline, recent_activity } = analytics;
  const totalWorkflowDocs = Object.values(workflow_distribution).reduce((a, b) => a + b, 0);
  const metrics = dashboardMetrics?.key_metrics;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-[var(--color-foreground)]">Portfolio Dashboard</h2>
          <p className="text-[var(--color-muted-foreground)] mt-1">Overview of your credit agreement portfolio</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-[var(--color-muted-foreground)] cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-[var(--color-border)] bg-[var(--surface-panel)] text-[var(--color-foreground)] focus:ring-[var(--color-foreground)]/20"
            />
            Auto-refresh
          </label>
          <button
            onClick={() => fetchData(false)}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-[var(--surface-panel)] hover:bg-[var(--surface-panel-hover)] disabled:opacity-50 rounded-lg text-sm transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {summary.total_documents === 0 && (
        <div className="bg-gradient-to-r from-[var(--color-primary)]/10 to-[var(--color-accent)]/10 border border-[var(--color-primary)]/20 rounded-xl p-6 text-center">
          <FileText className="h-12 w-12 text-[var(--color-primary)] mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">Welcome to CreditNexus</h3>
          <p className="text-[var(--color-muted-foreground)] mb-4 max-w-md mx-auto">
            Your portfolio is empty. Start by uploading a credit agreement document using the Docu-Digitizer, then save it to your library.
          </p>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Log in to save and manage your documents.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Documents"
          value={summary.total_documents}
          subtitle="Credit agreements"
          icon={FileText}
          iconBg="bg-[var(--color-blue-500)]/20"
          iconColor="text-[var(--color-blue-400)]"
          trend={metrics?.docs_trend_percent}
          trendLabel={metrics?.docs_this_week ? `${metrics.docs_this_week} this week` : undefined}
        />

        <MetricCard
          title="Total Commitments"
          value={formatCurrency(summary.total_commitment_usd)}
          icon={DollarSign}
          iconBg="bg-[var(--color-emerald-500)]/20"
          iconColor="text-[var(--color-emerald-400)]"
          subtitle={Object.keys(summary.commitments_by_currency).length > 0 
            ? `Across ${Object.keys(summary.commitments_by_currency).length} currencies`
            : undefined}
        />

        <MetricCard
          title="Pending Review"
          value={metrics?.pending_review ?? (workflow_distribution.under_review || 0)}
          subtitle={metrics?.approved_this_week ? `${metrics.approved_this_week} approved this week` : undefined}
          icon={Clock}
          iconBg="bg-[var(--color-amber-500)]/20"
          iconColor="text-[var(--color-amber-400)]"
        />

        <MetricCard
          title="Sustainability-Linked"
          value={`${summary.sustainability_percentage}%`}
          subtitle={`${summary.sustainability_linked_count} of ${summary.total_documents} documents`}
          icon={Leaf}
          iconBg="bg-[var(--color-green-500)]/20"
          iconColor="text-[var(--color-green-400)]"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Published"
          value={metrics?.published_count ?? (workflow_distribution.published || 0)}
          subtitle="Final documents"
          icon={FileCheck}
          iconBg="bg-[var(--color-purple-500)]/20"
          iconColor="text-[var(--color-purple-400)]"
        />

        <MetricCard
          title="In Draft"
          value={metrics?.draft_count ?? (workflow_distribution.draft || 0)}
          subtitle="Work in progress"
          icon={Edit}
          iconBg="bg-[var(--color-slate-500)]/20"
          iconColor="text-[var(--color-slate-400)]"
        />

        <MetricCard
          title="Approved"
          value={workflow_distribution.approved || 0}
          subtitle="Ready to publish"
          icon={CheckCircle}
          iconBg="bg-[var(--color-emerald-500)]/20"
          iconColor="text-[var(--color-emerald-400)]"
        />

        <MetricCard
          title="Workflow Progress"
          value={`${totalWorkflowDocs > 0 ? Math.round(((workflow_distribution.approved || 0) + (workflow_distribution.published || 0)) / totalWorkflowDocs * 100) : 0}%`}
          subtitle="Completed rate"
          icon={TrendingUp}
          iconBg="bg-[var(--color-indigo-500)]/20"
          iconColor="text-[var(--color-indigo-400)]"
        />
      </div>

      {/* Filing Deadline Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <FilingDeadlineAlerts limit={5} daysAhead={30} />
        </div>
        <div className="lg:col-span-2">
          {/* Placeholder for other content or keep empty for now */}
        </div>
      </div>

      <PermissionGate permission={PERMISSION_AUDIT_VIEW}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 bg-[var(--surface-panel)] border border-[var(--surface-panel-border)] rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-[var(--color-muted-foreground)]" />
                <h3 className="text-lg font-medium text-[var(--color-foreground)]">Activity Feed</h3>
              </div>
            {dashboardMetrics?.last_updated && (
              <span className="text-xs text-[var(--color-muted-foreground)]">
                Updated {formatTimeAgo(dashboardMetrics.last_updated)}
              </span>
            )}
          </div>
          
          {!dashboardMetrics?.activity_feed || dashboardMetrics.activity_feed.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-[var(--color-muted-foreground)]">
              <Activity className="h-8 w-8 mb-2" />
              <p className="text-sm">No recent activity</p>
              <p className="text-xs mt-1">Actions will appear here as they happen</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {dashboardMetrics.activity_feed.slice(0, 10).map((activity) => (
                <ActivityItem key={activity.id} activity={activity} />
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-2 bg-[var(--surface-panel)] border border-[var(--surface-panel-border)] rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-5 w-5 text-[var(--color-muted-foreground)]" />
            <h3 className="text-lg font-medium text-[var(--color-foreground)]">Workflow Distribution</h3>
          </div>
          
          {totalWorkflowDocs === 0 ? (
            <div className="flex items-center justify-center h-40 text-[var(--color-muted-foreground)]">
              No documents in workflow yet
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(workflowStateColors).map(([state, config]) => {
                const count = workflow_distribution[state] || 0;
                const percentage = totalWorkflowDocs > 0 ? (count / totalWorkflowDocs) * 100 : 0;
                
                return (
                  <div key={state}>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-sm ${config.text}`}>{config.label}</span>
                      <span className="text-sm text-[var(--color-muted-foreground)]">{count} ({percentage.toFixed(1)}%)</span>
                    </div>
                    <div className="h-3 bg-[var(--surface-panel-secondary)] rounded-full overflow-hidden">
                      <div
                        className={`h-full ${config.bg.replace('/20', '')} transition-all duration-500`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          </div>
        </div>
      </PermissionGate>

      <PermissionGate permission={PERMISSION_DOCUMENT_VIEW}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[var(--surface-panel)] border border-[var(--surface-panel-border)] rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="h-5 w-5 text-[var(--color-muted-foreground)]" />
            <h3 className="text-lg font-medium text-[var(--color-foreground)]">Recent Documents</h3>
          </div>
          
          {recent_activity.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-[var(--color-muted-foreground)]">
              No recent documents
            </div>
          ) : (
            <div className="space-y-3">
              {recent_activity.map((doc) => {
                const stateConfig = doc.workflow_state
                  ? workflowStateColors[doc.workflow_state] || workflowStateColors.draft
                  : workflowStateColors.draft;
                
                return (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between p-3 bg-[var(--surface-panel-secondary)] rounded-lg hover:bg-[var(--surface-panel-hover)] transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-[var(--color-foreground)] truncate">{doc.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Building2 className="h-3 w-3 text-[var(--color-muted-foreground)]" />
                        <span className="text-xs text-[var(--color-muted-foreground)] truncate">
                          {doc.borrower_name || 'Unknown borrower'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 ml-4">
                      <span className={`text-xs px-2 py-1 rounded ${stateConfig.bg} ${stateConfig.text}`}>
                        {stateConfig.label}
                      </span>
                      <span className="text-xs text-[var(--color-muted-foreground)] whitespace-nowrap">
                        {doc.updated_at ? formatTimeAgo(doc.updated_at) : ''}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-[var(--surface-panel)] border border-[var(--surface-panel-border)] rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="h-5 w-5 text-[var(--color-muted-foreground)]" />
            <h3 className="text-lg font-medium text-[var(--color-foreground)]">Agreement Timeline</h3>
          </div>
          
          {maturity_timeline.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-[var(--color-muted-foreground)]">
              No agreements with dates
            </div>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {maturity_timeline.slice(0, 8).map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-3 bg-[var(--surface-panel-secondary)] rounded-lg"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-[var(--color-foreground)] truncate">{doc.title}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-[var(--color-muted-foreground)]">
                        {doc.agreement_date ? formatDate(doc.agreement_date) : 'No date'}
                      </span>
                      {doc.sustainability_linked && (
                        <span className="flex items-center gap-1 text-xs text-green-400">
                          <Leaf className="h-3 w-3" />
                          ESG
                        </span>
                      )}
                    </div>
                  </div>
                  {doc.total_commitment && doc.currency && (
                    <span className="text-sm font-medium text-emerald-400 ml-4">
                      {formatCurrency(doc.total_commitment, doc.currency)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      </PermissionGate>

      {/* Template Metrics Section */}
      <PermissionGate permission={PERMISSION_TEMPLATE_VIEW}>
        {dashboardMetrics?.template_metrics && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-[var(--surface-panel)] border border-[var(--surface-panel-border)] rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-purple-400" />
                <h3 className="text-lg font-medium text-[var(--color-foreground)]">Template Generation Metrics</h3>
              </div>
            
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="text-center p-4 bg-purple-500/10 rounded-lg border border-purple-500/20">
                <div className="text-2xl font-bold text-purple-400 mb-1">
                  {dashboardMetrics.template_metrics.total_generations}
                </div>
                <div className="text-xs text-[var(--color-muted-foreground)]">Total Generations</div>
              </div>
              <div className="text-center p-4 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                <div className="text-2xl font-bold text-emerald-400 mb-1">
                  {dashboardMetrics.template_metrics.success_rate}%
                </div>
                <div className="text-xs text-[var(--color-muted-foreground)]">Success Rate</div>
              </div>
              <div className="text-center p-4 bg-blue-500/10 rounded-lg border border-blue-500/20">
                <div className="text-2xl font-bold text-blue-400 mb-1">
                  {dashboardMetrics.template_metrics.average_generation_time_seconds}s
                </div>
                <div className="text-xs text-[var(--color-muted-foreground)]">Avg Time</div>
              </div>
            </div>

            {dashboardMetrics.template_metrics.most_used_templates.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-[var(--color-muted-foreground)] mb-3">Most Used Templates</h4>
                <div className="space-y-2">
                  {dashboardMetrics.template_metrics.most_used_templates.map((template, idx) => (
                    <div
                      key={template.template_id}
                      className="flex items-center justify-between p-3 bg-[var(--surface-panel-secondary)] rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                          <span className="text-xs font-bold text-purple-400">#{idx + 1}</span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-[var(--color-foreground)]">{template.template_name}</p>
                          <p className="text-xs text-[var(--color-muted-foreground)]">{template.template_category}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold text-purple-400">{template.usage_count}</div>
                        <div className="text-xs text-[var(--color-muted-foreground)]">uses</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <PermissionGate permission={PERMISSION_TEMPLATE_GENERATE}>
            <div className="bg-[var(--surface-panel)] border border-[var(--surface-panel-border)] rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Zap className="h-5 w-5 text-yellow-400" />
                <h3 className="text-lg font-medium text-[var(--color-foreground)]">Quick Generate</h3>
              </div>
              
              <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
                Start generating LMA documents from templates with your CDM data.
              </p>
              
              <button
                onClick={() => {
                  // Navigate to document generator
                  const event = new CustomEvent('navigateToApp', { detail: { app: 'document-generator' } });
                  window.dispatchEvent(event);
                }}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 rounded-lg text-[var(--color-foreground)] font-medium transition-all"
              >
                <Sparkles className="h-5 w-5" />
                Open Document Generator
                <ArrowRight className="h-4 w-4" />
              </button>
            
            <div className="mt-4 p-3 bg-[var(--surface-panel-secondary)] rounded-lg">
              <p className="text-xs text-[var(--color-muted-foreground)] mb-2">Quick Tips:</p>
              <ul className="text-xs text-[var(--color-muted-foreground)] space-y-1">
                <li>• Extract data from documents first</li>
                <li>• Select appropriate LMA template</li>
                <li>• Review and customize generated content</li>
              </ul>
            </div>
            </div>
          </PermissionGate>

          <PermissionGate permissions={[PERMISSION_DEAL_VIEW, PERMISSION_DEAL_VIEW_OWN]} requireAll={false}>
            <div className="bg-[var(--surface-panel)] border border-[var(--surface-panel-border)] rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Building2 className="h-5 w-5 text-emerald-400" />
                <h3 className="text-lg font-medium text-[var(--color-foreground)]">Deal Management</h3>
              </div>
              
              <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
                Manage your loan and credit deals, track lifecycle, and view timelines.
              </p>
              
              <button
                onClick={() => navigate('/dashboard/deals')}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 rounded-lg text-[var(--color-foreground)] font-medium transition-all"
              >
                <Building2 className="h-5 w-5" />
                View Deals
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </PermissionGate>
          </div>
        )}
      </PermissionGate>

      <PermissionGate permission={PERMISSION_DOCUMENT_VIEW}>
        <div className="bg-[var(--surface-panel)] border border-[var(--surface-panel-border)] rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Leaf className="h-5 w-5 text-green-400" />
            <h3 className="text-lg font-medium text-[var(--color-foreground)]">ESG Breakdown</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-4 bg-green-500/10 rounded-lg border border-green-500/20">
              <div className="flex items-center gap-3">
                <CheckCircle className="h-5 w-5 text-green-400" />
                <div>
                  <span className="text-sm text-green-300 block">Sustainability-Linked</span>
                  <span className="text-xs text-green-400/70">ESG compliant</span>
                </div>
              </div>
              <span className="text-2xl font-bold text-green-400">{esg_breakdown.sustainability_linked}</span>
            </div>
            
            <div className="flex items-center justify-between p-4 bg-[var(--surface-panel-secondary)] rounded-lg border border-[var(--surface-panel-border)]">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-[var(--color-muted-foreground)]" />
                <div>
                  <span className="text-sm text-[var(--color-muted-foreground)] block">Standard</span>
                  <span className="text-xs text-[var(--color-muted-foreground)]/70">Traditional agreements</span>
                </div>
              </div>
              <span className="text-2xl font-bold text-[var(--color-muted-foreground)]">{esg_breakdown.non_sustainability}</span>
            </div>
            
            {Object.keys(esg_breakdown.esg_score_distribution).length > 0 && (
              <div className="p-4 bg-[var(--surface-panel-secondary)] rounded-lg border border-[var(--surface-panel-border)]">
                <p className="text-xs text-[var(--color-muted-foreground)] uppercase tracking-wider mb-3">ESG Categories</p>
                <div className="space-y-2">
                  {Object.entries(esg_breakdown.esg_score_distribution).map(([category, count]) => (
                    <div key={category} className="flex items-center justify-between">
                      <span className="text-sm text-[var(--color-muted-foreground)]">{category}</span>
                      <span className="text-sm font-medium text-[var(--color-muted-foreground)]">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Clause Cache Editor */}
        <ClauseEditor className="mt-6" />
      </PermissionGate>

      {/* Asset Verification Widget */}
      <PermissionGate permission={PERMISSION_SATELLITE_VIEW}>
        <div className="mt-6">
          <VerificationWidget
            embedded={true}
            defaultCollapsed={false}
            onViewFull={() => {
              // Navigate to full verification dashboard
              navigate('/app/ground-truth');
            }}
            onVerificationComplete={(result) => {
              // Optional: Handle verification completion
              console.log('Verification completed:', result);
            }}
          />
        </div>
      </PermissionGate>

    </div>
  );
}
