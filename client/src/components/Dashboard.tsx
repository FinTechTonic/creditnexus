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
  Target,
  ArrowRight,
  Mail,
  Bell,
  User,
  ArrowRightCircle
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { SkeletonDashboard, EmptyState } from '@/components/ui/skeleton';
import { useNavigate } from 'react-router-dom';
import { ClauseEditor } from '@/components/ClauseEditor';
import { PermissionGate } from '@/components/PermissionGate';
import {
  PERMISSION_DOCUMENT_VIEW,
  PERMISSION_FINANCIAL_VIEW,
  PERMISSION_AUDIT_VIEW,
  PERMISSION_TEMPLATE_VIEW,
  PERMISSION_TEMPLATE_GENERATE,
  PERMISSION_DEAL_VIEW,
  PERMISSION_DEAL_VIEW_OWN,
  PERMISSION_SATELLITE_VIEW,
} from '@/utils/permissions';
import { VerificationWidget } from '@/components/VerificationWidget';

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
  draft: { bg: 'bg-slate-500/20', text: 'text-slate-400', label: 'Draft' },
  under_review: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'Under Review' },
  approved: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: 'Approved' },
  published: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'Published' },
  archived: { bg: 'bg-gray-500/20', text: 'text-gray-400', label: 'Archived' },
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
  create: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
  update: { bg: 'bg-amber-500/20', text: 'text-amber-400' },
  delete: { bg: 'bg-red-500/20', text: 'text-red-400' },
  approve: { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
  reject: { bg: 'bg-red-500/20', text: 'text-red-400' },
  publish: { bg: 'bg-purple-500/20', text: 'text-purple-400' },
  export: { bg: 'bg-cyan-500/20', text: 'text-cyan-400' },
  submit_review: { bg: 'bg-amber-500/20', text: 'text-amber-400' },
  login: { bg: 'bg-green-500/20', text: 'text-green-400' },
  logout: { bg: 'bg-slate-500/20', text: 'text-slate-400' },
  broadcast: { bg: 'bg-indigo-500/20', text: 'text-indigo-400' }
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
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-colors">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-lg ${iconBg} flex items-center justify-center`}>
          <Icon className={`h-5 w-5 ${iconColor}`} />
        </div>
        <span className="text-sm text-slate-400">{title}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <p className="text-3xl font-bold text-white">{value}</p>
        {trend !== undefined && (
          <span className={`flex items-center gap-1 text-sm ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {trend >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {Math.abs(trend)}%
          </span>
        )}
      </div>
      {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      {trendLabel && <p className="text-xs text-slate-500 mt-1">{trendLabel}</p>}
    </div>
  );
}

interface ActivityItemProps {
  activity: DashboardMetrics['activity_feed'][0];
}

function ActivityItem({ activity }: ActivityItemProps) {
  const Icon = actionIcons[activity.action] || Activity;
  const colors = actionColors[activity.action] || { bg: 'bg-slate-500/20', text: 'text-slate-400' };
  
  return (
    <div className="flex items-start gap-3 p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors">
      <div className={`w-8 h-8 rounded-lg ${colors.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
        <Icon className={`h-4 w-4 ${colors.text}`} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-medium">{activity.user_name}</span>
          <span className="text-slate-400"> {activity.action_text} </span>
          {activity.target_name && (
            <span className="font-medium text-slate-200">{activity.target_name}</span>
          )}
          {!activity.target_name && activity.target_type && activity.target_type !== 'user' && (
            <span className="text-slate-400">{activity.target_type}</span>
          )}
        </p>
        <p className="text-xs text-slate-500 mt-1">
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
  const [applications, setApplications] = useState<Application[]>([]);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
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
          <p className="text-slate-300 mb-4">{error}</p>
          <button
            onClick={() => fetchData()}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm mx-auto"
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
          <h2 className="text-2xl font-semibold text-white">Portfolio Dashboard</h2>
          <p className="text-slate-400 mt-1">Overview of your credit agreement portfolio</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-slate-600 bg-slate-700 text-emerald-500 focus:ring-emerald-500/20"
            />
            Auto-refresh
          </label>
          <button
            onClick={() => fetchData(false)}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 rounded-lg text-sm transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {summary.total_documents === 0 && (
        <div className="bg-gradient-to-r from-emerald-500/10 to-blue-500/10 border border-emerald-500/20 rounded-xl p-6 text-center">
          <FileText className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Welcome to CreditNexus</h3>
          <p className="text-slate-400 mb-4 max-w-md mx-auto">
            Your portfolio is empty. Start by uploading a credit agreement document using the Docu-Digitizer, then save it to your library.
          </p>
          <p className="text-sm text-slate-500">
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
          iconBg="bg-blue-500/20"
          iconColor="text-blue-400"
          trend={metrics?.docs_trend_percent}
          trendLabel={metrics?.docs_this_week ? `${metrics.docs_this_week} this week` : undefined}
        />

        <MetricCard
          title="Total Commitments"
          value={formatCurrency(summary.total_commitment_usd)}
          icon={DollarSign}
          iconBg="bg-emerald-500/20"
          iconColor="text-emerald-400"
          subtitle={Object.keys(summary.commitments_by_currency).length > 0 
            ? `Across ${Object.keys(summary.commitments_by_currency).length} currencies`
            : undefined}
        />

        <MetricCard
          title="Pending Review"
          value={metrics?.pending_review ?? (workflow_distribution.under_review || 0)}
          subtitle={metrics?.approved_this_week ? `${metrics.approved_this_week} approved this week` : undefined}
          icon={Clock}
          iconBg="bg-amber-500/20"
          iconColor="text-amber-400"
        />

        <MetricCard
          title="Sustainability-Linked"
          value={`${summary.sustainability_percentage}%`}
          subtitle={`${summary.sustainability_linked_count} of ${summary.total_documents} documents`}
          icon={Leaf}
          iconBg="bg-green-500/20"
          iconColor="text-green-400"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Published"
          value={metrics?.published_count ?? (workflow_distribution.published || 0)}
          subtitle="Final documents"
          icon={FileCheck}
          iconBg="bg-purple-500/20"
          iconColor="text-purple-400"
        />

        <MetricCard
          title="In Draft"
          value={metrics?.draft_count ?? (workflow_distribution.draft || 0)}
          subtitle="Work in progress"
          icon={Edit}
          iconBg="bg-slate-500/20"
          iconColor="text-slate-400"
        />

        <MetricCard
          title="Approved"
          value={workflow_distribution.approved || 0}
          subtitle="Ready to publish"
          icon={CheckCircle}
          iconBg="bg-emerald-500/20"
          iconColor="text-emerald-400"
        />

        <MetricCard
          title="Workflow Progress"
          value={`${totalWorkflowDocs > 0 ? Math.round(((workflow_distribution.approved || 0) + (workflow_distribution.published || 0)) / totalWorkflowDocs * 100) : 0}%`}
          subtitle="Completed rate"
          icon={TrendingUp}
          iconBg="bg-indigo-500/20"
          iconColor="text-indigo-400"
        />
      </div>

      <PermissionGate permission={PERMISSION_AUDIT_VIEW}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 bg-slate-800/50 border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-slate-400" />
                <h3 className="text-lg font-medium text-white">Activity Feed</h3>
              </div>
            {dashboardMetrics?.last_updated && (
              <span className="text-xs text-slate-500">
                Updated {formatTimeAgo(dashboardMetrics.last_updated)}
              </span>
            )}
          </div>
          
          {!dashboardMetrics?.activity_feed || dashboardMetrics.activity_feed.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-500">
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

        <div className="lg:col-span-2 bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-5 w-5 text-slate-400" />
            <h3 className="text-lg font-medium text-white">Workflow Distribution</h3>
          </div>
          
          {totalWorkflowDocs === 0 ? (
            <div className="flex items-center justify-center h-40 text-slate-500">
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
                      <span className="text-sm text-slate-400">{count} ({percentage.toFixed(1)}%)</span>
                    </div>
                    <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
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
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="h-5 w-5 text-slate-400" />
            <h3 className="text-lg font-medium text-white">Recent Documents</h3>
          </div>
          
          {recent_activity.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-slate-500">
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
                    className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-white truncate">{doc.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Building2 className="h-3 w-3 text-slate-500" />
                        <span className="text-xs text-slate-400 truncate">
                          {doc.borrower_name || 'Unknown borrower'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 ml-4">
                      <span className={`text-xs px-2 py-1 rounded ${stateConfig.bg} ${stateConfig.text}`}>
                        {stateConfig.label}
                      </span>
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        {doc.updated_at ? formatTimeAgo(doc.updated_at) : ''}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="h-5 w-5 text-slate-400" />
            <h3 className="text-lg font-medium text-white">Agreement Timeline</h3>
          </div>
          
          {maturity_timeline.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-slate-500">
              No agreements with dates
            </div>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {maturity_timeline.slice(0, 8).map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-white truncate">{doc.title}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-slate-400">
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
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-purple-400" />
                <h3 className="text-lg font-medium text-white">Template Generation Metrics</h3>
              </div>
            
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="text-center p-4 bg-purple-500/10 rounded-lg border border-purple-500/20">
                <div className="text-2xl font-bold text-purple-400 mb-1">
                  {dashboardMetrics.template_metrics.total_generations}
                </div>
                <div className="text-xs text-slate-400">Total Generations</div>
              </div>
              <div className="text-center p-4 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                <div className="text-2xl font-bold text-emerald-400 mb-1">
                  {dashboardMetrics.template_metrics.success_rate}%
                </div>
                <div className="text-xs text-slate-400">Success Rate</div>
              </div>
              <div className="text-center p-4 bg-blue-500/10 rounded-lg border border-blue-500/20">
                <div className="text-2xl font-bold text-blue-400 mb-1">
                  {dashboardMetrics.template_metrics.average_generation_time_seconds}s
                </div>
                <div className="text-xs text-slate-400">Avg Time</div>
              </div>
            </div>

            {dashboardMetrics.template_metrics.most_used_templates.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-slate-300 mb-3">Most Used Templates</h4>
                <div className="space-y-2">
                  {dashboardMetrics.template_metrics.most_used_templates.map((template, idx) => (
                    <div
                      key={template.template_id}
                      className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                          <span className="text-xs font-bold text-purple-400">#{idx + 1}</span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white">{template.template_name}</p>
                          <p className="text-xs text-slate-400">{template.template_category}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold text-purple-400">{template.usage_count}</div>
                        <div className="text-xs text-slate-500">uses</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <PermissionGate permission={PERMISSION_TEMPLATE_GENERATE}>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Zap className="h-5 w-5 text-yellow-400" />
                <h3 className="text-lg font-medium text-white">Quick Generate</h3>
              </div>
              
              <p className="text-sm text-slate-400 mb-4">
                Start generating LMA documents from templates with your CDM data.
              </p>
              
              <button
                onClick={() => {
                  // Navigate to document generator
                  const event = new CustomEvent('navigateToApp', { detail: { app: 'document-generator' } });
                  window.dispatchEvent(event);
                }}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 rounded-lg text-white font-medium transition-all"
              >
                <Sparkles className="h-5 w-5" />
                Open Document Generator
                <ArrowRight className="h-4 w-4" />
              </button>
            
            <div className="mt-4 p-3 bg-slate-700/30 rounded-lg">
              <p className="text-xs text-slate-400 mb-2">Quick Tips:</p>
              <ul className="text-xs text-slate-500 space-y-1">
                <li>• Extract data from documents first</li>
                <li>• Select appropriate LMA template</li>
                <li>• Review and customize generated content</li>
              </ul>
            </div>
            </div>
          </PermissionGate>

          <PermissionGate permissions={[PERMISSION_DEAL_VIEW, PERMISSION_DEAL_VIEW_OWN]} requireAll={false}>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Building2 className="h-5 w-5 text-emerald-400" />
                <h3 className="text-lg font-medium text-white">Deal Management</h3>
              </div>
              
              <p className="text-sm text-slate-400 mb-4">
                Manage your loan and credit deals, track lifecycle, and view timelines.
              </p>
              
              <button
                onClick={() => navigate('/dashboard/deals')}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 rounded-lg text-white font-medium transition-all"
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
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Leaf className="h-5 w-5 text-green-400" />
            <h3 className="text-lg font-medium text-white">ESG Breakdown</h3>
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
            
            <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg border border-slate-600">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-slate-400" />
                <div>
                  <span className="text-sm text-slate-300 block">Standard</span>
                  <span className="text-xs text-slate-400/70">Traditional agreements</span>
                </div>
              </div>
              <span className="text-2xl font-bold text-slate-300">{esg_breakdown.non_sustainability}</span>
            </div>
            
            {Object.keys(esg_breakdown.esg_score_distribution).length > 0 && (
              <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600">
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">ESG Categories</p>
                <div className="space-y-2">
                  {Object.entries(esg_breakdown.esg_score_distribution).map(([category, count]) => (
                    <div key={category} className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">{category}</span>
                      <span className="text-sm font-medium text-slate-300">{count}</span>
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
