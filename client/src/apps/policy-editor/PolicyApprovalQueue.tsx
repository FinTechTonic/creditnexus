/**
 * Policy Approval Queue - List of policies pending approval.
 * 
 * Features:
 * - List policies pending approval
 * - Filter by category
 * - Quick approve/reject actions
 * - View policy details
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '../../context/AuthContext';
import { usePermissions } from '../../hooks/usePermissions';
import { 
  CheckCircle2, 
  XCircle, 
  Eye, 
  Filter,
  Search,
  Loader2,
  FileText,
  Clock,
  User
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';

// Types
interface Policy {
  id: number;
  name: string;
  category: string;
  description?: string;
  status: string;
  version: number;
  created_by: number;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

interface PolicyApprovalQueueProps {
  onPolicySelect?: (policy: Policy) => void;
  onApprove?: (policyId: number) => void;
  onReject?: (policyId: number) => void;
  className?: string;
}

export function PolicyApprovalQueue({
  onPolicySelect,
  onApprove,
  onReject,
  className = ''
}: PolicyApprovalQueueProps) {
  const { hasPermission } = usePermissions();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  
  // Check permissions
  const canViewPending = hasPermission('POLICY_VIEW_PENDING');
  const canApprove = hasPermission('POLICY_APPROVE');
  const canReject = hasPermission('POLICY_REJECT');
  
  // Load pending approvals
  useEffect(() => {
    if (canViewPending) {
      loadPendingApprovals();
    } else {
      setError('You do not have permission to view pending approvals');
      setLoading(false);
    }
  }, [categoryFilter, canViewPending]);
  
  const loadPendingApprovals = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (categoryFilter !== 'all') {
        params.append('category', categoryFilter);
      }
      
      const response = await fetchWithAuth(`/api/policies/pending-approval?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Failed to load pending approvals');
      }
      
      const data = await response.json();
      setPolicies(data.policies || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pending approvals');
    } finally {
      setLoading(false);
    }
  };
  
  const handlePolicyClick = (policy: Policy) => {
    setSelectedPolicy(policy);
    if (onPolicySelect) {
      onPolicySelect(policy);
    }
  };
  
  const handleApprove = async (policyId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onApprove) {
      onApprove(policyId);
    }
  };
  
  const handleReject = async (policyId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onReject) {
      onReject(policyId);
    }
  };
  
  const filteredPolicies = policies.filter(policy => {
    const matchesSearch = searchTerm === '' || 
      policy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      policy.description?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });
  
  const categories = Array.from(new Set(policies.map(p => p.category)));
  
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <FileText className="h-6 w-6" />
          Policy Approval Queue
        </h2>
        <p className="text-muted-foreground">
          Review and approve policies pending approval
        </p>
      </div>
      
      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search policies..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="w-48">
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="all">All Categories</option>
                {categories.map(cat => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="outline"
              onClick={loadPendingApprovals}
            >
              <Filter className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      )}
      
      {/* Empty State */}
      {!loading && filteredPolicies.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">No Pending Approvals</h3>
            <p className="text-muted-foreground">
              {policies.length === 0 
                ? "There are no policies pending approval."
                : "No policies match your search criteria."}
            </p>
          </CardContent>
        </Card>
      )}
      
      {/* Policy List */}
      {!loading && filteredPolicies.length > 0 && (
        <div className="space-y-2">
          {filteredPolicies.map(policy => (
            <Card
              key={policy.id}
              className={`cursor-pointer hover:bg-muted transition-colors ${
                selectedPolicy?.id === policy.id ? 'ring-2 ring-primary' : ''
              }`}
              onClick={() => handlePolicyClick(policy)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold">{policy.name}</h3>
                      <Badge variant="outline">{policy.category}</Badge>
                      <Badge variant="secondary">v{policy.version}</Badge>
                    </div>
                    {policy.description && (
                      <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                        {policy.description}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(policy.created_at).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <User className="h-3 w-3" />
                        Created by User {policy.created_by}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {canApprove && (
                      <Button
                        size="sm"
                        variant="default"
                        onClick={(e) => handleApprove(policy.id, e)}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircle2 className="h-4 w-4 mr-1" />
                        Approve
                      </Button>
                    )}
                    {canReject && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={(e) => handleReject(policy.id, e)}
                      >
                        <XCircle className="h-4 w-4 mr-1" />
                        Reject
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePolicyClick(policy);
                      }}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      
      {/* Summary */}
      {!loading && filteredPolicies.length > 0 && (
        <div className="text-sm text-muted-foreground text-center">
          Showing {filteredPolicies.length} of {policies.length} pending approval{policies.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
