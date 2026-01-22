import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertTriangle,
  Clock,
  Calendar,
  ExternalLink,
  // FileText removed - unused
  Building2,
  Globe,
  Loader2,
  ChevronRight
} from 'lucide-react';

interface FilingDeadline {
  filing_id: number;
  document_id: number;
  document_title?: string;
  deal_id?: number;
  authority: string;
  jurisdiction: string;
  deadline: string;
  days_until: number;
  priority: string;
  status: string;
  filing_url?: string;
}

interface FilingDeadlineAlertsProps {
  limit?: number;
  daysAhead?: number;
}

export function FilingDeadlineAlerts({ limit = 5, daysAhead = 30 }: FilingDeadlineAlertsProps) {
  const navigate = useNavigate();
  const [deadlines, setDeadlines] = useState<FilingDeadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDeadlines();
    // Refresh every 5 minutes
    const interval = setInterval(fetchDeadlines, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [daysAhead, limit]);

  const fetchDeadlines = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch deadline alerts from compliance report or dedicated endpoint
      const response = await fetchWithAuth(
        `/api/filings/compliance-report?days_ahead=${daysAhead}`
      );
      
      if (response.ok) {
        const data = await response.json();
        // Extract deadline alerts from compliance report
        const alerts = data.report?.deadline_alerts || [];
        
        // Format and limit results
        const formatted: FilingDeadline[] = alerts
          .slice(0, limit)
          .map((alert: any) => ({
            filing_id: alert.filing_id,
            document_id: alert.document_id,
            document_title: alert.document_title,
            deal_id: alert.deal_id,
            authority: alert.authority,
            jurisdiction: alert.jurisdiction,
            deadline: alert.deadline,
            days_until: alert.days_until,
            priority: alert.priority,
            status: alert.status,
            filing_url: alert.filing_url
          }));
        
        setDeadlines(formatted);
      } else {
        // Fallback: try alternative endpoint
        const altResponse = await fetchWithAuth(
          `/api/filings/deadline-alerts?days_ahead=${daysAhead}&limit=${limit}`
        );
        if (altResponse.ok) {
          const altData = await altResponse.json();
          setDeadlines(altData.alerts || []);
        } else {
          throw new Error('Failed to fetch deadline alerts');
        }
      }
    } catch (err) {
      console.error('Error fetching filing deadlines:', err);
      setError(err instanceof Error ? err.message : 'Failed to load deadlines');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'submitted':
      case 'accepted':
        return 'bg-emerald-500/20 text-emerald-400';
      case 'pending':
      case 'prepared':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'rejected':
        return 'bg-red-500/20 text-red-400';
      default:
        return 'bg-slate-500/20 text-slate-400';
    }
  };

  const formatCountdown = (days: number) => {
    if (days < 0) {
      return `${Math.abs(days)} day${Math.abs(days) !== 1 ? 's' : ''} overdue`;
    } else if (days === 0) {
      return 'Due today';
    } else if (days === 1) {
      return 'Due tomorrow';
    } else if (days <= 7) {
      return `${days} days remaining`;
    } else {
      return `${days} days remaining`;
    }
  };

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-400" />
            Filing Deadlines
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-400" />
            Filing Deadlines
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-400">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (deadlines.length === 0) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-400" />
            Filing Deadlines
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-400 text-center py-4">
            No upcoming filing deadlines
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-400" />
            Filing Deadlines
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/app/filings')}
            className="text-slate-400 hover:text-slate-100"
          >
            View All
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {deadlines.map((deadline) => (
            <div
              key={deadline.filing_id}
              className={`p-3 rounded-lg border transition-all ${
                deadline.days_until <= 1
                  ? 'border-red-500/50 bg-red-500/10'
                  : deadline.days_until <= 7
                  ? 'border-yellow-500/50 bg-yellow-500/10'
                  : 'border-slate-700 bg-slate-900/50'
              } hover:bg-slate-800 cursor-pointer`}
              onClick={() => {
                if (deadline.document_id) {
                  navigate(`/app/documents?documentId=${deadline.document_id}`);
                }
              }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Building2 className="h-4 w-4 text-slate-400 flex-shrink-0" />
                    <span className="font-medium text-slate-100 truncate">
                      {deadline.authority}
                    </span>
                    <Badge className={getPriorityColor(deadline.priority)}>
                      {deadline.priority}
                    </Badge>
                  </div>
                  
                  {deadline.document_title && (
                    <p className="text-sm text-slate-400 truncate mb-1">
                      {deadline.document_title}
                    </p>
                  )}
                  
                  <div className="flex items-center gap-3 text-xs text-slate-400 mt-2">
                    <div className="flex items-center gap-1">
                      <Globe className="h-3 w-3" />
                      {deadline.jurisdiction}
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {new Date(deadline.deadline).toLocaleDateString()}
                    </div>
                    <Badge variant="outline" className={getStatusColor(deadline.status)}>
                      {deadline.status}
                    </Badge>
                  </div>
                </div>
                
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <div className="flex items-center gap-1">
                    <Clock className={`h-4 w-4 ${
                      deadline.days_until <= 1
                        ? 'text-red-400'
                        : deadline.days_until <= 7
                        ? 'text-yellow-400'
                        : 'text-slate-400'
                    }`} />
                    <span className={`text-sm font-medium ${
                      deadline.days_until <= 1
                        ? 'text-red-400'
                        : deadline.days_until <= 7
                        ? 'text-yellow-400'
                        : 'text-slate-300'
                    }`}>
                      {formatCountdown(deadline.days_until)}
                    </span>
                  </div>
                  {deadline.filing_url && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        window.open(deadline.filing_url, '_blank');
                      }}
                      className="h-6 px-2 text-xs text-blue-400 hover:text-blue-300"
                    >
                      <ExternalLink className="h-3 w-3 mr-1" />
                      View
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
        
        {deadlines.length >= limit && (
          <div className="mt-4 pt-3 border-t border-slate-700">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/app/filings')}
              className="w-full text-slate-400 hover:text-slate-100"
            >
              View All Filing Deadlines
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
