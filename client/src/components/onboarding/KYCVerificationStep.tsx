import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Clock, AlertCircle, ShieldCheck, Loader2, Upload, ExternalLink } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface KYCVerificationStepProps {
  onComplete: (data: any) => void;
  role: string;
}

export function KYCVerificationStep({ onComplete, role }: KYCVerificationStepProps) {
  const [status, setStatus] = useState<'idle' | 'initiating' | 'pending' | 'completed' | 'error'>('idle');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verificationData, setVerificationData] = useState<any>(null);
  const [evaluation, setEvaluation] = useState<any>(null);

  useEffect(() => {
    // Automatically initiate KYC and load current status on mount
    initiateKYC();
    pollStatus();
  }, []);

  const initiateKYC = async () => {
    setLoading(true);
    setStatus('initiating');
    setError(null);
    try {
      const res = await fetchWithAuth('/api/kyc/initiate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level: role === 'banker' || role === 'admin' ? 'enhanced' : 'standard' }),
      });
      if (!res.ok) {
        throw new Error('Failed to initiate KYC process');
      }
      const data = await res.json();
      setVerificationData(data.verification);
      setStatus('pending');
      // After initiating, refresh status/evaluation
      pollStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initiate KYC');
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const pollStatus = async () => {
    try {
      const res = await fetchWithAuth('/api/kyc/status');
      if (!res.ok) {
        return;
      }
      const data = await res.json();
      if (data.verification) {
        setVerificationData(data.verification);
      }
      if (data.evaluation) {
        setEvaluation(data.evaluation);
        if (data.evaluation.compliant) {
          setStatus('completed');
          onComplete({
            status: 'completed',
            decision: data.evaluation.decision,
            rule_applied: data.evaluation.rule_applied,
          });
        }
      }
    } catch (err) {
      // Non-fatal for now; keep UI responsive
      console.warn('Failed to poll KYC status', err);
    }
  };

  const handleSimulateVerification = async () => {
    // Temporary button: trigger an explicit evaluation + status refresh
    setLoading(true);
    setError(null);
    try {
      await fetchWithAuth('/api/kyc/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      await pollStatus();
    } catch (err) {
      setError('Verification evaluation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 py-4">
      <div className="flex items-center gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div className="h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center">
          <ShieldCheck className="h-6 w-6 text-emerald-500" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-slate-100 text-lg text-left">Identity Verification (KYC)</h3>
          <p className="text-sm text-slate-400 text-left">Regulatory compliance required for financial transactions.</p>
        </div>
        <Badge variant="outline" className={status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-2 text-left">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              Requirements
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between text-xs p-2 rounded bg-slate-950/50">
              <span className="text-slate-300">Identity Document</span>
              <span className="text-slate-500 italic">
                {verificationData?.identity_verified ? 'Verified' : 'Pending'}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs p-2 rounded bg-slate-950/50">
              <span className="text-slate-300">Proof of Address</span>
              <span className="text-slate-500 italic">
                {verificationData?.address_verified ? 'Verified' : 'Pending'}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs p-2 rounded bg-slate-950/50">
              <span className="text-slate-300">Sanctions Screening</span>
              <span className="text-slate-500 italic">
                {verificationData?.sanctions_check_passed ? 'Passed' : 'Pending'}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-2 text-left">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <ExternalLink className="h-4 w-4 text-blue-400" />
              PeopleHub Integration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-[11px] text-slate-400 text-left leading-relaxed">
              We use PeopleHub-style research workflows to enrich and validate identity data.
              Once your documents and checks are complete, this step will automatically mark as verified.
            </p>
            <Button
              size="sm"
              variant="outline"
              className="w-full h-8 text-xs border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
              onClick={pollStatus}
            >
              Refresh PeopleHub Status
            </Button>
            {evaluation && (
              <p className="text-[11px] text-left text-slate-400">
                Policy decision: <span className="font-semibold text-slate-200">{evaluation.decision}</span>
                {evaluation.rule_applied && (
                  <> · Rule: <span className="text-slate-300">{evaluation.rule_applied}</span></>
                )}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/50 flex items-center gap-3 text-red-400 text-xs text-left">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="pt-4 border-t border-slate-800 flex justify-end gap-3">
        <Button 
          className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
          onClick={handleSimulateVerification}
          disabled={loading}
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Verifying...
            </>
          ) : (
            'Complete Verification'
          )}
        </Button>
      </div>
    </div>
  );
}
