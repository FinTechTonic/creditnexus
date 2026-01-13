/**
 * Enhanced workflow link creator component with workflow type selection and metadata editing.
 */

import { useState, useEffect } from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectItem } from '@/components/ui/select'
import { Copy, Check, Share2, FileText, Loader2, Settings, User, Mail } from 'lucide-react'
import { WorkflowLinkSharer } from './WorkflowLinkSharer'
import { fetchWithAuth } from '@/context/AuthContext'

interface Document {
  id: number
  title: string
  filename: string
  category: string
  subdirectory: string
  size: number
}

type WorkflowType = 
  | 'verification'
  | 'notarization'
  | 'document_review'
  | 'deal_approval'
  | 'deal_review'
  | 'custom'

interface VerificationLinkCreatorProps {
  dealId?: number
  documentId?: number
  verificationId?: string
  onLinkGenerated?: (link: string, workflowId: string) => void
}

interface GeneratedLink {
  workflow_id: string
  workflow_type: string
  link: string
  encrypted_payload: string
  files_included: number
  expires_at?: string
}

interface Deal {
  id: number
  deal_id: string
  status: string
  deal_type: string | null
}

export function VerificationLinkCreator({
  dealId: propDealId,
  documentId: propDocumentId,
  verificationId,
  onLinkGenerated
}: VerificationLinkCreatorProps) {
  // Workflow configuration
  const [workflowType, setWorkflowType] = useState<WorkflowType>('verification')
  const [customWorkflowType, setCustomWorkflowType] = useState('')
  
  // Deal/Document selection (internal state that can override props)
  const [selectedDealId, setSelectedDealId] = useState<number | undefined>(propDealId)
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | undefined>(propDocumentId)
  const [availableDeals, setAvailableDeals] = useState<Deal[]>([])
  const [loadingDeals, setLoadingDeals] = useState(false)
  
  // File selection
  const [includeFiles, setIncludeFiles] = useState(true)
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [selectedDocuments, setSelectedDocuments] = useState<number[]>([])
  const [availableDocuments, setAvailableDocuments] = useState<Document[]>([])
  const [availableCategories, setAvailableCategories] = useState<string[]>([])
  
  // Metadata
  const [workflowTitle, setWorkflowTitle] = useState('')
  const [workflowDescription, setWorkflowDescription] = useState('')
  const [receiverEmail, setReceiverEmail] = useState('')
  const [receiverUserId, setReceiverUserId] = useState<number | null>(null)
  const [expiresInHours, setExpiresInHours] = useState(72)
  const [callbackUrl, setCallbackUrl] = useState('')
  
  // Workflow-specific fields
  const [requiredSigners, setRequiredSigners] = useState<string[]>([''])
  const [reviewType, setReviewType] = useState('general')
  const [flowType, setFlowType] = useState('approval')
  
  // State
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [generatedLink, setGeneratedLink] = useState<GeneratedLink | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Update selected IDs when props change
  useEffect(() => {
    if (propDealId) {
      setSelectedDealId(propDealId)
    }
  }, [propDealId])

  useEffect(() => {
    if (propDocumentId) {
      setSelectedDocumentId(propDocumentId)
    }
  }, [propDocumentId])

  useEffect(() => {
    loadCategories()
    setLoading(false)
  }, [])

  useEffect(() => {
    const currentDealId = selectedDealId || propDealId
    if (currentDealId) {
      loadDocuments(currentDealId)
    }
  }, [selectedDealId, propDealId])

  useEffect(() => {
    // Load deals if needed for dropdown
    const needsDeal = ['verification', 'notarization', 'deal_approval', 'deal_review', 'document_review'].includes(workflowType)
    const currentDealId = selectedDealId || propDealId
    if (needsDeal && !currentDealId && availableDeals.length === 0) {
      loadDeals()
    }
  }, [workflowType, selectedDealId, propDealId])

  useEffect(() => {
    // Set default title and description based on workflow type
    if (!workflowTitle) {
      const defaults: Record<WorkflowType, string> = {
        verification: 'Deal Verification Request',
        notarization: 'Document Notarization Request',
        document_review: 'Document Review Request',
        deal_approval: 'Deal Approval Request',
        deal_review: 'Deal Review Request',
        custom: 'Custom Workflow Request',
      }
      setWorkflowTitle(defaults[workflowType])
    }
    
    if (!workflowDescription) {
      const defaults: Record<WorkflowType, string> = {
        verification: 'Please review and verify this deal and its documents.',
        notarization: 'Please notarize these documents with blockchain signatures.',
        document_review: 'Please review this document and provide feedback.',
        deal_approval: 'Please review and approve this deal proposal.',
        deal_review: 'Please review this deal and provide feedback.',
        custom: 'Please process this custom workflow.',
      }
      setWorkflowDescription(defaults[workflowType])
    }
  }, [workflowType])

  const loadDeals = async () => {
    if (availableDeals.length > 0) return // Already loaded
    setLoadingDeals(true)
    try {
      const response = await fetchWithAuth('/api/deals?limit=100')
      if (response.ok) {
        const data = await response.json()
        setAvailableDeals(data.deals || [])
      }
    } catch (err) {
      console.error('Failed to load deals:', err)
    } finally {
      setLoadingDeals(false)
    }
  }

  const loadDocuments = async (dealIdToLoad: number) => {
    if (!dealIdToLoad) return
    try {
      const response = await fetchWithAuth(`/api/deals/${dealIdToLoad}/documents`)
      if (response.ok) {
        const docs = await response.json()
        setAvailableDocuments(docs.documents || docs || [])
      }
    } catch (err) {
      console.error('Failed to load documents:', err)
    }
  }

  const loadCategories = async () => {
    try {
      const response = await fetchWithAuth('/api/config/verification-file-whitelist')
      if (response.ok) {
        const data = await response.json()
        // Use parsed config if available, otherwise fallback to defaults
        const config = data.config || {}
        const categories = config.enabled_categories || ['legal', 'financial', 'compliance']
        setAvailableCategories(categories)
        setSelectedCategories(categories) // Select all by default
      }
    } catch (err) {
      console.error('Failed to load categories:', err)
      // Use default categories
      setAvailableCategories(['legal', 'financial', 'compliance'])
      setSelectedCategories(['legal', 'financial', 'compliance'])
    }
  }

  const handleGenerateLink = async () => {
    setGenerating(true)
    setError(null)

    try {
      // Use selected IDs (from dropdown or props)
      const currentDealId = selectedDealId || propDealId
      const currentDocumentId = selectedDocumentId || propDocumentId
      
      // Ensure dealId and documentId are numbers if provided
      const dealIdNum = currentDealId ? Number(currentDealId) : undefined
      const documentIdNum = currentDocumentId ? Number(currentDocumentId) : undefined

      // Validate required fields
      if (workflowType === 'verification' && (!dealIdNum || isNaN(dealIdNum))) {
        throw new Error('Deal ID is required for verification workflow. Please select a deal from the dropdown.')
      }
      if (workflowType === 'notarization' && (!dealIdNum || isNaN(dealIdNum))) {
        throw new Error('Deal ID is required for notarization workflow. Please select a deal from the dropdown.')
      }
      if (workflowType === 'notarization' && requiredSigners.filter(s => s.trim()).length === 0) {
        throw new Error('At least one required signer is needed for notarization')
      }
      if (workflowType === 'document_review' && (!documentIdNum || isNaN(documentIdNum))) {
        throw new Error('Document ID is required for document review workflow. Please select a document from the dropdown.')
      }
      if ((workflowType === 'deal_approval' || workflowType === 'deal_review') && (!dealIdNum || isNaN(dealIdNum))) {
        throw new Error('Deal ID is required for deal approval/review workflow. Please select a deal from the dropdown.')
      }
      if (workflowType === 'custom' && !customWorkflowType) {
        throw new Error('Custom workflow type is required for custom workflows')
      }

      // Build request payload
      const requestBody: any = {
        workflow_type: workflowType,
        deal_id: dealIdNum || undefined,
        document_id: documentIdNum || undefined,
        receiver_email: receiverEmail || undefined,
        receiver_user_id: receiverUserId || undefined,
        workflow_metadata: {
          title: workflowTitle,
          description: workflowDescription,
        },
        file_categories: includeFiles ? selectedCategories : undefined,
        file_document_ids: includeFiles && selectedDocuments.length > 0 ? selectedDocuments : undefined,
        expires_in_hours: expiresInHours,
        callback_url: callbackUrl || undefined,
      }

      // Add workflow-specific fields
      if (workflowType === 'notarization') {
        requestBody.required_signers = requiredSigners.filter(s => s.trim())
      }
      if (workflowType === 'document_review') {
        requestBody.review_type = reviewType
      }
      if (workflowType === 'deal_approval' || workflowType === 'deal_review') {
        requestBody.flow_type = flowType
      }
      if (workflowType === 'custom') {
        requestBody.custom_workflow_type = customWorkflowType
      }

      const response = await fetchWithAuth('/api/workflows/delegate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to generate workflow link')
      }

      const data = await response.json()
      setGeneratedLink(data)
      onLinkGenerated?.(data.link, data.workflow_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate workflow link')
    } finally {
      setGenerating(false)
    }
  }

  const handleAddSigner = () => {
    setRequiredSigners([...requiredSigners, ''])
  }

  const handleRemoveSigner = (index: number) => {
    setRequiredSigners(requiredSigners.filter((_, i) => i !== index))
  }

  const handleSignerChange = (index: number, value: string) => {
    const newSigners = [...requiredSigners]
    newSigners[index] = value
    setRequiredSigners(newSigners)
  }

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          <span className="ml-2 text-slate-400">Loading...</span>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Create Workflow Link
          </CardTitle>
          <CardDescription className="text-slate-400">
            Delegate workflows to remote users via encrypted links
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Workflow Type Selection */}
          <div className="space-y-2">
            <Label htmlFor="workflow-type" className="text-slate-300">
              Workflow Type
            </Label>
            <Select
              value={workflowType}
              onValueChange={(value) => setWorkflowType(value as WorkflowType)}
              className="bg-slate-900 border-slate-600 text-slate-200"
            >
              <option value="" disabled>Select workflow type</option>
              <SelectItem value="verification">Verification</SelectItem>
              <SelectItem value="notarization">Notarization</SelectItem>
              <SelectItem value="document_review">Document Review</SelectItem>
              <SelectItem value="deal_approval">Deal Approval</SelectItem>
              <SelectItem value="deal_review">Deal Review</SelectItem>
              <SelectItem value="custom">Custom Workflow</SelectItem>
            </Select>
          </div>

          {/* Deal Selection - Show when deal is required but not provided */}
          {(['verification', 'notarization', 'deal_approval', 'deal_review'].includes(workflowType) && !(selectedDealId || propDealId)) && (
            <div className="space-y-2">
              <Label htmlFor="deal-select" className="text-slate-300">
                Select Deal <span className="text-red-400">*</span>
              </Label>
              <select
                id="deal-select"
                value={selectedDealId || ''}
                onChange={(e) => {
                  const dealId = e.target.value ? parseInt(e.target.value) : undefined
                  setSelectedDealId(dealId)
                  if (dealId) {
                    loadDocuments(dealId)
                  }
                }}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                required
              >
                <option value="">Select a deal...</option>
                {loadingDeals ? (
                  <option disabled>Loading deals...</option>
                ) : (
                  availableDeals.map((deal) => (
                    <option key={deal.id} value={deal.id}>
                      {deal.deal_id} {deal.deal_type ? `(${deal.deal_type})` : ''} - {deal.status}
                    </option>
                  ))
                )}
              </select>
              {!loadingDeals && availableDeals.length === 0 && (
                <p className="text-xs text-slate-500">No deals available. Please create a deal first.</p>
              )}
            </div>
          )}

          {/* Deal Selection for Document Review - Show when document review needs a deal to load documents */}
          {workflowType === 'document_review' && !(selectedDealId || propDealId) && (
            <div className="space-y-2">
              <Label htmlFor="deal-select-doc-review" className="text-slate-300">
                Select Deal (to load documents) <span className="text-red-400">*</span>
              </Label>
              <select
                id="deal-select-doc-review"
                value={selectedDealId || ''}
                onChange={(e) => {
                  const dealId = e.target.value ? parseInt(e.target.value) : undefined
                  setSelectedDealId(dealId)
                  if (dealId) {
                    loadDocuments(dealId)
                  }
                }}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                required
              >
                <option value="">Select a deal to load documents...</option>
                {loadingDeals ? (
                  <option disabled>Loading deals...</option>
                ) : (
                  availableDeals.map((deal) => (
                    <option key={deal.id} value={deal.id}>
                      {deal.deal_id} {deal.deal_type ? `(${deal.deal_type})` : ''} - {deal.status}
                    </option>
                  ))
                )}
              </select>
              {!loadingDeals && availableDeals.length === 0 && (
                <p className="text-xs text-slate-500">No deals available. Please create a deal first.</p>
              )}
            </div>
          )}

          {/* Document Selection - Show when document is required but not provided */}
          {workflowType === 'document_review' && !(selectedDocumentId || propDocumentId) && (selectedDealId || propDealId) && (
            <div className="space-y-2">
              <Label htmlFor="document-select" className="text-slate-300">
                Select Document <span className="text-red-400">*</span>
              </Label>
              <select
                id="document-select"
                value={selectedDocumentId || ''}
                onChange={(e) => {
                  const docId = e.target.value ? parseInt(e.target.value) : undefined
                  setSelectedDocumentId(docId)
                }}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                required
              >
                <option value="">Select a document...</option>
                {availableDocuments.length === 0 ? (
                  <option disabled>No documents available for this deal. Please ensure documents exist.</option>
                ) : (
                  availableDocuments.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.title || doc.filename} {doc.category ? `(${doc.category})` : ''}
                    </option>
                  ))
                )}
              </select>
            </div>
          )}

          {/* Custom Workflow Type */}
          {workflowType === 'custom' && (
            <div className="space-y-2">
              <Label htmlFor="custom-workflow-type" className="text-slate-300">
                Custom Workflow Type Identifier
              </Label>
              <Input
                id="custom-workflow-type"
                value={customWorkflowType}
                onChange={(e) => setCustomWorkflowType(e.target.value)}
                placeholder="e.g., loan_onboarding, esg_reporting"
                className="bg-slate-900 border-slate-600 text-slate-200"
              />
            </div>
          )}

          {/* Metadata Editor */}
          <div className="space-y-4 p-4 bg-slate-900 rounded-lg border border-slate-700">
            <div className="flex items-center gap-2 text-slate-300">
              <Settings className="h-4 w-4" />
              <Label className="font-semibold">Workflow Metadata</Label>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="workflow-title" className="text-slate-300">
                Title
              </Label>
              <Input
                id="workflow-title"
                value={workflowTitle}
                onChange={(e) => setWorkflowTitle(e.target.value)}
                placeholder="Workflow title"
                className="bg-slate-800 border-slate-600 text-slate-200"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="workflow-description" className="text-slate-300">
                Description
              </Label>
              <Textarea
                id="workflow-description"
                value={workflowDescription}
                onChange={(e) => setWorkflowDescription(e.target.value)}
                placeholder="Workflow description and instructions"
                rows={3}
                className="bg-slate-800 border-slate-600 text-slate-200"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="receiver-email" className="text-slate-300">
                  Receiver Email (Optional)
                </Label>
                <Input
                  id="receiver-email"
                  type="email"
                  value={receiverEmail}
                  onChange={(e) => setReceiverEmail(e.target.value)}
                  placeholder="receiver@example.com"
                  className="bg-slate-800 border-slate-600 text-slate-200"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="expires-hours" className="text-slate-300">
                  Expires In (Hours)
                </Label>
                <Input
                  id="expires-hours"
                  type="number"
                  value={expiresInHours}
                  onChange={(e) => setExpiresInHours(parseInt(e.target.value) || 72)}
                  min={1}
                  max={720}
                  className="bg-slate-800 border-slate-600 text-slate-200"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="callback-url" className="text-slate-300">
                Callback URL (Optional)
              </Label>
              <Input
                id="callback-url"
                type="url"
                value={callbackUrl}
                onChange={(e) => setCallbackUrl(e.target.value)}
                placeholder="https://example.com/webhook"
                className="bg-slate-800 border-slate-600 text-slate-200"
              />
            </div>
          </div>

          {/* Workflow-Specific Fields */}
          {workflowType === 'notarization' && (
            <div className="space-y-2 p-4 bg-slate-900 rounded-lg border border-slate-700">
              <Label className="text-slate-300 font-semibold">Required Signers (Wallet Addresses)</Label>
              {requiredSigners.map((signer, index) => (
                <div key={index} className="flex gap-2">
                  <Input
                    value={signer}
                    onChange={(e) => handleSignerChange(index, e.target.value)}
                    placeholder="0x..."
                    className="bg-slate-800 border-slate-600 text-slate-200"
                  />
                  {requiredSigners.length > 1 && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleRemoveSigner(index)}
                      className="border-red-600 text-red-400 hover:bg-red-900/20"
                    >
                      Remove
                    </Button>
                  )}
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddSigner}
                className="w-full border-slate-600"
              >
                Add Signer
              </Button>
            </div>
          )}

          {workflowType === 'document_review' && (
            <div className="space-y-2">
              <Label htmlFor="review-type" className="text-slate-300">
                Review Type
              </Label>
              <Select 
                value={reviewType} 
                onValueChange={setReviewType}
                className="bg-slate-900 border-slate-600 text-slate-200"
              >
                <option value="" disabled>Select review type</option>
                <SelectItem value="general">General</SelectItem>
                <SelectItem value="legal">Legal</SelectItem>
                <SelectItem value="financial">Financial</SelectItem>
                <SelectItem value="compliance">Compliance</SelectItem>
              </Select>
            </div>
          )}

          {(workflowType === 'deal_approval' || workflowType === 'deal_review') && (
            <div className="space-y-2">
              <Label htmlFor="flow-type" className="text-slate-300">
                Flow Type
              </Label>
              <Select 
                value={flowType} 
                onValueChange={setFlowType}
                className="bg-slate-900 border-slate-600 text-slate-200"
              >
                <option value="" disabled>Select flow type</option>
                <SelectItem value="approval">Approval</SelectItem>
                <SelectItem value="review">Review</SelectItem>
                <SelectItem value="closure">Closure</SelectItem>
              </Select>
            </div>
          )}

          {/* File Inclusion Toggle */}
          <div className="flex items-center gap-3">
            <Checkbox
              id="include-files"
              checked={includeFiles}
              onCheckedChange={(checked) => setIncludeFiles(checked === true)}
            />
            <label
              htmlFor="include-files"
              className="text-sm font-medium text-slate-300 cursor-pointer"
            >
              Include relevant files in workflow link
            </label>
          </div>

          {/* Category Selection */}
          {includeFiles && availableCategories.length > 0 && (
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-300">
                File Categories
              </label>
              <div className="grid grid-cols-2 gap-2">
                {availableCategories.map(cat => (
                  <div key={cat} className="flex items-center gap-2">
                    <Checkbox
                      id={`category-${cat}`}
                      checked={selectedCategories.includes(cat)}
                      onCheckedChange={(checked) => {
                        if (checked === true) {
                          setSelectedCategories([...selectedCategories, cat])
                        } else {
                          setSelectedCategories(selectedCategories.filter(c => c !== cat))
                        }
                      }}
                    />
                    <label
                      htmlFor={`category-${cat}`}
                      className="text-sm text-slate-300 capitalize cursor-pointer"
                    >
                      {cat}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Document Selection */}
          {includeFiles && availableDocuments.length > 0 && (
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-300">
                Select Documents
              </label>
              <div className="max-h-48 overflow-y-auto space-y-1 bg-slate-900 rounded p-2">
                {availableDocuments.map(doc => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-2 p-2 hover:bg-slate-800 rounded cursor-pointer"
                    onClick={() => {
                      if (selectedDocuments.includes(doc.id)) {
                        setSelectedDocuments(selectedDocuments.filter(id => id !== doc.id))
                      } else {
                        setSelectedDocuments([...selectedDocuments, doc.id])
                      }
                    }}
                  >
                    <Checkbox
                      checked={selectedDocuments.includes(doc.id)}
                      onCheckedChange={(checked) => {
                        if (checked === true) {
                          setSelectedDocuments([...selectedDocuments, doc.id])
                        } else {
                          setSelectedDocuments(selectedDocuments.filter(id => id !== doc.id))
                        }
                      }}
                    />
                    <FileText className="h-4 w-4 text-slate-400" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-200 truncate">{doc.title || doc.filename}</p>
                      <p className="text-xs text-slate-500">
                        {doc.category} • {(doc.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-900/50 border border-red-700 rounded-lg">
              <p className="text-sm text-red-200">{error}</p>
            </div>
          )}

          {/* Generate Button */}
          <Button
            onClick={handleGenerateLink}
            disabled={generating}
            className="w-full"
          >
            {generating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Share2 className="h-4 w-4 mr-2" />
                Generate Workflow Link
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Generated Link with Sharer */}
      {generatedLink && (
        <WorkflowLinkSharer
          workflowId={generatedLink.workflow_id}
          workflowType={generatedLink.workflow_type}
          link={generatedLink.link}
          encryptedPayload={generatedLink.encrypted_payload}
          metadata={{
            title: workflowTitle,
            description: workflowDescription,
            dealId: dealId,
            documentId: documentId,
            expiresAt: generatedLink.expires_at,
            filesIncluded: generatedLink.files_included,
          }}
        />
      )}
    </div>
  )
}
