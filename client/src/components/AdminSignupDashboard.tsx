import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  User, 
  Search, 
  Filter, 
  CheckCircle, 
  XCircle, 
  Clock,
  Eye,
  Loader2,
  AlertCircle,
  FileText,
  Building2,
  Mail,
  Calendar
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { usePermissions } from '@/hooks/usePermissions';

interface SignupUser {
  id: number;
  email: string;
  display_name: string;
  role: string;
  signup_status: 'pending' | 'approved' | 'rejected';
  signup_submitted_at: string | null;
  signup_reviewed_at: string | null;
  signup_reviewed_by: number | null;
  signup_rejection_reason: string | null;
  profile_data: Record<string, any> | null;
  created_at: string;
}

interface SignupListResponse {
  status: string;
  data: SignupUser[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export function AdminSignupDashboard() {
  const { hasPermission } = usePermissions();
  const [signups, setSignups] = useState<SignupUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<'pending' | 'approved' | 'rejected' | 'all'>('pending');
  const [filterRole, setFilterRole] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedSignup, setSelectedSignup] = useState<SignupUser | null>(null);
  const [isApproving, setIsApproving] = useState<number | null>(null);
  const [isRejecting, setIsRejecting] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);

  useEffect(() => {
    fetchSignups();
  }, [filterStatus, filterRole, page]);

  const fetchSignups = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (filterStatus !== 'all') {
        params.append('status', filterStatus);
      }
      if (filterRole !== 'all') {
        params.append('role', filterRole);
      }
      params.append('page', page.toString());
      params.append('limit', '20');
      
      const response = await fetchWithAuth(`/api/admin/signups?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch signups');
      }
      
      const data: SignupListResponse = await response.json();
      setSignups(data.data);
      setTotalPages(data.pagination.pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load signups');
      console.error('Error fetching signups:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (userId: number) => {
    try {
      setIsApproving(userId);
      const response = await fetchWithAuth(`/api/admin/signups/${userId}/approve`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to approve signup');
      }
      
      // Refresh list
      await fetchSignups();
      if (selectedSignup?.id === userId) {
        setSelectedSignup(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve signup');
    } finally {
      setIsApproving(null);
    }
  };

  const handleReject = async (userId: number) => {
    if (!rejectReason.trim() || rejectReason.trim().length < 10) {
      setError('Rejection reason must be at least 10 characters');
      return;
    }
    
    try {
      setIsRejecting(userId);
      const response = await fetchWithAuth(`/api/admin/signups/${userId}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reason: rejectReason }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to reject signup');
      }
      
      // Refresh list
      await fetchSignups();
      setShowRejectModal(false);
      setRejectReason('');
      if (selectedSignup?.id === userId) {
        setSelectedSignup(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject signup');
    } finally {
      setIsRejecting(null);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="h-4 w-4 text-emerald-400" />;
      case 'rejected':
        return <XCircle className="h-4 w-4 text-red-400" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-400" />;
      default:
        return <Clock className="h-4 w-4 text-slate-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'text-emerald-400 bg-emerald-500/20 border-emerald-500/30';
      case 'rejected':
        return 'text-red-400 bg-red-500/20 border-red-500/30';
      case 'pending':
        return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30';
      default:
        return 'text-slate-400 bg-slate-500/20 border-slate-500/30';
    }
  };

  const filteredSignups = signups.filter(signup => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        signup.email.toLowerCase().includes(query) ||
        signup.display_name.toLowerCase().includes(query) ||
        signup.role.toLowerCase().includes(query)
      );
    }
    return true;
  });

  if (!hasPermission('USER_APPROVE') && !hasPermission('USER_REJECT')) {
    return (
      <div className="p-8 text-center">
        <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
        <p className="text-slate-400">You don't have permission to view this page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-blue-500/20 border border-blue-500/30">
              <User className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-slate-100">Platform User Signups</h1>
              <p className="text-slate-400 mt-1">Review and approve account signups for platform users (bankers, lawyers, accountants, etc.)</p>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm">
            <AlertCircle className="h-4 w-4 text-blue-400" />
            <span className="text-blue-300">These are platform account signups, not loan applications</span>
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search by email, name, or role..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <select
                value={filterStatus}
                onChange={(e) => {
                  setFilterStatus(e.target.value as any);
                  setPage(1);
                }}
                className="px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
              <select
                value={filterRole}
                onChange={(e) => {
                  setFilterRole(e.target.value);
                  setPage(1);
                }}
                className="px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="all">All Roles</option>
                <option value="applicant">Applicant</option>
                <option value="banker">Banker</option>
                <option value="law_officer">Law Officer</option>
                <option value="accountant">Accountant</option>
                <option value="analyst">Analyst</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-900/30 border border-red-700 rounded-lg flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Signups List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
        </div>
      ) : filteredSignups.length === 0 ? (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-12 text-center">
            <User className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">No signups found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredSignups.map((signup) => (
            <Card key={signup.id} className="bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className={`p-2 rounded-lg ${getStatusColor(signup.signup_status)}`}>
                        {getStatusIcon(signup.signup_status)}
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-slate-100">{signup.display_name}</h3>
                        <p className="text-sm text-slate-400 flex items-center gap-2">
                          <Mail className="h-3 w-3" />
                          {signup.email}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 mt-3 text-sm text-slate-400">
                      <span className="flex items-center gap-1">
                        <User className="h-4 w-4" />
                        {signup.role.replace('_', ' ')}
                      </span>
                      {signup.signup_submitted_at && (
                        <span className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          {new Date(signup.signup_submitted_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    {signup.profile_data && Object.keys(signup.profile_data).length > 0 && (
                      <div className="mt-3 p-3 bg-slate-900 rounded-lg">
                        <p className="text-xs text-slate-500 mb-1">Profile Data:</p>
                        <div className="text-sm text-slate-300">
                          {signup.profile_data.company && (
                            <span className="flex items-center gap-1 mb-1">
                              <Building2 className="h-3 w-3" />
                              {signup.profile_data.company}
                            </span>
                          )}
                          {signup.profile_data.job_title && (
                            <span className="flex items-center gap-1">
                              <FileText className="h-3 w-3" />
                              {signup.profile_data.job_title}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedSignup(signup)}
                      className="border-slate-600 text-slate-300 hover:bg-slate-700"
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      View
                    </Button>
                    {signup.signup_status === 'pending' && (
                      <>
                        {hasPermission('USER_APPROVE') && (
                          <Button
                            size="sm"
                            onClick={() => handleApprove(signup.id)}
                            disabled={isApproving === signup.id}
                            className="bg-emerald-600 hover:bg-emerald-500"
                          >
                            {isApproving === signup.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <>
                                <CheckCircle className="h-4 w-4 mr-2" />
                                Approve
                              </>
                            )}
                          </Button>
                        )}
                        {hasPermission('USER_REJECT') && (
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => {
                              setSelectedSignup(signup);
                              setShowRejectModal(true);
                            }}
                            disabled={isRejecting === signup.id}
                          >
                            <XCircle className="h-4 w-4 mr-2" />
                            Reject
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="border-slate-600 text-slate-300"
          >
            Previous
          </Button>
          <span className="text-slate-400">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="border-slate-600 text-slate-300"
          >
            Next
          </Button>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && selectedSignup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <Card className="w-full max-w-md bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Reject Signup</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-slate-300">
                Rejecting signup for <strong>{selectedSignup.display_name}</strong> ({selectedSignup.email})
              </p>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Rejection Reason (minimum 10 characters) *
                </label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  rows={4}
                  placeholder="Please provide a reason for rejection..."
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowRejectModal(false);
                    setRejectReason('');
                  }}
                  className="border-slate-600 text-slate-300"
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => handleReject(selectedSignup.id)}
                  disabled={!rejectReason.trim() || rejectReason.trim().length < 10 || isRejecting === selectedSignup.id}
                >
                  {isRejecting === selectedSignup.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    'Reject'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
