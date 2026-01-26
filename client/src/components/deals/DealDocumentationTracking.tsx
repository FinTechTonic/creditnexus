// #region agent log
/*
fetch('http://127.0.0.1:7242/ingest/b4962ed0-f261-4fa9-86f3-a557335b330a',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client/src/components/deals/DealDocumentationTracking.tsx:start',message:'Creating DealDocumentationTracking component',data:{todoId:'phase1-issue007-023'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
*/
// #endregion
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Clock, FileText, Eye } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface DealDocumentationTrackingProps {
  dealId: number;
}

interface DocumentationStatus {
  deal_id: number;
  required_documents: Array<{ document_type: string; document_category: string; required_by?: string }>;
  completed_documents: Array<{ document_id: number; document_type: string; document_category: string; completed_at: string }>;
  documentation_status: string;
  documentation_progress: number;
  documentation_deadline: string | null;
}

export function DealDocumentationTracking({ dealId }: DealDocumentationTrackingProps) {
  const navigate = useNavigate();
  const [status, setStatus] = useState<DocumentationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadStatus();
  }, [dealId]);
  
  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth(`/api/deals/${dealId}/documentation-status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (error) {
      console.error('Failed to load documentation status:', error);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return <div className="p-4">Loading documentation status...</div>;
  }
  
  if (!status) {
    return <div className="p-4 text-slate-400">No documentation requirements defined</div>;
  }
  
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'complete':
        return <Badge className="bg-green-600">Complete</Badge>;
      case 'in_progress':
        return <Badge className="bg-yellow-600">In Progress</Badge>;
      case 'non_compliant':
        return <Badge className="bg-red-600">Non-Compliant</Badge>;
      default:
        return <Badge className="bg-slate-600">Pending</Badge>;
    }
  };
  
  const handleViewDocument = (documentId: number) => {
    navigate(`/dashboard/documents/${documentId}`);
  };
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Documentation Status</CardTitle>
            <CardDescription>Required documents for this deal</CardDescription>
          </div>
          {getStatusBadge(status.documentation_status)}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Progress</span>
            <span className="text-sm font-semibold">{status.documentation_progress}%</span>
          </div>
          <Progress value={status.documentation_progress} className="h-2" />
        </div>
        
        {/* Deadline */}
        {status.documentation_deadline && (
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-slate-400" />
            <span className="text-slate-400">Deadline:</span>
            <span>{new Date(status.documentation_deadline).toLocaleDateString()}</span>
          </div>
        )}
        
        {/* Required Documents List */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Required Documents</h4>
          {status.required_documents.map((doc, idx) => {
            const completed = status.completed_documents.some(
              c => c.document_type === doc.document_type && c.document_category === doc.document_category
            );
            const completedDoc = status.completed_documents.find(
              c => c.document_type === doc.document_type && c.document_category === doc.document_category
            );
            
            return (
              <div
                key={idx}
                className={`flex items-center justify-between p-3 rounded ${
                  completed ? 'bg-green-900/20 border border-green-600/50' : 'bg-slate-800 border border-slate-700'
                }`}
              >
                <div className="flex items-center gap-3 flex-1">
                  {completed ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  ) : (
                    <FileText className="h-5 w-5 text-yellow-600" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm font-medium">{doc.document_type}</p>
                    <p className="text-xs text-slate-400">
                      {doc.document_category}
                      {doc.required_by && ` • Required by: ${doc.required_by}`}
                    </p>
                    {completed && completedDoc && (
                      <p className="text-xs text-slate-400 mt-1">
                        Completed: {new Date(completedDoc.completed_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
                {completed && completedDoc && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleViewDocument(completedDoc.document_id)}
                    className="ml-2"
                  >
                    <Eye className="h-4 w-4 mr-1" />
                    View
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
