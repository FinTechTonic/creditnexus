import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Copy, Check, Share2, ExternalLink, Loader2, X } from 'lucide-react';
import { useFDC3, createWorkflowLinkContext } from '@/context/FDC3Context';
// fetchWithAuth removed - unused
import { useThemeClasses } from '@/utils/themeUtils';

interface WorkflowLinkSharerProps {
  workflowId: string;
  workflowType: string;
  link: string;
  encryptedPayload: string;
  metadata?: {
    title?: string;
    description?: string;
    dealId?: number;
    documentId?: number;
    workflowType?: string;
    senderInfo?: {
      user_id?: number;
      email?: string;
      name?: string;
    };
    receiverInfo?: {
      user_id?: number;
      email?: string;
      name?: string;
    };
    expiresAt?: string;
    filesIncluded?: number;
  };
  onShared?: () => void;
  onClose?: () => void;
}

export function WorkflowLinkSharer({
  workflowId,
  workflowType,
  link,
  encryptedPayload,
  metadata,
  onShared,
  onClose,
}: WorkflowLinkSharerProps) {
  const { isAvailable, broadcastWorkflowLink, raiseIntent } = useFDC3();
  const classes = useThemeClasses();
  const [copied, setCopied] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [fdc3Shared, setFdc3Shared] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      onShared?.();
    } catch (err) {
      console.error('Failed to copy link:', err);
    }
  };

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        setSharing(true);
        await navigator.share({
          title: metadata?.title || 'Workflow Link',
          text: metadata?.description || 'Please process this workflow.',
          url: link,
        });
        onShared?.();
      } catch (err) {
        // User cancelled or share failed
        console.log('Share cancelled or failed:', err);
      } finally {
        setSharing(false);
      }
    } else {
      // Fallback to copy
      handleCopy();
    }
  };

  const handleFDC3Share = async () => {
    if (!isAvailable) {
      console.warn('[FDC3] FDC3 not available, cannot share via desktop');
      return;
    }

    try {
      setSharing(true);
      
      // Create workflow link context
      const workflowContext = createWorkflowLinkContext(
        workflowId,
        workflowType,
        encryptedPayload,
        metadata
      );

      // Broadcast context
      await broadcastWorkflowLink(workflowContext);
      setFdc3Shared(true);
      
      // Also raise ShareWorkflowLink intent
      try {
        await raiseIntent('ShareWorkflowLink', workflowContext);
      } catch (err) {
        console.warn('[FDC3] Failed to raise ShareWorkflowLink intent:', err);
      }

      onShared?.();
    } catch (err) {
      console.error('[FDC3] Failed to share workflow link:', err);
    } finally {
      setSharing(false);
    }
  };

  const handleOpenLink = () => {
    window.open(link, '_blank');
  };

  return (
    <Card className={`${classes.background.card} ${classes.border.default}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className={classes.text.primary}>Share Workflow Link</CardTitle>
            <CardDescription className={classes.text.secondary}>
              Share this workflow link via desktop (FDC3), native sharing, or copy to clipboard
            </CardDescription>
          </div>
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className={`${classes.text.secondary} ${classes.interactive.hover.text}`}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Link Display */}
        <div className="space-y-2">
          <Label htmlFor="workflow-link" className={classes.text.secondary}>
            Workflow Link
          </Label>
          <div className="flex gap-2">
            <Input
              id="workflow-link"
              value={link}
              readOnly
              className={`${classes.background.primary} ${classes.border.muted} ${classes.text.primary} font-mono text-sm`}
            />
            <Button
              variant="outline"
              size="icon"
              onClick={handleCopy}
              className={`${classes.border.muted} ${classes.interactive.hover.background}`}
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-400" />
              ) : (
                <Copy className={`h-4 w-4 ${classes.text.secondary}`} />
              )}
            </Button>
          </div>
        </div>

        {/* Metadata Display */}
        {metadata && (
          <div className={`${classes.background.primary} rounded-lg p-4 space-y-2 text-sm`}>
            {metadata.title && (
              <div>
                <span className={classes.text.secondary}>Title: </span>
                <span className={classes.text.primary}>{metadata.title}</span>
              </div>
            )}
            {metadata.description && (
              <div>
                <span className={classes.text.secondary}>Description: </span>
                <span className={classes.text.primary}>{metadata.description}</span>
              </div>
            )}
            {(metadata?.workflowType || workflowType) && (
              <div>
                <span className={classes.text.secondary}>Type: </span>
                <span className={`${classes.text.primary} capitalize`}>{(metadata?.workflowType || workflowType).replace('_', ' ')}</span>
              </div>
            )}
            {metadata.filesIncluded !== undefined && (
              <div>
                <span className={classes.text.secondary}>Files: </span>
                <span className={classes.text.primary}>{metadata.filesIncluded} included</span>
              </div>
            )}
            {metadata.expiresAt && (
              <div>
                <span className={classes.text.secondary}>Expires: </span>
                <span className={classes.text.primary}>
                  {new Date(metadata.expiresAt).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2">
          {/* FDC3 Desktop Share */}
          {isAvailable && (
            <Button
              onClick={handleFDC3Share}
              disabled={sharing}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {sharing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Sharing...
                </>
              ) : (
                <>
                  <Share2 className="h-4 w-4 mr-2" />
                  {fdc3Shared ? 'Shared via FDC3' : 'Share via Desktop (FDC3)'}
                </>
              )}
            </Button>
          )}

          {/* Native Share */}
          {typeof navigator !== 'undefined' && typeof navigator.share === 'function' && (
            <Button
              onClick={handleNativeShare}
              disabled={sharing}
              variant="outline"
              className={`${classes.border.muted} ${classes.interactive.hover.background}`}
            >
              {sharing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Sharing...
                </>
              ) : (
                <>
                  <Share2 className="h-4 w-4 mr-2" />
                  Native Share
                </>
              )}
            </Button>
          )}

          {/* Copy to Clipboard */}
          <Button
            onClick={handleCopy}
            variant="outline"
            className={`${classes.border.muted} ${classes.interactive.hover.background}`}
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-2" />
                Copy Link
              </>
            )}
          </Button>

          {/* Open Link */}
          <Button
            onClick={handleOpenLink}
            variant="outline"
            className={`${classes.border.muted} ${classes.interactive.hover.background}`}
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Open Link
          </Button>
        </div>

        {/* FDC3 Status */}
        {isAvailable && (
          <div className={`text-xs ${classes.text.secondary} flex items-center gap-2`}>
            <div className="h-2 w-2 bg-green-400 rounded-full"></div>
            FDC3 Desktop Integration Available
          </div>
        )}
      </CardContent>
    </Card>
  );
}
