import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  FileText,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  ExternalLink,
  Download,
  Filter,
  RefreshCw,
  Loader2,
  Building2,
  Globe,
  TrendingUp,
  TrendingDown
} from 'lucide-react';

interface FilingStatus {
  id: number;
  document_id: number;
  deal_id?: number;
  agreement_type: string;
  jurisdiction: string;
  filing_authority: string;
  filing_system: string;
  filing_reference?: string;
  filing_status: string;
  deadline?: string;
  filed_at?: string;
  filing_url?: string;
  confirmation_url?: string;
  manual_submission_url?: string;
  error_message?: string;
  retry_count: number;
}

interface DeadlineAlert {
  filing_id: number;
  document_id?: number;
  deal_id?: number;
  authority: string;
  deadline: string;
  days_remaining: number;
  urgency: string;
  penalty?: string;
}

interface FilingStatusDashboardProps {
  dealId?: number;
  documentId?: number;
}

export function FilingStatusDashboard({ dealId, documentId }: FilingStatusDashboardProps) {
  const [filings, setFilings] = useState<FilingStatus[]>([]);
  const [alerts, setAlerts] = useState<DeadlineAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterJurisdiction, setFilterJurisdiction] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchData();
  }, [dealId, documentId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch deadline alerts (which include filing info)
      const alertsUrl = `/api/filings/deadline-alerts?days_ahead=365${dealId ? `&deal_id=${dealId}` : ''}${documentId ? `&document_id=${documentId}` : ''}`;
      const alertsResponse = await fetchWithAuth(alertsUrl);
      
      if (alertsResponse.ok) {
        const alertsData = await alertsResponse.json();
        setAlerts(alertsData.alerts || []);
        
        // Extract unique filing IDs from alerts
        const filingIds = Array.from(new Set(alertsData.alerts.map((a: DeadlineAlert) => a.filing_id)));
        
        // Fetch filing details for each
        const filingPromises = filingIds.map(async (id: number) => {
          const filingResponse = await fetchWithAuth(`/api/filings/${id}`);
          if (filingResponse.ok) {
            const filingData = await filingResponse.json();
            return filingData.filing;
          }
          return null;
        });
        
        const filingResults = await Promise.all(filingPromises);
        setFilings(filingResults.filter((f) => f !== null));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load filing data');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const csvRows = [
        ['Filing ID', 'Authority', 'Jurisdiction', 'Status', 'Deadline', 'Filed At', 'Reference'].join(',')
      ];

      filings.forEach((filing) => {
        csvRows.push([
          filing.id.toString(),
          filing.filing_authority,
          filing.jurisdiction,
          filing.filing_status,
          filing.deadline || '',
          filing.filed_at || '',
          filing.filing_reference || ''
        ].join(','));
      });

      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `filing-status-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to export data');
    } finally {
      setExporting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'submitted':
      case 'accepted':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'rejected':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
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

  const filteredFilings = filings.filter((filing) => {
    if (filterJurisdiction !== 'all' && filing.jurisdiction !== filterJurisdiction) {
      return false;
    }
    if (filterStatus !== 'all' && filing.filing_status !== filterStatus) {
      return false;
    }
    return true;
  });

  const jurisdictions = Array.from(new Set(filings.map((f) => f.jurisdiction)));
  const statuses = Array.from(new Set(filings.map((f) => f.filing_status)));

  const stats = {
    total: filings.length,
    pending: filings.filter((f) => f.filing_status === 'pending').length,
    submitted: filings.filter((f) => f.filing_status === 'submitted').length,
    accepted: filings.filter((f) => f.filing_status === 'accepted').length,
    rejected: filings.filter((f) => f.filing_status === 'rejected').length,
    criticalAlerts: alerts.filter((a) => a.urgency === 'critical').length
  };

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Filing Status Dashboard
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleExport}
                disabled={exporting}
                className="text-slate-400 hover:text-slate-100"
              >
                {exporting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Export
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchData}
                className="text-slate-400 hover:text-slate-100"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-4">
            <div className="bg-slate-900 rounded-lg p-3">
              <p className="text-xs text-slate-400">Total</p>
              <p className="text-2xl font-bold text-slate-100">{stats.total}</p>
            </div>
            <div className="bg-slate-900 rounded-lg p-3">
              <p className="text-xs text-slate-400">Pending</p>
              <p className="text-2xl font-bold text-yellow-400">{stats.pending}</p>
            </div>
            <div className="bg-slate-900 rounded-lg p-3">
              <p className="text-xs text-slate-400">Submitted</p>
              <p className="text-2xl font-bold text-blue-400">{stats.submitted}</p>
            </div>
            <div className="bg-slate-900 rounded-lg p-3">
              <p className="text-xs text-slate-400">Accepted</p>
              <p className="text-2xl font-bold text-emerald-400">{stats.accepted}</p>
            </div>
            <div className="bg-slate-900 rounded-lg p-3">
              <p className="text-xs text-slate-400">Rejected</p>
              <p className="text-2xl font-bold text-red-400">{stats.rejected}</p>
            </div>
            <div className="bg-slate-900 rounded-lg p-3">
              <p className="text-xs text-slate-400">Critical Alerts</p>
              <p className="text-2xl font-bold text-red-400">{stats.criticalAlerts}</p>
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-400" />
              <select
                value={filterJurisdiction}
                onChange={(e) => setFilterJurisdiction(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="all">All Jurisdictions</option>
                {jurisdictions.map((j) => (
                  <option key={j} value={j}>
                    {j}
                  </option>
                ))}
              </select>
            </div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="all">All Statuses</option>
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Critical Alerts */}
      {alerts.filter((a) => a.urgency === 'critical').length > 0 && (
        <Card className="bg-red-500/10 border-red-500/50">
          <CardHeader>
            <CardTitle className="text-red-400 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Critical Deadline Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {alerts
                .filter((a) => a.urgency === 'critical')
                .map((alert) => (
                  <div
                    key={alert.filing_id}
                    className="flex items-center justify-between p-3 bg-slate-900 rounded-lg"
                  >
                    <div>
                      <p className="text-slate-100 font-medium">{alert.authority}</p>
                      <p className="text-sm text-slate-400">
                        {alert.days_remaining} day{alert.days_remaining !== 1 ? 's' : ''} remaining
                      </p>
                    </div>
                    <Badge className={getUrgencyColor(alert.urgency)}>
                      {alert.urgency}
                    </Badge>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filings List */}
      {filteredFilings.length === 0 ? (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6 text-center text-slate-400">
            No filings found
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredFilings.map((filing) => {
            const alert = alerts.find((a) => a.filing_id === filing.id);
            return (
              <Card key={filing.id} className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Building2 className="h-5 w-5 text-slate-400" />
                        <CardTitle className="text-slate-100 text-lg">
                          {filing.filing_authority}
                        </CardTitle>
                        <Badge className={getStatusColor(filing.filing_status)}>
                          {filing.filing_status}
                        </Badge>
                        {alert && (
                          <Badge className={getUrgencyColor(alert.urgency)}>
                            {alert.urgency}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
                        <div className="flex items-center gap-1">
                          <Globe className="h-4 w-4" />
                          {filing.jurisdiction}
                        </div>
                        {filing.filing_system === 'companies_house_api' && (
                          <Badge variant="outline" className="text-emerald-400">
                            Automated
                          </Badge>
                        )}
                        {filing.filing_reference && (
                          <span className="font-mono text-slate-300">
                            Ref: {filing.filing_reference}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {filing.deadline && (
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-slate-400" />
                        <span className="text-slate-300">
                          Deadline: {new Date(filing.deadline).toLocaleDateString()}
                        </span>
                        {alert && (
                          <Badge variant="outline" className="text-yellow-400">
                            {alert.days_remaining} days remaining
                          </Badge>
                        )}
                      </div>
                    )}

                    {filing.filed_at && (
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-emerald-400" />
                        <span className="text-slate-300">
                          Filed: {new Date(filing.filed_at).toLocaleDateString()}
                        </span>
                      </div>
                    )}

                    {filing.error_message && (
                      <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/50 rounded-lg">
                        <AlertCircle className="h-4 w-4 text-red-400 mt-0.5" />
                        <div>
                          <p className="text-sm text-red-400 font-medium">Error</p>
                          <p className="text-sm text-slate-400">{filing.error_message}</p>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-2 pt-2 border-t border-slate-700">
                      {filing.filing_url && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => window.open(filing.filing_url, '_blank')}
                          className="text-slate-400 hover:text-slate-100"
                        >
                          <ExternalLink className="h-4 w-4 mr-2" />
                          View Filing
                        </Button>
                      )}
                      {filing.confirmation_url && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => window.open(filing.confirmation_url, '_blank')}
                          className="text-slate-400 hover:text-slate-100"
                        >
                          <CheckCircle className="h-4 w-4 mr-2" />
                          Confirmation
                        </Button>
                      )}
                      {filing.manual_submission_url && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => window.open(filing.manual_submission_url, '_blank')}
                          className="text-slate-400 hover:text-slate-100"
                        >
                          <ExternalLink className="h-4 w-4 mr-2" />
                          Submission Portal
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
