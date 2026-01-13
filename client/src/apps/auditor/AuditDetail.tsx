import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchWithAuth } from '@/context/AuthContext';
import { AuditTimeline } from '@/components/audit/AuditTimeline';
import type { AuditEvent } from '@/components/audit/AuditTimeline';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Download, User, Clock, FileText, Shield, AlertCircle, CheckCircle, XCircle } from 'lucide-react';

interface AuditLogDetail {
  log: AuditEvent & {
    ip_address?: string;
    user_agent?: string;
    action_metadata?: Record<string, any>;
  };
  related_events: AuditEvent[];
}

export function AuditDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [auditLog, setAuditLog] = useState<AuditLogDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const fetchAuditLog = async () => {
      if (!id) return;
      
      try {
        setLoading(true);
        setError(null);
        const response = await fetchWithAuth(`/api/auditor/logs/${id}`);
        if (!response.ok) {
          throw new Error('Failed to load audit log');
        }
        const data = await response.json();
        setAuditLog(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load audit log');
      } finally {
        setLoading(false);
      }
    };

    fetchAuditLog();
  }, [id]);

  const handleExport = async (format: 'json' | 'csv') => {
    if (!auditLog) return;
    
    try {
      setExporting(true);
      const response = await fetchWithAuth(
        `/api/auditor/logs/${id}/export?format=${format}`
      );
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_log_${id}.${format}`;
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

  const getActionIcon = (action: string) => {
    if (action.includes('create') || action.includes('approve')) {
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    }
    if (action.includes('delete') || action.includes('reject')) {
      return <XCircle className="h-5 w-5 text-red-500" />;
    }
    if (action.includes('update') || action.includes('edit')) {
      return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    }
    return <Clock className="h-5 w-5 text-blue-500" />;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (error || !auditLog) {
    return (
      <div className="p-6">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4 text-red-400">
          Error: {error || 'Audit log not found'}
        </div>
        <Button onClick={() => navigate('/auditor')} className="mt-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Button>
      </div>
    );
  }

  const log = auditLog.log;

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
            <h1 className="text-3xl font-bold text-slate-100">Audit Log Details</h1>
            <p className="text-slate-400 mt-1">ID: {log.id}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => handleExport('json')}
            variant="outline"
            size="sm"
            disabled={exporting}
          >
            <Download className="w-4 h-4 mr-2" />
            Export JSON
          </Button>
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Action Details */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100 flex items-center gap-2">
                {getActionIcon(log.action)}
                Action Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-400 mb-1">Action</p>
                  <p className="text-slate-100 font-medium capitalize">
                    {log.action.replace(/_/g, ' ')}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-400 mb-1">Target Type</p>
                  <p className="text-slate-100 font-medium capitalize">
                    {log.target_type}
                  </p>
                </div>
                {log.target_id && (
                  <div>
                    <p className="text-sm text-slate-400 mb-1">Target ID</p>
                    <p className="text-slate-100 font-medium">{log.target_id}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm text-slate-400 mb-1">Occurred At</p>
                  <p className="text-slate-100 font-medium">{formatDate(log.occurred_at)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* User Information */}
          {log.user && (
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <User className="h-5 w-5" />
                  User Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-400 mb-1">User ID</p>
                    <p className="text-slate-100 font-medium">{log.user.id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400 mb-1">Name</p>
                    <p className="text-slate-100 font-medium">{log.user.name}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-slate-400 mb-1">Email</p>
                    <p className="text-slate-100 font-medium">{log.user.email}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Request Information */}
          {(log.ip_address || log.user_agent) && (
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Request Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {log.ip_address && (
                  <div>
                    <p className="text-sm text-slate-400 mb-1">IP Address</p>
                    <p className="text-slate-100 font-medium">{log.ip_address}</p>
                  </div>
                )}
                {log.user_agent && (
                  <div>
                    <p className="text-sm text-slate-400 mb-1">User Agent</p>
                    <p className="text-slate-100 font-medium text-sm break-all">
                      {log.user_agent}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Metadata */}
          {log.action_metadata && Object.keys(log.action_metadata).length > 0 && (
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Metadata
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="bg-slate-900/50 p-4 rounded-lg text-sm text-slate-300 overflow-auto">
                  {JSON.stringify(log.action_metadata, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Related Events */}
        <div className="space-y-6">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Related Events</CardTitle>
            </CardHeader>
            <CardContent>
              {auditLog.related_events && auditLog.related_events.length > 0 ? (
                <AuditTimeline
                  events={auditLog.related_events}
                  onEventClick={(event) => navigate(`/auditor/logs/${event.id}`)}
                  height={600}
                />
              ) : (
                <p className="text-slate-400 text-center py-8">No related events</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
