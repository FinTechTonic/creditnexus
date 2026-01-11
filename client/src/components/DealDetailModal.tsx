import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
  X, 
  FileText, 
  Building2, 
  Calendar, 
  DollarSign, 
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  Eye,
  Download,
  RefreshCw,
  Code
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import type { DemoDeal } from './DemoDealCard';

interface Document {
  id: number;
  title: string;
  borrower_name?: string;
  created_at: string;
  workflow_state?: string;
  filename?: string;
}

interface Workflow {
  id: number;
  document_id: number;
  state: string;
  assigned_to?: number;
  priority?: string;
  due_date?: string;
  created_at: string;
}

interface DealDetailModalProps {
  deal: DemoDeal | null;
  open: boolean;
  onClose: () => void;
  onViewDocument?: (documentId: number) => void;
  onDownloadDocument?: (documentId: number) => void;
}

export function DealDetailModal({
  deal,
  open,
  onClose,
  onViewDocument,
  onDownloadDocument
}: DealDetailModalProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [cdmData, setCdmData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'workflows' | 'cdm'>('overview');

  useEffect(() => {
    if (open && deal) {
      fetchDealDetails();
    } else {
      // Reset state when modal closes
      setDocuments([]);
      setWorkflows([]);
      setCdmData(null);
      setError(null);
      setActiveTab('overview');
    }
  }, [open, deal]);

  const fetchDealDetails = async () => {
    if (!deal) return;

    setLoading(true);
    setError(null);

    try {
      // Fetch deal details with documents and workflows
      const response = await fetchWithAuth(`/api/deals/${deal.id}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch deal details');
      }

      const data = await response.json();
      setDocuments(data.documents || []);
      setWorkflows(data.workflows || []);
      
      // Try to extract CDM data from deal_data
      if (data.deal?.deal_data) {
        setCdmData(data.deal.deal_data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load deal details');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number | undefined, currency: string = 'USD') => {
    if (!amount) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
      submitted: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      under_review: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      approved: 'bg-green-500/20 text-green-300 border-green-500/30',
      rejected: 'bg-red-500/20 text-red-300 border-red-500/30',
      active: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      closed: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
    };
    return colors[status] || 'bg-slate-500/20 text-slate-300 border-slate-500/30';
  };

  const getWorkflowStateColor = (state: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-300',
      in_progress: 'bg-blue-500/20 text-blue-300',
      completed: 'bg-green-500/20 text-green-300',
      rejected: 'bg-red-500/20 text-red-300',
    };
    return colors[state] || 'bg-slate-500/20 text-slate-300';
  };

  if (!deal) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-2xl font-bold text-white">
                {deal.deal_id}
              </DialogTitle>
              <DialogDescription className="text-slate-400 mt-1">
                Deal Details and Information
              </DialogDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
          </div>
        ) : error ? (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
            {error}
          </div>
        ) : (
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="mt-4">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="documents">
                Documents ({documents.length})
              </TabsTrigger>
              <TabsTrigger value="workflows">
                Workflows ({workflows.length})
              </TabsTrigger>
              <TabsTrigger value="cdm">CDM Data</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-slate-400">Deal Information</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">Status:</span>
                      <span className={`text-xs px-2 py-0.5 rounded border ${getStatusColor(deal.status)}`}>
                        {deal.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">Type:</span>
                      <span className="text-sm text-white capitalize">
                        {deal.deal_type.replace('_', ' ')}
                      </span>
                    </div>
                    {deal.borrower_name && (
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-slate-400" />
                        <span className="text-sm text-white">{deal.borrower_name}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-slate-400" />
                      <span className="text-sm text-slate-300">{formatDate(deal.created_at)}</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-slate-400">Financial Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-4 h-4 text-slate-400" />
                      <span className="text-lg font-semibold text-white">
                        {formatCurrency(
                          deal.total_commitment || deal.deal_data?.loan_amount,
                          deal.currency
                        )}
                      </span>
                    </div>
                    {deal.deal_data?.interest_rate && (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">Interest Rate:</span>
                        <span className="text-sm text-white">{deal.deal_data.interest_rate}%</span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-slate-400">Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-slate-300">
                    This deal has {documents.length} associated document(s) and {workflows.length} workflow(s).
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="documents" className="mt-4">
              {documents.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  No documents found for this deal.
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <Card key={doc.id} className="hover:border-indigo-500/50 transition-colors">
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                              <h4 className="text-sm font-semibold text-white truncate">
                                {doc.title}
                              </h4>
                            </div>
                            {doc.borrower_name && (
                              <p className="text-xs text-slate-400">{doc.borrower_name}</p>
                            )}
                            <p className="text-xs text-slate-500 mt-1">
                              Created: {formatDate(doc.created_at)}
                            </p>
                            {doc.workflow_state && (
                              <span className={`text-xs px-2 py-0.5 rounded mt-2 inline-block ${getWorkflowStateColor(doc.workflow_state)}`}>
                                {doc.workflow_state.replace('_', ' ')}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 ml-4">
                            {onViewDocument && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onViewDocument(doc.id)}
                              >
                                <Eye className="w-4 h-4" />
                              </Button>
                            )}
                            {onDownloadDocument && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onDownloadDocument(doc.id)}
                              >
                                <Download className="w-4 h-4" />
                              </Button>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="workflows" className="mt-4">
              {workflows.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  No workflows found for this deal.
                </div>
              ) : (
                <div className="space-y-2">
                  {workflows.map((workflow) => (
                    <Card key={workflow.id} className="hover:border-indigo-500/50 transition-colors">
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className={`text-xs px-2 py-0.5 rounded ${getWorkflowStateColor(workflow.state)}`}>
                                {workflow.state.replace('_', ' ').toUpperCase()}
                              </span>
                              {workflow.priority && (
                                <span className="text-xs text-slate-400">
                                  Priority: {workflow.priority}
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-400">
                              Document ID: {workflow.document_id}
                            </p>
                            {workflow.due_date && (
                              <p className="text-xs text-slate-500 mt-1">
                                Due: {formatDate(workflow.due_date)}
                              </p>
                            )}
                            <p className="text-xs text-slate-500 mt-1">
                              Created: {formatDate(workflow.created_at)}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="cdm" className="mt-4">
              {cdmData ? (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                      <Code className="w-4 h-4" />
                      CDM Data Preview
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs bg-slate-900 p-4 rounded-lg overflow-x-auto text-slate-300 font-mono">
                      {JSON.stringify(cdmData, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  No CDM data available for this deal.
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          {loading && (
            <Button variant="ghost" onClick={fetchDealDetails} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
