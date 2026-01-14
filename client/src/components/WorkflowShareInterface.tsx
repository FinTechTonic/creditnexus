/**
 * Workflow Share Interface - Routes to and hydrates workflow components.
 * 
 * This component serves as a central hub for workflow sharing functionality,
 * routing users to the appropriate workflow creation or processing interface.
 */

import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Share2,
  Send,
  Eye,
  Settings,
  Link as LinkIcon,
  Copy,
  Check,
  X
} from 'lucide-react'
import { WorkflowLinkCreator } from '@/apps/workflow/WorkflowLinkCreator'
import { WorkflowProcessingPage } from './WorkflowProcessingPage'
import { WorkflowDelegationDashboard } from './WorkflowDelegationDashboard'
import { WorkflowLinkSharer } from './WorkflowLinkSharer'
import { useFDC3 } from '@/context/FDC3Context'
import type { WorkflowLinkContext } from '@/context/FDC3Context'
import { useThemeClasses } from '@/utils/themeUtils'

type ShareView = 'create' | 'process' | 'dashboard' | 'share'

interface WorkflowShareInterfaceProps {
  initialView?: ShareView
  dealId?: number
  documentId?: number
  onWorkflowCreated?: (link: string, workflowId: string) => void
}

export function WorkflowShareInterface({
  initialView = 'create',
  dealId: propDealId,
  documentId: propDocumentId,
  onWorkflowCreated
}: WorkflowShareInterfaceProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { listenForWorkflowLinks } = useFDC3()
  const classes = useThemeClasses()

  const [activeView, setActiveView] = useState<ShareView>(initialView)
  const [generatedLink, setGeneratedLink] = useState<string | null>(null)
  const [generatedWorkflowId, setGeneratedWorkflowId] = useState<string | null>(null)
  const [sharerData, setSharerData] = useState<any>(null)
  const [copied, setCopied] = useState(false)

  // Hydrate dealId and documentId from URL params or props
  const dealId = propDealId || (searchParams.get('dealId') ? parseInt(searchParams.get('dealId')!) : undefined)
  const documentId = propDocumentId || (searchParams.get('documentId') ? parseInt(searchParams.get('documentId')!) : undefined)

  // Determine view from URL params
  useEffect(() => {
    const viewParam = searchParams.get('view')
    const payloadParam = searchParams.get('payload')

    if (payloadParam) {
      setActiveView('process')
    } else if (viewParam && ['create', 'process', 'dashboard', 'share'].includes(viewParam)) {
      setActiveView(viewParam as ShareView)
    }
  }, [searchParams])

  // Listen for FDC3 workflow links
  useEffect(() => {
    listenForWorkflowLinks((workflowCtx: WorkflowLinkContext) => {
      if (workflowCtx.linkPayload) {
        const params: Record<string, string> = { view: 'process', payload: workflowCtx.linkPayload }
        if (workflowCtx.metadata?.dealId) params.dealId = workflowCtx.metadata.dealId.toString()
        if (workflowCtx.metadata?.documentId) params.documentId = workflowCtx.metadata.documentId.toString()
        setSearchParams(params)
        setActiveView('process')
      }
    })
  }, [listenForWorkflowLinks, setSearchParams])

  // Handle workflow link generation
  const handleLinkGenerated = (link: string, workflowId: string) => {
    setGeneratedLink(link)
    setGeneratedWorkflowId(workflowId)
    setActiveView('share')

    // Extract encrypted payload from link
    const url = new URL(link)
    const payload = url.searchParams.get('payload') || workflowId

    setSharerData({
      workflowId: workflowId,
      workflowType: 'verification', // This would come from the creator
      link: link,
      encryptedPayload: payload,
      metadata: {
        title: 'Workflow Link',
        description: 'Share this workflow link with others',
      },
    })

    onWorkflowCreated?.(link, workflowId)
  }

  // Handle copy link
  const handleCopyLink = async () => {
    if (generatedLink) {
      await navigator.clipboard.writeText(generatedLink)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Navigate to view (preserve dealId and documentId)
  const navigateToView = (view: ShareView) => {
    const params: Record<string, string> = { view }
    if (dealId) params.dealId = dealId.toString()
    if (documentId) params.documentId = documentId.toString()
    setSearchParams(params)
    setActiveView(view)
  }

  // Render based on active view
  const renderView = () => {
    switch (activeView) {
      case 'create':
        return (
          <div className="space-y-4">
            <Card className={`${classes.background.card} ${classes.border.default}`}>
              <CardHeader>
                <CardTitle className={`${classes.text.primary} flex items-center gap-2`}>
                  <Send className="h-5 w-5" />
                  Create Workflow Link
                </CardTitle>
                <CardDescription className={classes.text.secondary}>
                  Delegate workflows to remote users via encrypted links
                </CardDescription>
              </CardHeader>
              <CardContent>
                <WorkflowLinkCreator
                  dealId={dealId}
                  documentId={documentId}
                  onLinkGenerated={handleLinkGenerated}
                />
              </CardContent>
            </Card>
          </div>
        )

      case 'process':
        return (
          <div className="space-y-4">
            <Card className={`${classes.background.card} ${classes.border.default}`}>
              <CardHeader>
                <CardTitle className={`${classes.text.primary} flex items-center gap-2`}>
                  <Eye className="h-5 w-5" />
                  Process Workflow
                </CardTitle>
                <CardDescription className={classes.text.secondary}>
                  Review and process a workflow link
                </CardDescription>
              </CardHeader>
              <CardContent>
                <WorkflowProcessingPage />
              </CardContent>
            </Card>
          </div>
        )

      case 'dashboard':
        return (
          <div className="space-y-4">
            <WorkflowDelegationDashboard />
          </div>
        )

      case 'share':
        return sharerData ? (
          <div className="space-y-4">
            <Card className={`${classes.background.card} ${classes.border.default}`}>
              <CardHeader>
                <CardTitle className={`${classes.text.primary} flex items-center gap-2`}>
                  <Share2 className="h-5 w-5" />
                  Share Workflow Link
                </CardTitle>
                <CardDescription className={classes.text.secondary}>
                  Share this workflow link via desktop (FDC3), native sharing, or copy to clipboard
                </CardDescription>
              </CardHeader>
              <CardContent>
                <WorkflowLinkSharer
                  {...sharerData}
                  onClose={() => {
                    setSharerData(null)
                    navigateToView('create')
                  }}
                />
              </CardContent>
            </Card>
          </div>
        ) : (
          <Card className={`${classes.background.card} ${classes.border.default}`}>
            <CardContent className="pt-6">
              <div className="text-center py-12">
                <LinkIcon className={`h-12 w-12 ${classes.text.muted} mx-auto mb-4`} />
                <p className={`${classes.text.secondary} mb-4`}>No workflow link to share</p>
                <Button onClick={() => navigateToView('create')} className="bg-blue-600 hover:bg-blue-700">
                  Create Workflow Link
                </Button>
              </div>
            </CardContent>
          </Card>
        )

      default:
        return null
    }
  }

  const handleClose = () => {
    // Check if we came from a specific route
    const from = (location.state as { from?: string })?.from;
    if (from) {
      navigate(from);
    } else {
      // Default to dashboard or previous page
      navigate(-1);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Close Button */}
      <div className="flex items-center justify-between">
        <h1 className={`text-2xl font-bold ${classes.text.primary}`}>Workflow Share</h1>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClose}
          className={`${classes.text.secondary} ${classes.interactive.hover.text} ${classes.interactive.hover.background}`}
        >
          <X className="h-4 w-4 mr-2" />
          Close
        </Button>
      </div>

      {/* Navigation Tabs */}
      <Card className={`${classes.background.card} ${classes.border.default}`}>
        <CardContent className="pt-6">
          <Tabs value={activeView} onValueChange={(v) => navigateToView(v as ShareView)}>
            <TabsList className={`grid w-full grid-cols-4 ${classes.background.primary}`}>
              <TabsTrigger value="create" className={`data-[state=active]:${classes.background.card}`}>
                <Send className="h-4 w-4 mr-2" />
                Create
              </TabsTrigger>
              <TabsTrigger value="process" className={`data-[state=active]:${classes.background.card}`}>
                <Eye className="h-4 w-4 mr-2" />
                Process
              </TabsTrigger>
              <TabsTrigger value="dashboard" className={`data-[state=active]:${classes.background.card}`}>
                <Settings className="h-4 w-4 mr-2" />
                Dashboard
              </TabsTrigger>
              <TabsTrigger value="share" className={`data-[state=active]:${classes.background.card}`}>
                <Share2 className="h-4 w-4 mr-2" />
                Share
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      {activeView === 'create' && generatedLink && (
        <Card className="bg-blue-900/20 border-blue-700">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-blue-300 mb-1">Link Generated!</p>
                <p className="text-xs text-blue-400 truncate">{generatedLink}</p>
              </div>
              <div className="flex gap-2 ml-4">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCopyLink}
                  className="border-blue-600 text-blue-400"
                >
                  {copied ? (
                    <>
                      <Check className="h-4 w-4 mr-1" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4 mr-1" />
                      Copy
                    </>
                  )}
                </Button>
                <Button
                  size="sm"
                  onClick={() => navigateToView('share')}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <Share2 className="h-4 w-4 mr-1" />
                  Share
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active View Content */}
      {renderView()}
    </div>
  )
}
