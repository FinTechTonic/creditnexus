import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth, fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { 
  ArrowLeft,
  Building2,
  Calendar,
  Clock,
  FileText,
  MessageSquare,
  Plus,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Eye,
  Edit,
  Trash2,
  RefreshCw,
  ChevronRight,
  Share2
} from 'lucide-react';
import { SkeletonDocumentList } from '@/components/ui/skeleton';
import { DealTimeline, type TimelineEvent as DealTimelineEvent } from '@/components/DealTimeline';
import { FilingRequirementsPanel } from '@/components/FilingRequirementsPanel';
import { NotarizationPayment } from '@/components/NotarizationPayment';

interface Deal {
  id: number;
  deal_id: string;
  applicant_id: number;
  application_id: number | null;
  status: string;
  deal_type: string | null;
  deal_data: Record<string, unknown> | null;
  folder_path: string | null;
  created_at: string;
  updated_at: string;
}

interface Document {
  id: number;
  title: string;
  borrower_name: string | null;
  created_at: string;
  updated_at: string;
}

interface DealNote {
  id: number;
  deal_id: number;
  user_id: number;
  content: string;
  note_type: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

interface TimelineEvent {
  event_type: string;
  timestamp: string | null;
  data: Record<string, unknown>;
  status?: 'success' | 'failure' | 'pending' | 'review_needed' | 'warning';
  verification_step?: boolean;
  requires_review?: boolean;
  branch_id?: string;
  parent_branch?: string;
}

export function DealDetail() {
  const { dealId } = useParams<{ dealId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [deal, setDeal] = useState<Deal | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [notes, setNotes] = useState<DealNote[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newNoteContent, setNewNoteContent] = useState('');
  const [newNoteType, setNewNoteType] = useState('general');
  const [submittingNote, setSubmittingNote] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'notes' | 'timeline' | 'filings'>('overview');

  useEffect(() => {
    if (dealId) {
      fetchDealDetail();
    }
  }, [dealId]);

  const fetchDealDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `/api/deals/${dealId}`;
      const response = await fetchWithAuth(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to fetch deal');
      }
      const data = await response.json();
      setDeal(data.deal);
      setDocuments(data.documents || []);
      setNotes(data.notes || []);
      setTimeline(data.timeline || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load deal');
    } finally {
      setLoading(false);
    }
  };

  const handleAddNote = async () => {
    if (!newNoteContent.trim() || !dealId) return;

    setSubmittingNote(true);
    setError(null);
    try {
      const response = await fetchWithAuth(`/api/deals/${dealId}/notes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: newNoteContent,
          note_type: newNoteType,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to add note');
      }

      const data = await response.json();
      setNotes([data.note, ...notes]);
      setNewNoteContent('');
      setNewNoteType('general');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add note');
    } finally {
      setSubmittingNote(false);
    }
  };

  const handleDeleteNote = async (noteId: number) => {
    if (!confirm('Are you sure you want to delete this note?')) return;

    try {
      const response = await fetchWithAuth(`/api/deals/${dealId}/notes/${noteId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete note');
      }

      setNotes(notes.filter(note => note.id !== noteId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete note');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft':
        return 'bg-slate-500 text-white';
      case 'submitted':
        return 'bg-blue-500 text-white';
      case 'under_review':
        return 'bg-yellow-500 text-white';
      case 'approved':
        return 'bg-emerald-500 text-white';
      case 'rejected':
        return 'bg-red-500 text-white';
      case 'active':
        return 'bg-green-500 text-white';
      case 'closed':
        return 'bg-gray-500 text-white';
      case 'restructuring':
        return 'bg-orange-500 text-white';
      case 'withdrawn':
        return 'bg-gray-500 text-white';
      default:
        return 'bg-slate-500 text-white';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
      case 'active':
        return <CheckCircle className="h-4 w-4" />;
      case 'rejected':
      case 'closed':
        return <XCircle className="h-4 w-4" />;
      case 'submitted':
      case 'under_review':
        return <Clock className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const formatDealType = (dealType: string | null) => {
    if (!dealType) return 'N/A';
    return dealType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const formatEventType = (eventType: string) => {
    return eventType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonDocumentList count={3} />
      </div>
    );
  }

  if (error || !deal) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/dashboard/deals')}
            className="text-slate-400 hover:text-slate-100"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Deals
          </Button>
        </div>
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle className="h-5 w-5" />
              <span>{error || 'Deal not found'}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/dashboard/deals')}
            className="text-slate-400 hover:text-slate-100"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Deals
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-slate-100">{deal.deal_id}</h1>
            <p className="text-slate-400 mt-1">Deal Details</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            onClick={() => navigate(`/app/workflow/share?view=create&dealId=${deal.id}`)}
            className="text-slate-400 hover:text-slate-100"
            title="Share workflow link for this deal"
          >
            <Share2 className="h-4 w-4 mr-2" />
            Share Workflow
          </Button>
          <Button
            variant="ghost"
            onClick={fetchDealDetail}
            className="text-slate-400 hover:text-slate-100"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 flex items-center gap-2 text-red-400">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {/* Deal Info Card */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Deal Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-slate-400">Status:</span>
              <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 w-fit ${getStatusColor(deal.status)}`}>
                {getStatusIcon(deal.status)}
                {deal.status.replace(/_/g, ' ').toUpperCase()}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Type:</span>
              <span className="text-slate-100 ml-2">{formatDealType(deal.deal_type)}</span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-slate-400" />
              <span className="text-slate-400">Created:</span>
              <span className="text-slate-100">{new Date(deal.created_at).toLocaleDateString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-slate-400" />
              <span className="text-slate-400">Updated:</span>
              <span className="text-slate-100">{new Date(deal.updated_at).toLocaleDateString()}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-700">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'overview'
              ? 'text-emerald-400 border-b-2 border-emerald-400'
              : 'text-slate-400 hover:text-slate-100'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('documents')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'documents'
              ? 'text-emerald-400 border-b-2 border-emerald-400'
              : 'text-slate-400 hover:text-slate-100'
          }`}
        >
          Documents ({documents.length})
        </button>
        <button
          onClick={() => setActiveTab('notes')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'notes'
              ? 'text-emerald-400 border-b-2 border-emerald-400'
              : 'text-slate-400 hover:text-slate-100'
          }`}
        >
          Notes ({notes.length})
        </button>
        <button
          onClick={() => setActiveTab('timeline')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'timeline'
              ? 'text-emerald-400 border-b-2 border-emerald-400'
              : 'text-slate-400 hover:text-slate-100'
          }`}
        >
          Timeline ({timeline?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('filings')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'filings'
              ? 'text-emerald-400 border-b-2 border-emerald-400'
              : 'text-slate-400 hover:text-slate-100'
          }`}
        >
          Filings
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6">
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-2">Deal Summary</h3>
                  <p className="text-slate-400">
                    Deal ID: <span className="text-slate-100">{deal.deal_id}</span>
                  </p>
                  {deal.application_id && (
                    <p className="text-slate-400 mt-2">
                      Application ID: <span className="text-slate-100">{deal.application_id}</span>
                    </p>
                  )}
                </div>
                {deal.deal_data && Object.keys(deal.deal_data).length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-2">Deal Data</h3>
                    <pre className="bg-slate-900 p-4 rounded-lg text-sm text-slate-300 overflow-auto">
                      {JSON.stringify(deal.deal_data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Notarization Payment Component */}
          <NotarizationPayment
            dealId={deal.id}
            onPaymentComplete={(transactionHash) => {
              // Refresh deal details after payment
              fetchDealDetail();
              console.log('Payment completed:', transactionHash);
            }}
            onPaymentSkipped={() => {
              // Refresh deal details after skip
              fetchDealDetail();
            }}
            onError={(error) => {
              setError(error);
            }}
          />
        </div>
      )}

      {activeTab === 'documents' && (
        <div className="space-y-4">
          {documents.length === 0 ? (
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-6 text-center text-slate-400">
                No documents attached to this deal
              </CardContent>
            </Card>
          ) : (
            documents.map((doc) => (
              <Card key={doc.id} className="bg-slate-800 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-5 w-5 text-slate-400" />
                        <h3 className="text-lg font-semibold text-slate-100">{doc.title}</h3>
                      </div>
                      {doc.borrower_name && (
                        <p className="text-slate-400">Borrower: {doc.borrower_name}</p>
                      )}
                      <p className="text-sm text-slate-500 mt-2">
                        Created: {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/app/document-parser?documentId=${doc.id}`)}
                        className="text-slate-400 hover:text-slate-100"
                        title="View extraction"
                      >
                        <FileText className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/app/ground-truth?documentId=${doc.id}`)}
                        className="text-slate-400 hover:text-slate-100"
                        title="Verify document"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/dashboard/documents/${doc.id}`)}
                        className="text-slate-400 hover:text-slate-100"
                        title="View document details"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'notes' && (
        <div className="space-y-4">
          {/* Add Note Form */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Add Note</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Note Type</label>
                  <select
                    value={newNoteType}
                    onChange={(e) => setNewNoteType(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="general">General</option>
                    <option value="verification">Verification</option>
                    <option value="status_change">Status Change</option>
                    <option value="review">Review</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Content</label>
                  <Textarea
                    value={newNoteContent}
                    onChange={(e) => setNewNoteContent(e.target.value)}
                    placeholder="Enter note content..."
                    className="bg-slate-900 border-slate-700 text-slate-100 placeholder-slate-500"
                    rows={4}
                  />
                </div>
                <Button
                  onClick={handleAddNote}
                  disabled={!newNoteContent.trim() || submittingNote}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  {submittingNote ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Add Note
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Notes List */}
          {notes.length === 0 ? (
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-6 text-center text-slate-400">
                No notes yet. Add your first note above.
              </CardContent>
            </Card>
          ) : (
            notes.map((note) => (
              <Card key={note.id} className="bg-slate-800 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <MessageSquare className="h-4 w-4 text-slate-400" />
                        <span className="text-sm text-slate-400">
                          {note.note_type || 'general'} • {new Date(note.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-slate-100 whitespace-pre-wrap">{note.content}</p>
                    </div>
                    {note.user_id === user?.id && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteNote(note.id)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'timeline' && (
        <div className="space-y-4">
          <DealTimeline
            events={timeline as DealTimelineEvent[]}
            dealStatus={deal?.status}
            className="w-full"
          />
        </div>
      )}

      {activeTab === 'filings' && (
        <div className="space-y-4">
          {documents.length === 0 ? (
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-6 text-center text-slate-400">
                No documents available for filing requirements
              </CardContent>
            </Card>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="space-y-4">
                <Card className="bg-slate-800 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-slate-100 flex items-center gap-2">
                      <FileText className="h-5 w-5" />
                      {doc.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <FilingRequirementsPanel
                      documentId={doc.id}
                      dealId={deal.id}
                      agreementType="facility_agreement"
                    />
                  </CardContent>
                </Card>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
