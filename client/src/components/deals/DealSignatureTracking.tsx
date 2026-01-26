// #region agent log
/*
fetch('http://127.0.0.1:7242/ingest/b4962ed0-f261-4fa9-86f3-a557335b330a',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client/src/components/deals/DealSignatureTracking.tsx:start',message:'Creating DealSignatureTracking component',data:{todoId:'phase1-issue007-021'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
*/
// #endregion
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Clock, XCircle, AlertTriangle } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useFDC3, createDealSignatureContext } from '@/context/FDC3Context';

interface DealSignatureTrackingProps {
  dealId: number;
}

interface SignatureStatus {
  deal_id: number;
  required_signatures: Array<{ name: string; email: string; role: string }>;
  completed_signatures: Array<{ signer_email: string; signed_at: string; signature_id: number }>;
  signature_status: string;
  signature_progress: number;
  signature_deadline: string | null;
}

export function DealSignatureTracking({ dealId }: DealSignatureTrackingProps) {
  const { broadcast } = useFDC3();
  const [status, setStatus] = useState<SignatureStatus | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadStatus();
  }, [dealId]);
  
  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth(`/api/deals/${dealId}/signature-status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        
        // Broadcast FDC3 context on status update
        if (data && broadcast) {
          try {
            const context = createDealSignatureContext(dealId, data);
            await broadcast(context);
          } catch (error) {
            console.warn('Failed to broadcast FDC3 context:', error);
          }
        }
      }
    } catch (error) {
      console.error('Failed to load signature status:', error);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return <div className="p-4">Loading signature status...</div>;
  }
  
  if (!status) {
    return <div className="p-4 text-slate-400">No signature requirements defined</div>;
  }
  
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-600">Completed</Badge>;
      case 'in_progress':
        return <Badge className="bg-yellow-600">In Progress</Badge>;
      case 'expired':
        return <Badge className="bg-red-600">Expired</Badge>;
      default:
        return <Badge className="bg-slate-600">Pending</Badge>;
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Signature Status</CardTitle>
            <CardDescription>Required signatures for this deal</CardDescription>
          </div>
          {getStatusBadge(status.signature_status)}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Progress</span>
            <span className="text-sm font-semibold">{status.signature_progress}%</span>
          </div>
          <Progress value={status.signature_progress} className="h-2" />
        </div>
        
        {/* Deadline */}
        {status.signature_deadline && (
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-slate-400" />
            <span className="text-slate-400">Deadline:</span>
            <span>{new Date(status.signature_deadline).toLocaleDateString()}</span>
          </div>
        )}
        
        {/* Required Signatures List */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Required Signatures</h4>
          {status.required_signatures.map((sig, idx) => {
            const completed = status.completed_signatures.some(
              c => c.signer_email === sig.email
            );
            const completedSig = status.completed_signatures.find(
              c => c.signer_email === sig.email
            );
            
            return (
              <div
                key={idx}
                className={`flex items-center justify-between p-3 rounded ${
                  completed ? 'bg-green-900/20 border border-green-600/50' : 'bg-slate-800 border border-slate-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  {completed ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  ) : (
                    <Clock className="h-5 w-5 text-yellow-600" />
                  )}
                  <div>
                    <p className="text-sm font-medium">{sig.name}</p>
                    <p className="text-xs text-slate-400">{sig.role} • {sig.email}</p>
                  </div>
                </div>
                {completed && completedSig && (
                  <div className="text-xs text-slate-400">
                    Signed: {new Date(completedSig.signed_at).toLocaleDateString()}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
