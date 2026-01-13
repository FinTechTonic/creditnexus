/**
 * Workflow Delegation Dashboard for managing and viewing all workflow delegations with analytics.
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectItem } from '@/components/ui/select'
import { 
  BarChart3, 
  TrendingUp, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  FileText,
  Share2,
  Eye,
  RefreshCw,
  Loader2,
  Search,
  Filter,
  Download,
  Send
} from 'lucide-react'
import { fetchWithAuth } from '@/context/AuthContext'
import { WorkflowLinkSharer } from './WorkflowLinkSharer'
import { VerificationLinkCreator } from './VerificationLinkCreator'

interface WorkflowDelegation {
  id: number
  workflow_id: string
  workflow_type: string
  deal_id?: number
  document_id?: number
  sender_user_id: number
  receiver_user_id?: number
  receiver_email?: string
  status: string
  expires_at: string
  completed_at?: string
  created_at: string
  updated_at: string
  workflow_metadata?: any
}

interface WorkflowAnalytics {
  total: number
  pending: number
  processing: number
  completed: number
  declined: number
  expired: number
  by_type: Record<string, number>
  by_status: Record<string, number>
  completion_rate: number
  average_completion_time_hours?: number
}

export function WorkflowDelegationDashboard() {
  const navigate = useNavigate()
  
  const [delegations, setDelegations] = useState<WorkflowDelegation[]>([])
  const [analytics, setAnalytics] = useState<WorkflowAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterDealId, setFilterDealId] = useState<string>('')
  
  // UI State
  const [selectedDelegation, setSelectedDelegation] = useState<WorkflowDelegation | null>(null)
  const [showCreator, setShowCreator] = useState(false)
  const [showSharer, setShowSharer] = useState(false)
  const [sharerData, setSharerData] = useState<any>(null)

  const loadDelegations = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      const params = new URLSearchParams()
      if (filterType !== 'all') params.append('workflow_type', filterType)
      if (filterStatus !== 'all') params.append('status', filterStatus)
      if (filterDealId) params.append('deal_id', filterDealId)
      
      const response = await fetchWithAuth(`/api/workflows?${params.toString()}`)
      
      if (!response.ok) {
        throw new Error('Failed to load workflow delegations')
      }
      
      const data = await response.json()
      setDelegations(data.delegations || [])
      
      // Calculate analytics
      const analyticsData: WorkflowAnalytics = {
        total: data.delegations?.length || 0,
        pending: data.delegations?.filter((d: WorkflowDelegation) => d.status === 'pending').length || 0,
        processing: data.delegations?.filter((d: WorkflowDelegation) => d.status === 'processing').length || 0,
        completed: data.delegations?.filter((d: WorkflowDelegation) => d.status === 'completed').length || 0,
        declined: data.delegations?.filter((d: WorkflowDelegation) => d.status === 'declined').length || 0,
        expired: data.delegations?.filter((d: WorkflowDelegation) => d.status === 'expired').length || 0,
        by_type: {},
        by_status: {},
        completion_rate: 0,
      }
      
      // Count by type
      data.delegations?.forEach((d: WorkflowDelegation) => {
        analyticsData.by_type[d.workflow_type] = (analyticsData.by_type[d.workflow_type] || 0) + 1
        analyticsData.by_status[d.status] = (analyticsData.by_status[d.status] || 0) + 1
      })
      
      // Calculate completion rate
      if (analyticsData.total > 0) {
        analyticsData.completion_rate = (analyticsData.completed / analyticsData.total) * 100
      }
      
      setAnalytics(analyticsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load delegations')
    } finally {
      setLoading(false)
    }
  }, [filterType, filterStatus, filterDealId])

  useEffect(() => {
    loadDelegations()
  }, [loadDelegations])

  const handleViewDelegation = (delegation: WorkflowDelegation) => {
    setSelectedDelegation(delegation)
  }

  const handleProcessLink = (delegation: WorkflowDelegation) => {
    // Navigate to processing page with the workflow link
    navigate(`/app/workflow/process?payload=${encodeURIComponent(delegation.workflow_id)}`)
  }

  const handleShareLink = async (delegation: WorkflowDelegation) => {
    // Get the full link from the delegation
    // For now, construct it from workflow_id
    const link = `${window.location.origin}/app/workflow/process?payload=${delegation.workflow_id}`
    
    setSharerData({
      workflowId: delegation.workflow_id,
      workflowType: delegation.workflow_type,
      link: link,
      encryptedPayload: delegation.workflow_id, // This would be the actual encrypted payload
      metadata: delegation.workflow_metadata || {},
    })
    setShowSharer(true)
  }

  const filteredDelegations = delegations.filter(d => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        d.workflow_id.toLowerCase().includes(query) ||
        d.workflow_type.toLowerCase().includes(query) ||
        d.receiver_email?.toLowerCase().includes(query) ||
        d.workflow_metadata?.title?.toLowerCase().includes(query)
      )
    }
    return true
  })

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-400" />
      case 'declined':
        return <XCircle className="h-4 w-4 text-red-400" />
      case 'expired':
        return <AlertTriangle className="h-4 w-4 text-yellow-400" />
      case 'processing':
        return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />
      default:
        return <Clock className="h-4 w-4 text-slate-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-900/50 text-green-400 border-green-700'
      case 'declined':
        return 'bg-red-900/50 text-red-400 border-red-700'
      case 'expired':
        return 'bg-yellow-900/50 text-yellow-400 border-yellow-700'
      case 'processing':
        return 'bg-blue-900/50 text-blue-400 border-blue-700'
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700'
    }
  }

  if (loading && !analytics) {
    return (
      <div className="space-y-6">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            <span className="ml-2 text-slate-400">Loading workflow delegations...</span>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Workflow Delegations</h1>
          <p className="text-slate-400 mt-1">Manage and track workflow delegations</p>
        </div>
        <Button onClick={() => setShowCreator(true)} className="bg-blue-600 hover:bg-blue-700">
          <Send className="h-4 w-4 mr-2" />
          Create Workflow Link
        </Button>
      </div>

      {/* Analytics Cards */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Total Workflows</p>
                  <p className="text-2xl font-bold text-slate-100">{analytics.total}</p>
                </div>
                <BarChart3 className="h-8 w-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Pending</p>
                  <p className="text-2xl font-bold text-yellow-400">{analytics.pending}</p>
                </div>
                <Clock className="h-8 w-8 text-yellow-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Completed</p>
                  <p className="text-2xl font-bold text-green-400">{analytics.completed}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Completion Rate</p>
                  <p className="text-2xl font-bold text-blue-400">{analytics.completion_rate.toFixed(1)}%</p>
                </div>
                <TrendingUp className="h-8 w-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search workflows..."
                  className="pl-8 bg-slate-900 border-slate-600 text-slate-200"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Workflow Type</Label>
              <Select 
                value={filterType} 
                onValueChange={setFilterType}
                className="bg-slate-900 border-slate-600 text-slate-200"
              >
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="verification">Verification</SelectItem>
                <SelectItem value="notarization">Notarization</SelectItem>
                <SelectItem value="document_review">Document Review</SelectItem>
                <SelectItem value="deal_approval">Deal Approval</SelectItem>
                <SelectItem value="deal_review">Deal Review</SelectItem>
                <SelectItem value="custom">Custom</SelectItem>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Status</Label>
              <Select 
                value={filterStatus} 
                onValueChange={setFilterStatus}
                className="bg-slate-900 border-slate-600 text-slate-200"
              >
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="declined">Declined</SelectItem>
                <SelectItem value="expired">Expired</SelectItem>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Deal ID</Label>
              <Input
                value={filterDealId}
                onChange={(e) => setFilterDealId(e.target.value)}
                placeholder="Filter by deal ID..."
                className="bg-slate-900 border-slate-600 text-slate-200"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delegations Table */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-slate-100">Workflow Delegations</CardTitle>
              <CardDescription className="text-slate-400">
                {filteredDelegations.length} workflow{filteredDelegations.length !== 1 ? 's' : ''} found
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadDelegations}
              className="border-slate-600"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="p-4 bg-red-900/20 border border-red-700 rounded-lg mb-4">
              <p className="text-red-300">{error}</p>
            </div>
          )}

          {filteredDelegations.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400">No workflow delegations found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left p-3 text-sm font-semibold text-slate-300">Workflow ID</th>
                    <th className="text-left p-3 text-sm font-semibold text-slate-300">Type</th>
                    <th className="text-left p-3 text-sm font-semibold text-slate-300">Status</th>
                    <th className="text-left p-3 text-sm font-semibold text-slate-300">Receiver</th>
                    <th className="text-left p-3 text-sm font-semibold text-slate-300">Expires</th>
                    <th className="text-left p-3 text-sm font-semibold text-slate-300">Created</th>
                    <th className="text-right p-3 text-sm font-semibold text-slate-300">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDelegations.map((delegation) => (
                    <tr
                      key={delegation.id}
                      className="border-b border-slate-700 hover:bg-slate-900/50"
                    >
                      <td className="p-3">
                        <code className="text-xs text-slate-300">{delegation.workflow_id.slice(0, 16)}...</code>
                      </td>
                      <td className="p-3">
                        <span className="text-sm text-slate-300 capitalize">
                          {delegation.workflow_type.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="p-3">
                        <div className={`inline-flex items-center gap-2 px-2 py-1 rounded border ${getStatusColor(delegation.status)}`}>
                          {getStatusIcon(delegation.status)}
                          <span className="text-xs font-medium capitalize">{delegation.status}</span>
                        </div>
                      </td>
                      <td className="p-3">
                        <p className="text-sm text-slate-300">
                          {delegation.receiver_email || 'Not specified'}
                        </p>
                      </td>
                      <td className="p-3">
                        <p className="text-sm text-slate-400">
                          {new Date(delegation.expires_at).toLocaleDateString()}
                        </p>
                      </td>
                      <td className="p-3">
                        <p className="text-sm text-slate-400">
                          {new Date(delegation.created_at).toLocaleDateString()}
                        </p>
                      </td>
                      <td className="p-3">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleViewDelegation(delegation)}
                            className="border-slate-600"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleShareLink(delegation)}
                            className="border-slate-600"
                          >
                            <Share2 className="h-4 w-4" />
                          </Button>
                          {delegation.status === 'pending' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleProcessLink(delegation)}
                              className="border-blue-600 text-blue-400"
                            >
                              Process
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Creator Modal */}
      {showCreator && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="bg-slate-800 border-slate-700 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-slate-100">Create Workflow Link</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCreator(false)}
                  className="text-slate-400"
                >
                  ×
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <VerificationLinkCreator
                onLinkGenerated={(link, workflowId) => {
                  setShowCreator(false)
                  loadDelegations()
                }}
              />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Sharer Modal */}
      {showSharer && sharerData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="bg-slate-800 border-slate-700 max-w-2xl w-full">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-slate-100">Share Workflow Link</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowSharer(false)
                    setSharerData(null)
                  }}
                  className="text-slate-400"
                >
                  ×
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <WorkflowLinkSharer {...sharerData} />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
