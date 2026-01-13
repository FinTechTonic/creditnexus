/**
 * Workflow processing page for handling all workflow types via encrypted links.
 */

import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  FileText, 
  Loader2, 
  Download,
  Clock,
  User,
  Building2
} from 'lucide-react'
import { fetchWithAuth } from '@/context/AuthContext'
import { useFDC3 } from '@/context/FDC3Context'
import type { WorkflowLinkContext } from '@/context/FDC3Context'

interface WorkflowData {
  workflow_id: string
  workflow_type: string
  workflow_metadata: {
    title?: string
    description?: string
    dealId?: number
    documentId?: number
    senderInfo?: {
      user_id?: number
      email?: string
      name?: string
    }
    receiverInfo?: {
      user_id?: number
      email?: string
      name?: string
    }
    expiresAt?: string
    filesIncluded?: number
    required_actions?: string[]
    required_signers?: string[]
    review_type?: string
    flow_type?: string
  }
  deal_id?: number
  deal_data?: any
  cdm_payload?: any
  file_references?: Array<{
    document_id?: number
    filename: string
    category: string
    subdirectory: string
    size: number
    download_url: string
    title: string
  }>
  expires_at?: string
}

export function WorkflowProcessingPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { context, listenForWorkflowLinks } = useFDC3()
  
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<WorkflowData | null>(null)
  const [declineReason, setDeclineReason] = useState('')
  const [showDeclineDialog, setShowDeclineDialog] = useState(false)

  // Get payload from URL or FDC3 context
  const payloadFromUrl = searchParams.get('payload')
  const workflowContext = context?.type === 'fdc3.creditnexus.workflow' ? context as WorkflowLinkContext : null
  const encryptedPayload = payloadFromUrl || workflowContext?.linkPayload

  useEffect(() => {
    if (encryptedPayload) {
      loadWorkflowFromPayload(encryptedPayload)
    } else {
      setError('No workflow payload provided')
      setLoading(false)
    }
  }, [encryptedPayload])

  // Listen for FDC3 workflow links
  useEffect(() => {
    if (!encryptedPayload) {
      listenForWorkflowLinks((workflowCtx) => {
        if (workflowCtx.linkPayload) {
          loadWorkflowFromPayload(workflowCtx.linkPayload)
        }
      })
    }
  }, [encryptedPayload, listenForWorkflowLinks])

  const loadWorkflowFromPayload = async (payload: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetchWithAuth('/api/workflows/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ encrypted_payload: payload }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Invalid or expired workflow link')
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workflow')
    } finally {
      setLoading(false)
    }
  }

  const handleComplete = async () => {
    if (!data) return

    setProcessing(true)
    try {
      const response = await fetchWithAuth(`/api/workflows/${data.workflow_id}/complete`, {
        method: 'POST',
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to complete workflow')
      }

      // Reload workflow data to get updated state
      if (encryptedPayload) {
        await loadWorkflowFromPayload(encryptedPayload)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete workflow')
    } finally {
      setProcessing(false)
    }
  }

  const handleDecline = async () => {
    if (!data || !declineReason.trim()) {
      setError('Please provide a reason for declining')
      return
    }

    setProcessing(true)
    try {
      const response = await fetchWithAuth(`/api/workflows/${data.workflow_id}/state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state: 'declined',
          metadata: {
            reason: declineReason,
            declined_at: new Date().toISOString(),
          },
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to decline workflow')
      }

      // Reload workflow data
      if (encryptedPayload) {
        await loadWorkflowFromPayload(encryptedPayload)
      }
      setShowDeclineDialog(false)
      setDeclineReason('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to decline workflow')
    } finally {
      setProcessing(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            <span className="ml-2 text-slate-400">Loading workflow...</span>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4">
        <Card className="bg-slate-800 border-slate-700 max-w-md w-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-400">
              <XCircle className="h-5 w-5" />
              Workflow Error
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-slate-300">{error}</p>
            <Button onClick={() => navigate('/')} className="w-full">
              Return to Home
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!data) return null

  const isExpired = data.expires_at ? new Date(data.expires_at) < new Date() : false
  const workflowTypeLabel = data.workflow_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())

  return (
    <div className="min-h-screen bg-slate-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="h-6 w-6 text-blue-400" />
                <div>
                  <CardTitle className="text-slate-100">{data.workflow_metadata?.title || workflowTypeLabel}</CardTitle>
                  <CardDescription className="text-slate-400">
                    {data.workflow_metadata?.description || `Process this ${workflowTypeLabel.toLowerCase()} workflow`}
                  </CardDescription>
                </div>
              </div>
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                isExpired 
                  ? 'bg-yellow-900/50 text-yellow-400' 
                  : 'bg-blue-900/50 text-blue-400'
              }`}>
                {workflowTypeLabel}
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Error Message */}
        {error && (
          <Card className="bg-red-900/20 border-red-700">
            <CardContent className="pt-6">
              <p className="text-red-300">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Expiration Notice */}
        {isExpired && (
          <Card className="bg-yellow-900/20 border-yellow-700">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-yellow-400">
                <AlertTriangle className="h-5 w-5" />
                <p>This workflow link has expired</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Workflow Information */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Sender Info */}
          {data.workflow_metadata?.senderInfo && (
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-sm text-slate-300 flex items-center gap-2">
                  <User className="h-4 w-4" />
                  From
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-100 font-medium">
                  {data.workflow_metadata.senderInfo.name || data.workflow_metadata.senderInfo.email || 'Unknown'}
                </p>
                {data.workflow_metadata.senderInfo.email && (
                  <p className="text-sm text-slate-400">{data.workflow_metadata.senderInfo.email}</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Expiration */}
          {data.expires_at && (
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-sm text-slate-300 flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Expires
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-100">
                  {new Date(data.expires_at).toLocaleString()}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Deal Information */}
        {data.deal_id && data.deal_data && (
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100 flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Deal Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div>
                <Label className="text-slate-400 text-sm">Deal ID</Label>
                <p className="text-slate-200 font-mono">{data.deal_id}</p>
              </div>
              {data.deal_data.deal_id && (
                <div>
                  <Label className="text-slate-400 text-sm">External Deal ID</Label>
                  <p className="text-slate-200">{data.deal_data.deal_id}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* File References */}
        {data.file_references && data.file_references.length > 0 && (
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100 flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Referenced Files ({data.file_references.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {data.file_references.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 bg-slate-900 rounded border border-slate-700"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate">
                        {file.title || file.filename}
                      </p>
                      <p className="text-xs text-slate-400">
                        {file.category} • {(file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => window.open(file.download_url, '_blank')}
                      className="ml-2 border-slate-600"
                    >
                      <Download className="h-4 w-4 mr-1" />
                      Download
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* CDM Payload (Collapsible) */}
        {data.cdm_payload && Object.keys(data.cdm_payload).length > 0 && (
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">CDM Payload</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-xs overflow-auto max-h-64 bg-slate-900 p-4 rounded font-mono text-slate-300">
                {JSON.stringify(data.cdm_payload, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Action Buttons */}
        {!isExpired && (
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex gap-4">
                <Button
                  onClick={handleComplete}
                  disabled={processing}
                  className="flex-1 bg-green-600 hover:bg-green-700"
                >
                  {processing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Complete Workflow
                    </>
                  )}
                </Button>
                <Button
                  onClick={() => setShowDeclineDialog(true)}
                  disabled={processing}
                  variant="outline"
                  className="flex-1 border-red-600 text-red-400 hover:bg-red-900/20"
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Decline
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Decline Dialog */}
        {showDeclineDialog && (
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Decline Workflow</CardTitle>
              <CardDescription className="text-slate-400">
                Please provide a reason for declining this workflow
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="decline-reason" className="text-slate-300">
                  Reason
                </Label>
                <Textarea
                  id="decline-reason"
                  value={declineReason}
                  onChange={(e) => setDeclineReason(e.target.value)}
                  placeholder="Enter reason for declining..."
                  rows={4}
                  className="bg-slate-900 border-slate-600 text-slate-200 mt-2"
                />
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={handleDecline}
                  disabled={!declineReason.trim() || processing}
                  className="flex-1 bg-red-600 hover:bg-red-700"
                >
                  {processing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Declining...
                    </>
                  ) : (
                    'Confirm Decline'
                  )}
                </Button>
                <Button
                  onClick={() => {
                    setShowDeclineDialog(false)
                    setDeclineReason('')
                  }}
                  variant="outline"
                  className="border-slate-600"
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
