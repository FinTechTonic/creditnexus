import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle, FileText, User, ShieldCheck, Globe, Clock } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface AuditLog {
  id: number;
  action: string;
  target_type: string;
  target_id?: number;
  user_id?: number;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
  action_metadata?: Record<string, any>;
}

export function SignatureAuditTrail({ signatureId }: { signatureId?: number }) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAuditLogs();
  }, [signatureId]);

  const loadAuditLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      // Backend should have a generic audit log endpoint
      // GET /api/audit-logs?target_type=signature_request&target_id=...
      const url = signatureId 
        ? `/api/audit-logs?target_type=signature_request&target_id=${signatureId}`
        : '/api/audit-logs?target_type=signature_request';
        
      const res = await fetchWithAuth(url);
      if (!res.ok) {
        throw new Error('Failed to load audit trail');
      }
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (err) {
      // Fail gracefully - might not have generic endpoint yet
      console.warn('Audit trail endpoint not yet fully compatible:', err);
      setLogs([]); 
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {logs.length === 0 ? (
        <div className="p-8 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg">
          <ShieldCheck className="h-10 w-10 mx-auto mb-3 opacity-20" />
          <p className="text-sm">No audit entries found for this signature.</p>
        </div>
      ) : (
        <div className="relative border-l-2 border-slate-800 ml-3 pl-6 space-y-6 py-2">
          {logs.map((log) => (
            <div key={log.id} className="relative">
              <div className="absolute -left-[33px] top-0 h-4 w-4 rounded-full bg-slate-900 border-2 border-slate-700" />
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="h-5 text-[10px] uppercase font-bold bg-slate-800 text-slate-300 border-slate-700">
                    {log.action}
                  </Badge>
                  <span className="text-xs text-slate-500 font-medium">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="bg-slate-900/40 rounded-lg border border-slate-800 p-3 mt-1">
                  <div className="grid grid-cols-2 gap-y-2 text-xs">
                    <div className="flex items-center gap-2 text-slate-400">
                      <User className="h-3 w-3" />
                      <span>User ID: {log.user_id || 'System'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-400">
                      <Globe className="h-3 w-3" />
                      <span>IP: {log.ip_address || 'Unknown'}</span>
                    </div>
                    {log.action_metadata && Object.entries(log.action_metadata).map(([k, v]) => (
                      <div key={k} className="col-span-2 flex gap-2">
                        <span className="text-slate-500 font-semibold uppercase text-[9px] min-w-[60px]">{k}:</span>
                        <span className="text-slate-300 font-mono truncate">{JSON.stringify(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
