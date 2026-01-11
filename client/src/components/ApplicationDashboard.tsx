import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  FileText, 
  Search, 
  Clock, 
  ChevronRight, 
  Loader2, 
  Plus,
  Filter,
  Edit,
  Send,
  CheckCircle,
  X,
  AlertCircle,
  Calendar,
  Building2,
  User,
  Trash2,
  Eye,
  Download,
  ArrowRightCircle
} from 'lucide-react';
import { useAuth, fetchWithAuth } from '@/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { SkeletonDocumentList, EmptyState } from '@/components/ui/skeleton';

interface Application {
  id: number;
  application_type: string;
  status: string;
  user_id: number | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  application_data: Record<string, unknown> | null;
  business_data: Record<string, unknown> | null;
  individual_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

type ApplicationStatus = 'draft' | 'submitted' | 'under_review' | 'approved' | 'rejected' | 'withdrawn';
type ApplicationType = 'individual' | 'business';

export function ApplicationDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<ApplicationStatus | 'all'>('all');
  const [filterType, setFilterType] = useState<ApplicationType | 'all'>('all');
  const [sortBy, setSortBy] = useState<'date' | 'status'>('date');
  const [searchQuery, setSearchQuery] = useState('');
  const [creatingDeal, setCreatingDeal] = useState<number | null>(null);

  useEffect(() => {
    fetchApplications();
  }, [filterStatus, filterType, sortBy]);

  const fetchApplications = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (filterStatus !== 'all') {
        params.append('status', filterStatus);
      }
      if (filterType !== 'all') {
        params.append('application_type', filterType);
      }
      params.append('page', '1');
      params.append('limit', '100');
      
      const response = await fetchWithAuth(`/api/applications?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch applications');
      }
      
      const data = await response.json();
      setApplications(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load applications');
      console.error('Error fetching applications:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (applicationId: number) => {
    try {
      const response = await fetchWithAuth(`/api/applications/${applicationId}/submit`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error('Failed to submit application');
      }
      
      await fetchApplications();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit application');
    }
  };

  const handleWithdraw = async (applicationId: number) => {
    if (!confirm('Are you sure you want to withdraw this application?')) {
      return;
    }
    
    try {
      // Note: Withdraw endpoint would need to be added to backend
      const response = await fetchWithAuth(`/api/applications/${applicationId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'withdrawn' }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to withdraw application');
      }
      
      await fetchApplications();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to withdraw application');
    }
  };

  const handleCreateDeal = async (applicationId: number) => {
    if (!confirm('Create a deal from this approved application?')) {
      return;
    }
    
    setCreatingDeal(applicationId);
    setError(null);
    
    try {
      const response = await fetchWithAuth(`/api/applications/${applicationId}/create-deal`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to create deal');
      }
      
      const data = await response.json();
      
      // Navigate to the created deal
      if (data.deal?.id) {
        navigate(`/dashboard/deals/${data.deal.id}`);
      } else {
        // Refresh applications list if navigation fails
        await fetchApplications();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create deal');
      setCreatingDeal(null);
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
      case 'withdrawn':
        return 'bg-gray-500 text-white';
      default:
        return 'bg-slate-500 text-white';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="h-4 w-4" />;
      case 'rejected':
        return <X className="h-4 w-4" />;
      case 'submitted':
      case 'under_review':
        return <Clock className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const filteredApplications = applications.filter(app => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const title = app.application_data?.title || app.individual_data?.name || app.business_data?.company_name || '';
      return title.toString().toLowerCase().includes(query) || 
             app.id.toString().includes(query);
    }
    return true;
  });

  const sortedApplications = [...filteredApplications].sort((a, b) => {
    if (sortBy === 'date') {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    } else {
      return a.status.localeCompare(b.status);
    }
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-emerald-500/20 border border-emerald-500/30">
              <FileText className="h-6 w-6 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-slate-100">Loan & Credit Applications</h1>
              <p className="text-slate-400 mt-1">Manage loan and credit applications from prospective borrowers</p>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-sm">
            <AlertCircle className="h-4 w-4 text-emerald-400" />
            <span className="text-emerald-300">These are loan/credit applications from borrowers, not platform user signups</span>
          </div>
        </div>
        <Button
          onClick={() => navigate('/apply')}
          className="bg-emerald-600 hover:bg-emerald-500 text-white"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Application
        </Button>
      </div>

      {/* Filters and Search */}
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search applications..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-400" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as ApplicationStatus | 'all')}
                className="px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="all">All Status</option>
                <option value="draft">Draft</option>
                <option value="submitted">Submitted</option>
                <option value="under_review">Under Review</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="withdrawn">Withdrawn</option>
              </select>
            </div>

            {/* Type Filter */}
            <div className="flex items-center gap-2">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value as ApplicationType | 'all')}
                className="px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="all">All Types</option>
                <option value="individual">Individual</option>
                <option value="business">Business</option>
              </select>
            </div>

            {/* Sort */}
            <div className="flex items-center gap-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'date' | 'status')}
                className="px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="date">Sort by Date</option>
                <option value="status">Sort by Status</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 flex items-center gap-2 text-red-400">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {/* Applications List */}
      {loading ? (
        <SkeletonDocumentList count={5} />
      ) : sortedApplications.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-12 w-12 text-slate-500" />}
          title="No applications found"
          description="Get started by creating a new application"
          action={
            <Button
              onClick={() => navigate('/apply')}
              className="bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Application
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {sortedApplications.map((app) => (
            <Card key={app.id} className="bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      {app.application_type === 'individual' ? (
                        <User className="h-5 w-5 text-slate-400" />
                      ) : (
                        <Building2 className="h-5 w-5 text-slate-400" />
                      )}
                      <h3 className="text-lg font-semibold text-slate-100">
                        Application #{app.id}
                      </h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${getStatusColor(app.status)}`}>
                        {getStatusIcon(app.status)}
                        {app.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 text-sm">
                      <div>
                        <span className="text-slate-400">Type:</span>
                        <span className="text-slate-100 ml-2 capitalize">{app.application_type}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Created:</span>
                        <span className="text-slate-100 ml-2">
                          {new Date(app.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      {app.submitted_at && (
                        <div>
                          <span className="text-slate-400">Submitted:</span>
                          <span className="text-slate-100 ml-2">
                            {new Date(app.submitted_at).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>

                    {app.rejection_reason && (
                      <div className="mt-3 p-3 bg-red-500/10 border border-red-500/50 rounded-lg">
                        <p className="text-sm text-red-400">
                          <strong>Rejection Reason:</strong> {app.rejection_reason}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/dashboard/applications/${app.id}`)}
                      className="text-slate-400 hover:text-slate-100"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    
                    {app.status === 'draft' && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/apply/${app.application_type}/${app.id}/edit`)}
                          className="text-slate-400 hover:text-slate-100"
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSubmit(app.id)}
                          className="text-emerald-400 hover:text-emerald-300"
                        >
                          <Send className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                    
                    {app.status === 'approved' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCreateDeal(app.id)}
                        disabled={creatingDeal === app.id}
                        className="text-emerald-400 hover:text-emerald-300"
                        title="Create Deal"
                      >
                        {creatingDeal === app.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <ArrowRightCircle className="h-4 w-4" />
                        )}
                      </Button>
                    )}
                    
                    {(app.status === 'draft' || app.status === 'submitted') && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleWithdraw(app.id)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
