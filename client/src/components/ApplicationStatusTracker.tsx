import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext'; // useAuth removed - unused
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  CheckCircle, 
  Clock, 
  X, 
  FileText, 
  Send, 
  Eye,
  Loader2,
  AlertCircle
} from 'lucide-react';

interface Application {
  id: number;
  application_type: string;
  status: string;
  user_id: number | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

interface StatusChange {
  status: string;
  timestamp: string;
  label: string;
  icon: typeof CheckCircle;
  color: string;
}

const statusConfig: Record<string, { label: string; icon: typeof CheckCircle; color: string; bg: string }> = {
  draft: {
    label: 'Draft',
    icon: FileText,
    color: 'text-slate-400',
    bg: 'bg-slate-500/20'
  },
  submitted: {
    label: 'Submitted',
    icon: Send,
    color: 'text-blue-400',
    bg: 'bg-blue-500/20'
  },
  under_review: {
    label: 'Under Review',
    icon: Eye,
    color: 'text-amber-400',
    bg: 'bg-amber-500/20'
  },
  approved: {
    label: 'Approved',
    icon: CheckCircle,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/20'
  },
  rejected: {
    label: 'Rejected',
    icon: X,
    color: 'text-red-400',
    bg: 'bg-red-500/20'
  },
  withdrawn: {
    label: 'Withdrawn',
    icon: X,
    color: 'text-slate-400',
    bg: 'bg-slate-500/20'
  },
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  
  if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  return 'Just now';
}

function buildStatusTimeline(application: Application): StatusChange[] {
  const timeline: StatusChange[] = [];
  
  // Created (Draft)
  timeline.push({
    status: 'draft',
    timestamp: application.created_at,
    label: 'Application Created',
    icon: statusConfig.draft.icon,
    color: statusConfig.draft.color,
  });

  // Submitted
  if (application.submitted_at) {
    timeline.push({
      status: 'submitted',
      timestamp: application.submitted_at,
      label: 'Application Submitted',
      icon: statusConfig.submitted.icon,
      color: statusConfig.submitted.color,
    });
  }

  // Under Review
  if (application.reviewed_at && application.status === 'under_review') {
    timeline.push({
      status: 'under_review',
      timestamp: application.reviewed_at,
      label: 'Review Started',
      icon: statusConfig.under_review.icon,
      color: statusConfig.under_review.color,
    });
  }

  // Final Status
  if (application.approved_at) {
    timeline.push({
      status: 'approved',
      timestamp: application.approved_at,
      label: 'Application Approved',
      icon: statusConfig.approved.icon,
      color: statusConfig.approved.color,
    });
  } else if (application.rejected_at) {
    timeline.push({
      status: 'rejected',
      timestamp: application.rejected_at,
      label: 'Application Rejected',
      icon: statusConfig.rejected.icon,
      color: statusConfig.rejected.color,
    });
  }

  return timeline.sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
}

interface ApplicationStatusTrackerProps {
  applicationId: number;
  className?: string;
}

export function ApplicationStatusTracker({ applicationId, className = '' }: ApplicationStatusTrackerProps) {
  // const { user } = useAuth(); // user removed - unused
  const [application, setApplication] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchApplication();
  }, [applicationId]);

  const fetchApplication = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth(`/api/applications/${applicationId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch application');
      }
      const data = await response.json();
      setApplication(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load application');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card className={`bg-slate-800 border-slate-700 ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`bg-slate-800 border-slate-700 ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="h-5 w-5" />
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!application) {
    return null;
  }

  const timeline = buildStatusTimeline(application);
  const currentStatusConfig = statusConfig[application.status] || statusConfig.draft;
  const CurrentIcon = currentStatusConfig.icon;

  return (
    <Card className={`bg-slate-800 border-slate-700 ${className}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-slate-400" />
          Application Status Timeline
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Current Status */}
        <div className="flex items-center gap-4 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
          <div className={`w-12 h-12 rounded-lg ${currentStatusConfig.bg} flex items-center justify-center`}>
            <CurrentIcon className={`h-6 w-6 ${currentStatusConfig.color}`} />
          </div>
          <div className="flex-1">
            <p className="text-sm text-slate-400 mb-1">Current Status</p>
            <p className={`text-lg font-semibold ${currentStatusConfig.color}`}>
              {currentStatusConfig.label}
            </p>
          </div>
          {application.rejection_reason && (
            <div className="text-right">
              <p className="text-xs text-slate-500 mb-1">Rejection Reason</p>
              <p className="text-sm text-red-400 max-w-xs">{application.rejection_reason}</p>
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="relative">
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-slate-700" />
          <div className="space-y-6">
            {timeline.map((item) => { // index removed - unused
              const Icon = item.icon;
              // const isLast = index === timeline.length - 1; // Commented out - unused
              const isActive = item.status === application.status;
              
              return (
                <div key={`${item.status}-${item.timestamp}`} className="relative flex items-start gap-4">
                  <div className={`relative z-10 w-12 h-12 rounded-full ${isActive ? statusConfig[item.status].bg : 'bg-slate-700/50'} flex items-center justify-center border-2 ${isActive ? 'border-emerald-500/50' : 'border-slate-600'}`}>
                    <Icon className={`h-5 w-5 ${isActive ? item.color : 'text-slate-500'}`} />
                  </div>
                  <div className="flex-1 pt-1">
                    <div className="flex items-center justify-between mb-1">
                      <p className={`text-sm font-medium ${isActive ? 'text-white' : 'text-slate-400'}`}>
                        {item.label}
                      </p>
                      <span className="text-xs text-slate-500">
                        {formatTimeAgo(item.timestamp)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      {formatDate(item.timestamp)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Application Type Info */}
        <div className="pt-4 border-t border-slate-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Application Type</span>
            <span className="text-white font-medium">
              {application.application_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-slate-400">Created</span>
            <span className="text-slate-300">
              {formatDate(application.created_at)}
            </span>
          </div>
          {application.updated_at && (
            <div className="flex items-center justify-between text-sm mt-2">
              <span className="text-slate-400">Last Updated</span>
              <span className="text-slate-300">
                {formatTimeAgo(application.updated_at)}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
