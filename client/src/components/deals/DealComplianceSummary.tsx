// #region agent log
/*
fetch('http://127.0.0.1:7242/ingest/b4962ed0-f261-4fa9-86f3-a557335b330a',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client/src/components/deals/DealComplianceSummary.tsx:start',message:'Creating DealComplianceSummary component',data:{todoId:'phase1-issue007-026'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
*/
// #endregion
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, AlertTriangle, FileText, FileCheck } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { DealSignatureTracking } from './DealSignatureTracking';
import { DealDocumentationTracking } from './DealDocumentationTracking';

interface DealComplianceSummaryProps {
  dealId: number;
}

interface ComplianceSummary {
  deal_id: number;
  compliance_status: string;
  signature_status: {
    deal_id: number;
    required_signatures: Array<{ name: string; email: string; role: string }>;
    completed_signatures: Array<{ signer_email: string; signed_at: string; signature_id: number }>;
    signature_status: string;
    signature_progress: number;
    signature_deadline: string | null;
  };
  documentation_status: {
    deal_id: number;
    required_documents: Array<{ document_type: string; document_category: string; required_by?: string }>;
    completed_documents: Array<{ document_id: number; document_type: string; document_category: string; completed_at: string }>;
    documentation_status: string;
    documentation_progress: number;
    documentation_deadline: string | null;
  };
  compliance_notes: string | null;
}

export function DealComplianceSummary({ dealId }: DealComplianceSummaryProps) {
  const [summary, setSummary] = useState<ComplianceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadSummary();
  }, [dealId]);
  
  const loadSummary = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth(`/api/deals/${dealId}/compliance-summary`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch (error) {
      console.error('Failed to load compliance summary:', error);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return <div className="p-4">Loading compliance summary...</div>;
  }
  
  if (!summary) {
    return <div className="p-4 text-slate-400">No compliance data available</div>;
  }
  
  const getComplianceBadge = (status: string) => {
    switch (status) {
      case 'compliant':
        return (
          <Badge className="bg-green-600 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Compliant
          </Badge>
        );
      case 'non_compliant':
        return (
          <Badge className="bg-red-600 flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Non-Compliant
          </Badge>
        );
      case 'pending_review':
        return (
          <Badge className="bg-yellow-600 flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Pending Review
          </Badge>
        );
      default:
        return <Badge className="bg-slate-600">Unknown</Badge>;
    }
  };
  
  const signatureComplete = summary.signature_status.signature_status === 'completed';
  const documentationComplete = summary.documentation_status.documentation_status === 'complete';
  
  return (
    <div className="space-y-6">
      {/* Overall Compliance Status Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Compliance Summary</CardTitle>
              <CardDescription>Overall compliance status for this deal</CardDescription>
            </div>
            {getComplianceBadge(summary.compliance_status)}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Status Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className={`p-4 rounded border ${
              signatureComplete ? 'bg-green-900/20 border-green-600/50' : 'bg-slate-800 border-slate-700'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {signatureComplete ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : (
                  <FileText className="h-5 w-5 text-yellow-600" />
                )}
                <span className="font-semibold">Signatures</span>
              </div>
              <p className="text-sm text-slate-400">
                {summary.signature_status.completed_signatures.length} of {summary.signature_status.required_signatures.length} completed
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Status: {summary.signature_status.signature_status}
              </p>
            </div>
            
            <div className={`p-4 rounded border ${
              documentationComplete ? 'bg-green-900/20 border-green-600/50' : 'bg-slate-800 border-slate-700'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {documentationComplete ? (
                  <FileCheck className="h-5 w-5 text-green-600" />
                ) : (
                  <FileText className="h-5 w-5 text-yellow-600" />
                )}
                <span className="font-semibold">Documentation</span>
              </div>
              <p className="text-sm text-slate-400">
                {summary.documentation_status.completed_documents.length} of {summary.documentation_status.required_documents.length} completed
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Status: {summary.documentation_status.documentation_status}
              </p>
            </div>
          </div>
          
          {/* Compliance Notes */}
          {summary.compliance_notes && (
            <div className="p-4 bg-slate-800 rounded border border-slate-700">
              <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                Compliance Notes
              </h4>
              <p className="text-sm text-slate-300 whitespace-pre-wrap">{summary.compliance_notes}</p>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Detailed Tracking Components */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DealSignatureTracking dealId={dealId} />
        <DealDocumentationTracking dealId={dealId} />
      </div>
    </div>
  );
}
