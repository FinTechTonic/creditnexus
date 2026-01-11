/**
 * Approval History - Component for displaying policy approval history.
 * 
 * Features:
 * - Display approval history for a policy
 * - Filter by status
 * - Show approval comments
 * - Timeline view
 */

import { useState, useEffect } from 'react';
import { fetchWithAuth } from '../../context/AuthContext';
import { 
  CheckCircle2, 
  XCircle, 
  Clock,
  User,
  FileText,
  Loader2,
  Filter
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';

// Types
interface ApprovalRecord {
  id: number;
  policy_id: number;
  policy_version: number;
  approver_id: number;
  approval_status: string;
  approval_comment?: string;
  approved_at: string;
}

interface ApprovalHistoryProps {
  policyId: number;
  className?: string;
}

export function ApprovalHistory({ policyId, className = '' }: ApprovalHistoryProps) {
  const [history, setHistory] = useState<ApprovalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  
  useEffect(() => {
    if (policyId) {
      loadApprovalHistory();
    }
  }, [policyId, statusFilter]);
  
  const loadApprovalHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetchWithAuth(`/api/policies/${policyId}/approval-history`);
      if (!response.ok) {
        throw new Error('Failed to load approval history');
      }
      
      const data = await response.json();
      let records = data.approval_history || [];
      
      // Apply status filter
      if (statusFilter !== 'all') {
        records = records.filter((r: ApprovalRecord) => r.approval_status === statusFilter);
      }
      
      setHistory(records);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load approval history');
    } finally {
      setLoading(false);
    }
  };
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'rejected':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-600" />;
    }
  };
  
  const getStatusBadgeVariant = (status: string): "default" | "destructive" | "secondary" => {
    switch (status) {
      case 'approved':
        return 'default';
      case 'rejected':
        return 'destructive';
      default:
        return 'secondary';
    }
  };
  
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Approval History
            </CardTitle>
            <CardDescription>
              Review all approval decisions for this policy
            </CardDescription>
          </div>
          <div className="w-40">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="all">All Status</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="pending">Pending</option>
            </select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        )}
        
        {!loading && history.length === 0 && (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">No approval history found</p>
          </div>
        )}
        
        {!loading && history.length > 0 && (
          <div className="space-y-4">
            {history.map((record, index) => (
              <div
                key={record.id}
                className="relative pl-8 pb-4 border-l-2 border-muted last:border-l-0 last:pb-0"
              >
                {/* Timeline dot */}
                <div className="absolute left-0 top-0 transform -translate-x-1/2">
                  {getStatusIcon(record.approval_status)}
                </div>
                
                {/* Content */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={getStatusBadgeVariant(record.approval_status)}>
                      {record.approval_status}
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      Version {record.policy_version}
                    </span>
                  </div>
                  
                  {record.approval_comment && (
                    <p className="text-sm">{record.approval_comment}</p>
                  )}
                  
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(record.approved_at).toLocaleString()}
                    </span>
                    <span className="flex items-center gap-1">
                      <User className="h-3 w-3" />
                      User {record.approver_id}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
