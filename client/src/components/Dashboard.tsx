import { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  Leaf,
  FileText,
  Clock,
  DollarSign,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Loader2,
  Calendar,
  Building2
} from 'lucide-react';

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

const workflowStateColors: Record<string, { bg: string; text: string; label: string }> = {
  draft: { bg: 'bg-slate-500/20', text: 'text-slate-400', label: 'Draft' },
  under_review: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'Under Review' },
  approved: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: 'Approved' },
  published: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'Published' },
  archived: { bg: 'bg-gray-500/20', text: 'text-gray-400', label: 'Archived' },
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
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  return 'Just now';
}

export function Dashboard() {
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetch('/api/analytics/portfolio');
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail?.message || 'Failed to fetch analytics');
      }
      
      setAnalytics(data.analytics);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading portfolio analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <p className="text-slate-300 mb-4">{error}</p>
          <button
            onClick={fetchAnalytics}
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Portfolio Dashboard</h2>
          <p className="text-slate-400 mt-1">Overview of your credit agreement portfolio</p>
        </div>
        <button
          onClick={fetchAnalytics}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <FileText className="h-5 w-5 text-blue-400" />
            </div>
            <span className="text-sm text-slate-400">Total Documents</span>
          </div>
          <p className="text-3xl font-bold text-white">{summary.total_documents}</p>
          <p className="text-sm text-slate-500 mt-1">Credit agreements</p>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
              <DollarSign className="h-5 w-5 text-emerald-400" />
            </div>
            <span className="text-sm text-slate-400">Total Commitments</span>
          </div>
          <p className="text-3xl font-bold text-white">
            {formatCurrency(summary.total_commitment_usd)}
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            {Object.entries(summary.commitments_by_currency).map(([currency, amount]) => (
              <span key={currency} className="text-xs text-slate-400 bg-slate-700/50 px-2 py-1 rounded">
                {currency}: {formatCurrency(amount, currency)}
              </span>
            ))}
          </div>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
              <Leaf className="h-5 w-5 text-green-400" />
            </div>
            <span className="text-sm text-slate-400">Sustainability-Linked</span>
          </div>
          <p className="text-3xl font-bold text-white">{summary.sustainability_percentage}%</p>
          <p className="text-sm text-slate-500 mt-1">
            {summary.sustainability_linked_count} of {summary.total_documents} documents
          </p>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-purple-400" />
            </div>
            <span className="text-sm text-slate-400">Workflow Status</span>
          </div>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-white">
              {workflow_distribution.approved || 0}
            </p>
            <span className="text-sm text-emerald-400">approved</span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            {workflow_distribution.under_review || 0} pending review
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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

        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Leaf className="h-5 w-5 text-green-400" />
            <h3 className="text-lg font-medium text-white">ESG Breakdown</h3>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-green-500/10 rounded-lg border border-green-500/20">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-sm text-green-300">Sustainability-Linked</span>
              </div>
              <span className="font-semibold text-green-400">{esg_breakdown.sustainability_linked}</span>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg border border-slate-600">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-slate-400" />
                <span className="text-sm text-slate-300">Standard</span>
              </div>
              <span className="font-semibold text-slate-300">{esg_breakdown.non_sustainability}</span>
            </div>
            
            {Object.keys(esg_breakdown.esg_score_distribution).length > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-700">
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">ESG Categories</p>
                {Object.entries(esg_breakdown.esg_score_distribution).map(([category, count]) => (
                  <div key={category} className="flex items-center justify-between py-1">
                    <span className="text-sm text-slate-400">{category}</span>
                    <span className="text-sm font-medium text-slate-300">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="h-5 w-5 text-slate-400" />
            <h3 className="text-lg font-medium text-white">Recent Activity</h3>
          </div>
          
          {recent_activity.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-slate-500">
              No recent activity
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
    </div>
  );
}
