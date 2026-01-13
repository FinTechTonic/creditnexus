import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchWithAuth } from '@/context/AuthContext';
import { AuditTimeline } from '@/components/audit/AuditTimeline';
import { AuditFilters } from '@/components/audit/AuditFilters';
import type { AuditFilters as AuditFiltersType } from '@/components/audit/AuditFilters';
import type { AuditEvent } from '@/components/audit/AuditTimeline';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Download, Building2, FileText, Shield, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface DealAuditTrail {
  deal: {
    id: number;
    deal_id: string;
    title: string;
    status: string;
    created_at: string;
    updated_at: string;
  };
  audit_logs: AuditEvent[];
  policy_decisions: Array<{
    id: number;
    transaction_id: string;
    decision: string;
    rule_applied: string;
    created_at: string;
  }>;
  summary: {
    total_logs: number;
    total_policy_decisions: number;
    date_range: {
      start: string | null;
      end: string | null;
    };
  };
}

export function DealAuditView() {
  const { dealId } = useParams<{ dealId: string }>();
  const navigate = useNavigate();
  const [auditTrail, setAuditTrail] = useState<DealAuditTrail | null>(null);
  const [filters, setFilters] = useState<AuditFiltersType>({
    startDate: null,
    endDate: null,
    action: null,
    targetType: null,
    userId: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const fetchAuditTrail = async () => {
      if (!dealId) return;
      
      try {
        setLoading(true);
        setError(null);
        const params = new URLSearchParams();
        if (filters.startDate) params.append('start_date', filters.startDate);
        if (filters.endDate) params.append('end_date', filters.endDate);
        
        const response = await fetchWithAuth(
          `/api/auditor/deals/${dealId}/audit?${params.toString()}`
        );
        if (!response.ok) {
          throw new Error('Failed to load deal audit trail');
        }
        const data = await response.json();
        setAuditTrail(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load audit trail');
      } finally {
        setLoading(false);
      }
    };

    fetchAuditTrail();
  }, [dealId, filters.startDate, filters.endDate]);

  const handleFilterChange = (newFilters: Partial<AuditFiltersType>) => {
    setFilters({ ...filters, ...newFilters });
  };

  const handleExport = async (format: 'csv' | 'excel' | 'pdf') => {
    if (!auditTrail) return;
    
    try {
      setExporting(true);
      const params = new URLSearchParams();
      params.append('format', format);
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      
      const response = await fetchWithAuth(
        `/api/auditor/export?${params.toString()}`
      );
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `deal_${dealId}_audit_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'ALLOW':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'BLOCK':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'FLAG':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (error || !auditTrail) {
    return (
      <div className="p-6">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4 text-red-400">
          Error: {error || 'Deal audit trail not found'}
        </div>
        <Button onClick={() => navigate('/auditor')} className="mt-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/auditor')}
            className="text-slate-400 hover:text-slate-100"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-2">
              <Building2 className="h-8 w-8" />
              Deal Audit Trail
            </h1>
            <p className="text-slate-400 mt-1">{auditTrail.deal.title || auditTrail.deal.deal_id}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => handleExport('csv')}
            variant="outline"
            size="sm"
            disabled={exporting}
          >
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
          <Button
            onClick={() => handleExport('excel')}
            variant="outline"
            size="sm"
            disabled={exporting}
          >
            <Download className="w-4 h-4 mr-2" />
            Export Excel
          </Button>
        </div>
      </div>

      {/* Deal Information */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Deal Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-slate-400 mb-1">Deal ID</p>
              <p className="text-slate-100 font-medium">{auditTrail.deal.deal_id}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400 mb-1">Status</p>
              <p className="text-slate-100 font-medium capitalize">{auditTrail.deal.status}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400 mb-1">Created</p>
              <p className="text-slate-100 font-medium text-sm">
                {new Date(auditTrail.deal.created_at).toLocaleDateString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-400 mb-1">Last Updated</p>
              <p className="text-slate-100 font-medium text-sm">
                {new Date(auditTrail.deal.updated_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate-300">Total Audit Logs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-100">
              {auditTrail.summary.total_logs}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate-300">Policy Decisions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-100">
              {auditTrail.summary.total_policy_decisions}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate-300">Date Range</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-slate-400">
              {auditTrail.summary.date_range.start ? (
                <>
                  {new Date(auditTrail.summary.date_range.start).toLocaleDateString()} -{' '}
                  {auditTrail.summary.date_range.end
                    ? new Date(auditTrail.summary.date_range.end).toLocaleDateString()
                    : 'Present'}
                </>
              ) : (
                'All time'
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <AuditFilters
            filters={filters}
            onFilterChange={handleFilterChange}
          />
        </CardContent>
      </Card>

      {/* Policy Decisions */}
      {auditTrail.policy_decisions && auditTrail.policy_decisions.length > 0 && (
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Policy Decisions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {auditTrail.policy_decisions.map((decision) => (
                <div
                  key={decision.id}
                  className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    {getDecisionIcon(decision.decision)}
                    <div>
                      <p className="text-sm font-medium text-slate-100">
                        {decision.decision} - {decision.rule_applied || 'No rule'}
                      </p>
                      <p className="text-xs text-slate-400">
                        Transaction: {decision.transaction_id}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500">
                    {new Date(decision.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Audit Timeline */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Audit Timeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AuditTimeline
            events={auditTrail.audit_logs}
            onEventClick={(event) => navigate(`/auditor/logs/${event.id}`)}
            height={600}
          />
        </CardContent>
      </Card>
    </div>
  );
}
