/**
 * Loan Recovery Sidebar Component
 * 
 * Displays loan defaults, recovery actions, and provides interface for managing recovery workflows.
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useToast } from '@/components/ui/toast';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
// Input removed - unused
import {
  AlertCircle,
  Phone,
  MessageSquare,
  Mail,
  Clock,
  // CheckCircle removed - unused
  XCircle,
  Loader2,
  RefreshCw,
  Filter,
  ChevronRight,
  // Calendar removed - unused
  DollarSign
} from 'lucide-react';
import type {
  LoanDefault,
  RecoveryAction,
  DefaultSeverity,
  DefaultStatus,
  ActionStatus
} from '@/types/recovery';

interface LoanRecoverySidebarProps {
  dealId?: number;
  onDefaultSelect?: (defaultId: number) => void;
}

export function LoanRecoverySidebar({ dealId, onDefaultSelect }: LoanRecoverySidebarProps) {
  const { addToast } = useToast();
  const [defaults, setDefaults] = useState<LoanDefault[]>([]);
  const [selectedDefault, setSelectedDefault] = useState<LoanDefault | null>(null);
  const [recoveryActions, setRecoveryActions] = useState<RecoveryAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<{
    status?: DefaultStatus;
    severity?: DefaultSeverity;
  }>({});

  // Fetch defaults
  const fetchDefaults = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (dealId) params.append('deal_id', dealId.toString());
      if (filters.status) params.append('status', filters.status);
      if (filters.severity) params.append('severity', filters.severity);
      params.append('page', '1');
      params.append('limit', '50');

      const response = await fetchWithAuth(`/api/recovery/defaults?${params.toString()}`);
      if (!response.ok) throw new Error('Failed to fetch defaults');
      
      const data = await response.json();
      setDefaults(data.defaults || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load defaults');
      console.error('Error fetching defaults:', err);
    } finally {
      setLoading(false);
    }
  }, [dealId, filters.status, filters.severity]);

  // Fetch recovery actions for selected default
  const fetchRecoveryActions = useCallback(async (defaultId: number) => {
    try {
      const response = await fetchWithAuth(`/api/recovery/actions?default_id=${defaultId}`);
      if (!response.ok) throw new Error('Failed to fetch actions');
      
      const data = await response.json();
      setRecoveryActions(data.actions || []);
    } catch (err) {
      console.error('Error fetching recovery actions:', err);
    }
  }, []);

  // Trigger recovery actions
  const handleTriggerActions = useCallback(async (defaultId: number, actionTypes?: string[]) => {
    try {
      const response = await fetchWithAuth(`/api/recovery/defaults/${defaultId}/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_types: actionTypes || null })
      });
      if (!response.ok) throw new Error('Failed to trigger actions');
      const actions = await response.json();
      // Handle both array and object responses
      const actionsArray = Array.isArray(actions) ? actions : (actions.actions || []);
      setRecoveryActions(prev => [...prev, ...actionsArray]);
      await fetchDefaults(); // Refresh defaults
      
      // Show success message
      if (actionsArray.length > 0) {
        addToast(`Successfully triggered ${actionsArray.length} recovery action(s)`, 'success');
      } else {
        addToast('No recovery actions were created. Check borrower contact information.', 'warning');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to trigger actions';
      setError(errorMessage);
      addToast(errorMessage, 'error');
      console.error('Error triggering actions:', err);
    }
  }, [fetchDefaults]);

  // Execute recovery action
  const handleExecuteAction = useCallback(async (actionId: number) => {
    try {
      const response = await fetchWithAuth(`/api/recovery/actions/${actionId}/execute`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Failed to execute action');
      
      const updatedAction = await response.json();
      setRecoveryActions(prev =>
        prev.map(action => action.id === actionId ? updatedAction : action)
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute action');
      console.error('Error executing action:', err);
    }
  }, []);

  // Handle default selection
  const handleSelectDefault = useCallback((defaultItem: LoanDefault) => {
    setSelectedDefault(defaultItem);
    if (defaultItem.id) {
      fetchRecoveryActions(defaultItem.id);
      onDefaultSelect?.(defaultItem.id);
    }
  }, [fetchRecoveryActions, onDefaultSelect]);

  // Detect defaults
  const handleDetectDefaults = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth('/api/recovery/defaults/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deal_id: dealId || null })
      });
      
      if (!response.ok) {
        // Try to get error details from response
        let errorMessage = 'Failed to detect defaults';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          // If response is not JSON, use status text
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }
      
      const data = await response.json();
      console.log('Detected defaults:', data);
      
      await fetchDefaults(); // Refresh list
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to detect defaults';
      setError(errorMessage);
      console.error('Error detecting defaults:', err);
    } finally {
      setLoading(false);
    }
  }, [dealId, fetchDefaults]);

  useEffect(() => {
    fetchDefaults();
  }, [fetchDefaults]);

  // Get severity badge color
  const getSeverityColor = (severity: DefaultSeverity): string => {
    switch (severity) {
      case 'low': return 'bg-yellow-500/20 text-yellow-600 border-yellow-500/50';
      case 'medium': return 'bg-orange-500/20 text-orange-600 border-orange-500/50';
      case 'high': return 'bg-red-500/20 text-red-600 border-red-500/50';
      case 'critical': return 'bg-red-800/20 text-red-800 border-red-800/50';
      default: return 'bg-gray-500/20 text-gray-600 border-gray-500/50';
    }
  };

  // Get status badge color
  const getStatusColor = (status: DefaultStatus | ActionStatus): string => {
    switch (status) {
      case 'open':
      case 'pending': return 'bg-yellow-500/20 text-yellow-600 border-yellow-500/50';
      case 'in_recovery':
      case 'sent': return 'bg-blue-500/20 text-blue-600 border-blue-500/50';
      case 'resolved':
      case 'delivered': return 'bg-green-500/20 text-green-600 border-green-500/50';
      case 'failed': return 'bg-red-500/20 text-red-600 border-red-500/50';
      case 'written_off': return 'bg-gray-500/20 text-gray-600 border-gray-500/50';
      default: return 'bg-gray-500/20 text-gray-600 border-gray-500/50';
    }
  };

  // Get action icon
  const getActionIcon = (method: string) => {
    switch (method) {
      case 'sms': return <MessageSquare className="w-4 h-4" />;
      case 'voice': return <Phone className="w-4 h-4" />;
      case 'email': return <Mail className="w-4 h-4" />;
      default: return <AlertCircle className="w-4 h-4" />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            Loan Recovery
          </h2>
          <Badge variant="outline" className="bg-red-500/20 text-red-400 border-red-500/50">
            {defaults.length} Active
          </Badge>
        </div>
        <div className="flex gap-2 mt-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleDetectDefaults}
            disabled={loading}
            className="flex-1"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Detect Defaults
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={fetchDefaults}
            disabled={loading}
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="p-4 border-b border-gray-800 space-y-2">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-400">Filters</span>
        </div>
        <div className="flex gap-2">
          <select
            value={filters.status || ''}
            onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as DefaultStatus || undefined }))}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
          >
            <option value="">All Status</option>
            <option value="open">Open</option>
            <option value="in_recovery">In Recovery</option>
            <option value="resolved">Resolved</option>
            <option value="written_off">Written Off</option>
          </select>
          <select
            value={filters.severity || ''}
            onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value as DefaultSeverity || undefined }))}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
          >
            <option value="">All Severity</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-500/20 border-b border-red-500/50">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Defaults List */}
      <div className="flex-1 overflow-y-auto">
        {loading && defaults.length === 0 ? (
          <div className="p-4 text-center text-gray-400">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            <p>Loading defaults...</p>
          </div>
        ) : defaults.length === 0 ? (
          <div className="p-4 text-center text-gray-400">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No active defaults found</p>
          </div>
        ) : (
          <div className="p-2 space-y-2">
            {defaults.map((defaultItem) => (
              <Card
                key={defaultItem.id}
                className={`cursor-pointer transition-colors ${
                  selectedDefault?.id === defaultItem.id
                    ? 'bg-blue-500/20 border-blue-500/50'
                    : 'bg-gray-800 border-gray-700 hover:bg-gray-700'
                }`}
                onClick={() => handleSelectDefault(defaultItem)}
              >
                <CardContent className="p-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium">
                          {defaultItem.loan_id || `Deal #${defaultItem.deal_id}`}
                        </span>
                        <Badge className={`text-xs ${getSeverityColor(defaultItem.severity)}`}>
                          {defaultItem.severity}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-400 capitalize">
                        {defaultItem.default_type.replace('_', ' ')}
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {defaultItem.days_past_due} days
                    </div>
                    {defaultItem.amount_overdue && (
                      <div className="flex items-center gap-1">
                        <DollarSign className="w-3 h-3" />
                        ${parseFloat(defaultItem.amount_overdue).toLocaleString()}
                      </div>
                    )}
                    <Badge className={`text-xs ${getStatusColor(defaultItem.status)}`}>
                      {defaultItem.status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Selected Default Details */}
      {selectedDefault && (
        <div className="border-t border-gray-800 p-4 space-y-4 max-h-96 overflow-y-auto">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Default Details</h3>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setSelectedDefault(null)}
            >
              <XCircle className="w-4 h-4" />
            </Button>
          </div>

          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-3 space-y-2">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-400">Type:</span>
                  <p className="capitalize">{selectedDefault.default_type.replace('_', ' ')}</p>
                </div>
                <div>
                  <span className="text-gray-400">Severity:</span>
                  <Badge className={`text-xs ${getSeverityColor(selectedDefault.severity)}`}>
                    {selectedDefault.severity}
                  </Badge>
                </div>
                <div>
                  <span className="text-gray-400">Days Past Due:</span>
                  <p>{selectedDefault.days_past_due}</p>
                </div>
                {selectedDefault.amount_overdue && (
                  <div>
                    <span className="text-gray-400">Amount Overdue:</span>
                    <p>${parseFloat(selectedDefault.amount_overdue).toLocaleString()}</p>
                  </div>
                )}
              </div>
              {selectedDefault.default_reason && (
                <div>
                  <span className="text-gray-400 text-sm">Reason:</span>
                  <p className="text-sm">{selectedDefault.default_reason}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recovery Actions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold">Recovery Actions</h4>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  if (selectedDefault) handleTriggerActions(selectedDefault.id);
                }}
                disabled={!selectedDefault}
              >
                Trigger Actions
              </Button>
            </div>
            <div className="space-y-2">
              {recoveryActions.length === 0 ? (
                <p className="text-sm text-gray-400">No recovery actions yet</p>
              ) : (
                recoveryActions.map((action) => (
                  <Card key={action.id} className="bg-gray-800 border-gray-700">
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {getActionIcon(action.communication_method)}
                          <span className="text-sm font-medium capitalize">
                            {action.action_type.replace('_', ' ')}
                          </span>
                        </div>
                        <Badge className={`text-xs ${getStatusColor(action.status)}`}>
                          {action.status}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-400 mb-2">{action.message_content}</p>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        {action.sent_at && (
                          <span>Sent: {new Date(action.sent_at).toLocaleDateString()}</span>
                        )}
                        {action.delivered_at && (
                          <span>Delivered: {new Date(action.delivered_at).toLocaleDateString()}</span>
                        )}
                      </div>
                      {action.status === 'pending' && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="mt-2 w-full"
                          onClick={() => handleExecuteAction(action.id)}
                        >
                          Execute Now
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
