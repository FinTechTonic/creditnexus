import { useState, useEffect, useCallback } from 'react';
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
  Eye,
  Building2,
  Calendar,
  DollarSign,
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw
} from 'lucide-react';
import { useAuth, fetchWithAuth } from '@/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { SkeletonDocumentList, EmptyState } from '@/components/ui/skeleton';

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

type DealStatus = 'draft' | 'submitted' | 'under_review' | 'approved' | 'rejected' | 'active' | 'closed' | 'restructuring' | 'withdrawn';

export function DealDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<DealStatus | 'all'>('all');
  const [filterType, setFilterType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const fetchDeals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (filterStatus !== 'all') {
        params.append('status', filterStatus);
      }
      if (filterType !== 'all') {
        params.append('deal_type', filterType);
      }
      if (searchQuery.trim()) {
        params.append('search', searchQuery.trim());
      }
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());
      
      const url = `/api/deals?${params.toString()}`;
      const response = await fetchWithAuth(url);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to fetch deals');
      }
      
      const data = await response.json();
      setDeals(data.deals || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load deals');
      console.error('Error fetching deals:', err);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterType, searchQuery, offset]);

  useEffect(() => {
    fetchDeals();
  }, [fetchDeals]);

  // Track state changes for debugging
  useEffect(() => {
  }, [loading, deals, error, filterStatus, filterType, searchQuery]);

  const handleSearch = useCallback(() => {
    setOffset(0);
    fetchDeals();
  }, [fetchDeals]);

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Deals</h1>
          <p className="text-slate-400 mt-1">Manage your loan and credit deals</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchDeals}
            className="text-slate-400 hover:text-slate-100"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
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
                  placeholder="Search deals by ID or applicant..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-400" />
              <select
                value={filterStatus}
                onChange={(e) => {
                  setFilterStatus(e.target.value as DealStatus | 'all');
                  setOffset(0);
                }}
                className="px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="all">All Status</option>
                <option value="draft">Draft</option>
                <option value="submitted">Submitted</option>
                <option value="under_review">Under Review</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="active">Active</option>
                <option value="closed">Closed</option>
                <option value="restructuring">Restructuring</option>
                <option value="withdrawn">Withdrawn</option>
              </select>
            </div>

            {/* Type Filter */}
            <div className="flex items-center gap-2">
              <select
                value={filterType}
                onChange={(e) => {
                  setFilterType(e.target.value);
                  setOffset(0);
                }}
                className="px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="all">All Types</option>
                <option value="loan_application">Loan Application</option>
                <option value="debt_sale">Debt Sale</option>
                <option value="loan_purchase">Loan Purchase</option>
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

      {/* Deals List */}
      {(() => {
        if (loading) {
          return <SkeletonDocumentList count={5} />;
        }
        if (deals.length === 0) {
          return (
            <EmptyState
              icon={<FileText className="h-12 w-12 text-slate-500" />}
              title="No deals found"
              description={searchQuery || filterStatus !== 'all' || filterType !== 'all' 
                ? "Try adjusting your filters or search query"
                : "Deals will appear here once created"}
            />
          );
        }
        return (
        <>
          <div className="space-y-4">
            {deals.map((deal) => (
              <Card key={deal.id} className="bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors cursor-pointer" onClick={() => navigate(`/dashboard/deals/${deal.id}`)}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <Building2 className="h-5 w-5 text-slate-400" />
                        <h3 className="text-lg font-semibold text-slate-100">
                          {deal.deal_id}
                        </h3>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${getStatusColor(deal.status)}`}>
                          {getStatusIcon(deal.status)}
                          {deal.status.replace(/_/g, ' ').toUpperCase()}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 text-sm">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-slate-400" />
                          <span className="text-slate-400">Type:</span>
                          <span className="text-slate-100">{formatDealType(deal.deal_type)}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-slate-400" />
                          <span className="text-slate-400">Created:</span>
                          <span className="text-slate-100">
                            {new Date(deal.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        {deal.updated_at && deal.updated_at !== deal.created_at && (
                          <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-slate-400" />
                            <span className="text-slate-400">Updated:</span>
                            <span className="text-slate-100">
                              {new Date(deal.updated_at).toLocaleDateString()}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 ml-4">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/dashboard/deals/${deal.id}`);
                        }}
                        className="text-slate-400 hover:text-slate-100"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {total > limit && (
            <div className="flex items-center justify-between pt-4">
              <div className="text-sm text-slate-400">
                Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} deals
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0 || loading}
                  className="text-slate-400 hover:text-slate-100"
                >
                  Previous
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= total || loading}
                  className="text-slate-400 hover:text-slate-100"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
        );
      })()}
    </div>
  );
}
