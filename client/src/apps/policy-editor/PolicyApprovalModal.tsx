/**
 * Policy Approval Modal - Modal for approving or rejecting policies.
 * 
 * Features:
 * - View policy details
 * - Approve with comment
 * - Reject with comment
 * - Show approval history
 */

import { useState, useEffect } from 'react';
import { fetchWithAuth } from '../../context/AuthContext';
import { usePermissions } from '../../hooks/usePermissions';
import { 
  CheckCircle2, 
  XCircle, 
  X,
  Loader2,
  FileText,
  AlertCircle,
  History
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Card, CardContent } from '../../components/ui/card';

// Types
interface Policy {
  id: number;
  name: string;
  category: string;
  description?: string;
  rules_yaml: string;
  status: string;
  version: number;
  created_by: number;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

interface ApprovalRecord {
  id: number;
  policy_id: number;
  policy_version: number;
  approver_id: number;
  approval_status: string;
  approval_comment?: string;
  approved_at: string;
}

interface PolicyApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  policyId: number | null;
  onApproved?: () => void;
  onRejected?: () => void;
}

export function PolicyApprovalModal({
  isOpen,
  onClose,
  policyId,
  onApproved,
  onRejected
}: PolicyApprovalModalProps) {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approvalComment, setApprovalComment] = useState('');
  const [rejectionComment, setRejectionComment] = useState('');
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [approvalHistory, setApprovalHistory] = useState<ApprovalRecord[]>([]);
  const [activeTab, setActiveTab] = useState<'details' | 'history'>('details');
  const { hasPermission } = usePermissions();
  
  // Check permissions
  const canApprove = hasPermission('POLICY_APPROVE');
  const canReject = hasPermission('POLICY_REJECT');
  
  // Load policy and history when modal opens
  useEffect(() => {
    if (isOpen && policyId) {
      loadPolicy();
      loadApprovalHistory();
    } else {
      // Reset state when modal closes
      setPolicy(null);
      setApprovalComment('');
      setRejectionComment('');
      setError(null);
      setActiveTab('details');
    }
  }, [isOpen, policyId]);
  
  const loadPolicy = async () => {
    if (!policyId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetchWithAuth(`/api/policies/${policyId}`);
      if (!response.ok) {
        throw new Error('Failed to load policy');
      }
      
      const data = await response.json();
      setPolicy(data.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load policy');
    } finally {
      setLoading(false);
    }
  };
  
  const loadApprovalHistory = async () => {
    if (!policyId) return;
    
    try {
      const response = await fetchWithAuth(`/api/policies/${policyId}/approval-history`);
      if (response.ok) {
        const data = await response.json();
        setApprovalHistory(data.approval_history || []);
      }
    } catch (err) {
      // Silently fail - approval history is optional
      console.error('Failed to load approval history:', err);
    }
  };
  
  const handleApprove = async () => {
    if (!policyId) return;
    
    try {
      setApproving(true);
      setError(null);
      
      const response = await fetchWithAuth(`/api/policies/${policyId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approval_comment: approvalComment || undefined
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to approve policy');
      }
      
      if (onApproved) {
        onApproved();
      }
      
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve policy');
    } finally {
      setApproving(false);
    }
  };
  
  const handleReject = async () => {
    if (!policyId || !rejectionComment.trim()) {
      setError('Rejection comment is required');
      return;
    }
    
    try {
      setRejecting(true);
      setError(null);
      
      const response = await fetchWithAuth(`/api/policies/${policyId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rejection_comment: rejectionComment
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to reject policy');
      }
      
      if (onRejected) {
        onRejected();
      }
      
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject policy');
    } finally {
      setRejecting(false);
    }
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Policy Approval
          </DialogTitle>
          <DialogDescription>
            Review policy details and approve or reject
          </DialogDescription>
        </DialogHeader>
        
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        )}
        
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        
        {!loading && policy && (
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
            <TabsList>
              <TabsTrigger value="details">Policy Details</TabsTrigger>
              <TabsTrigger value="history">
                Approval History
                {approvalHistory.length > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {approvalHistory.length}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="details" className="space-y-4">
              {/* Policy Info */}
              <Card>
                <CardContent className="p-4 space-y-3">
                  <div>
                    <Label className="text-muted-foreground">Policy Name</Label>
                    <p className="font-semibold">{policy.name}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-muted-foreground">Category</Label>
                      <p>{policy.category}</p>
                    </div>
                    <div>
                      <Label className="text-muted-foreground">Version</Label>
                      <p>v{policy.version}</p>
                    </div>
                  </div>
                  {policy.description && (
                    <div>
                      <Label className="text-muted-foreground">Description</Label>
                      <p>{policy.description}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* YAML Preview */}
              <Card>
                <CardContent className="p-4">
                  <Label className="text-muted-foreground mb-2 block">Rules YAML</Label>
                  <pre className="bg-muted p-4 rounded text-xs overflow-x-auto max-h-64 overflow-y-auto">
                    {policy.rules_yaml}
                  </pre>
                </CardContent>
              </Card>
              
              {/* Approval Actions */}
              <div className="grid grid-cols-2 gap-4">
                {canApprove && (
                  <Card>
                    <CardContent className="p-4 space-y-4">
                      <div>
                        <Label htmlFor="approval-comment">Approval Comment (Optional)</Label>
                        <Textarea
                          id="approval-comment"
                          value={approvalComment}
                          onChange={(e) => setApprovalComment(e.target.value)}
                          placeholder="Add a comment about why you're approving this policy..."
                          rows={4}
                        />
                      </div>
                      <Button
                        onClick={handleApprove}
                        disabled={approving}
                        className="w-full bg-green-600 hover:bg-green-700"
                      >
                        {approving ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Approving...
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="h-4 w-4 mr-2" />
                            Approve Policy
                          </>
                        )}
                      </Button>
                    </CardContent>
                  </Card>
                )}
                
                {canReject && (
                  <Card>
                    <CardContent className="p-4 space-y-4">
                      <div>
                        <Label htmlFor="rejection-comment">Rejection Comment (Required)</Label>
                        <Textarea
                          id="rejection-comment"
                          value={rejectionComment}
                          onChange={(e) => setRejectionComment(e.target.value)}
                          placeholder="Explain why you're rejecting this policy..."
                          rows={4}
                          required
                        />
                      </div>
                      <Button
                        onClick={handleReject}
                        disabled={rejecting || !rejectionComment.trim()}
                        variant="destructive"
                        className="w-full"
                      >
                        {rejecting ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Rejecting...
                          </>
                        ) : (
                          <>
                            <XCircle className="h-4 w-4 mr-2" />
                            Reject Policy
                          </>
                        )}
                      </Button>
                    </CardContent>
                  </Card>
                )}
                
                {!canApprove && !canReject && (
                  <Card>
                    <CardContent className="p-4 text-center">
                      <p className="text-muted-foreground">
                        You do not have permission to approve or reject policies.
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>
            
            <TabsContent value="history" className="space-y-4">
              {approvalHistory.length === 0 ? (
                <Card>
                  <CardContent className="p-12 text-center">
                    <History className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-muted-foreground">No approval history yet</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-2">
                  {approvalHistory.map((record) => (
                    <Card key={record.id}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge
                                variant={
                                  record.approval_status === 'approved' 
                                    ? 'default' 
                                    : record.approval_status === 'rejected'
                                    ? 'destructive'
                                    : 'secondary'
                                }
                              >
                                {record.approval_status}
                              </Badge>
                              <span className="text-sm text-muted-foreground">
                                Version {record.policy_version}
                              </span>
                            </div>
                            {record.approval_comment && (
                              <p className="text-sm mb-2">{record.approval_comment}</p>
                            )}
                            <p className="text-xs text-muted-foreground">
                              {new Date(record.approved_at).toLocaleString()} by User {record.approver_id}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}
