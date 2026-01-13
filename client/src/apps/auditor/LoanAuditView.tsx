import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchWithAuth } from '@/context/AuthContext';
import { AuditTimeline } from '@/components/audit/AuditTimeline';
import type { AuditEvent } from '@/components/audit/AuditTimeline';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Download, DollarSign, Shield, TrendingUp, AlertTriangle } from 'lucide-react';

interface LoanAuditTrail {
  loan: {
    id: number;
    loan_id: string;
    risk_status: string;
    last_verified_score: number | null;
    created_at: string;
    last_verified_at: string | null;
  };
  audit_logs: AuditEvent[];
  policy_decisions: Array<{
    id: number;
    transaction_id: string;
    decision: string;
    rule_applied: string;
    created_at: string;
  }>;
  verification_logs: Array<{
    id: number;
    action: string;
    created_at: string;
  }>;
  summary: {
    total_logs: number;
    total_policy_decisions: number;
    total_verification_logs: number;
    date_range: {
      start: string | null;
      end: string | null;
    };
  };
}

export function LoanAuditView() {
  const { loanId } = useParams<{ loanId: string }>();
  const navigate = useNavigate();
  const [auditTrail, setAuditTrail] = useState<LoanAuditTrail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const fetchAuditTrail = async () => {
      if (!loanId) return;
      
      try {
        setLoading(true);
        setError(null);
        const response = await fetchWithAuth(`/api/auditor/loans/${loanId}/audit`);
        if (!response.ok) {
          throw new Error('Failed to load loan audit trail');
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
  }, [loanId]);

  const handleExport = async (format: 'csv' | 'excel' | 'pdf') => {
    if (!auditTrail) return;
    
    try {
      setExporting(true);
      const params = new URLSearchParams();
      params.append('format', format);
      
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
      a.download = `loan_${loanId}_audit_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : format}`;
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

  const getRiskStatusColor = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'COMPLIANT':
        return 'text-green-400';
      case 'WARNING':
        return 'text-yellow-400';
      case 'PENDING':
        return 'text-blue-400';
      case 'ERROR':
        return 'text-red-400';
      default:
        return 'text-slate-400';
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
          Error: {error || 'Loan audit trail not found'}
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
              <DollarSign className="h-8 w-8" />
              Loan Audit Trail
            </h1>
            <p className="text-slate-400 mt-1">Loan ID: {auditTrail.loan.loan_id}</p>
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
        </div>
      </div>

      {/* Loan Information */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Loan Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-slate-400 mb-1">Loan ID</p>
              <p className="text-slate-100 font-medium">{auditTrail.loan.loan_id}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400 mb-1">Risk Status</p>
              <p className={`font-medium ${getRiskStatusColor(auditTrail.loan.risk_status)}`}>
                {auditTrail.loan.risk_status}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-400 mb-1">NDVI Score</p>
              <p className="text-slate-100 font-medium">
                {auditTrail.loan.last_verified_score !== null
                  ? auditTrail.loan.last_verified_score.toFixed(2)
                  : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-400 mb-1">Last Verified</p>
              <p className="text-slate-100 font-medium text-sm">
                {auditTrail.loan.last_verified_at
                  ? new Date(auditTrail.loan.last_verified_at).toLocaleDateString()
                  : 'Never'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
            <CardTitle className="text-sm font-medium text-slate-300">Verification Logs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-100">
              {auditTrail.summary.total_verification_logs}
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

      {/* Verification History */}
      {auditTrail.verification_logs && auditTrail.verification_logs.length > 0 && (
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Verification History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {auditTrail.verification_logs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    <div>
                      <p className="text-sm font-medium text-slate-100 capitalize">
                        {log.action}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500">
                    {new Date(log.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

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
                  <div>
                    <p className="text-sm font-medium text-slate-100">
                      {decision.decision} - {decision.rule_applied || 'No rule'}
                    </p>
                    <p className="text-xs text-slate-400">
                      Transaction: {decision.transaction_id}
                    </p>
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
          <CardTitle className="text-slate-100">Audit Timeline</CardTitle>
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
