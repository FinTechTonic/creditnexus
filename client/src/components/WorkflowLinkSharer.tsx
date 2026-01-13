import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Copy, Check, Share2, ExternalLink, Loader2 } from 'lucide-react';
import { useFDC3, createWorkflowLinkContext } from '@/context/FDC3Context';
import { fetchWithAuth } from '@/context/AuthContext';

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
}

export function WorkflowLinkSharer({
  workflowId,
  workflowType,
  link,
  encryptedPayload,
  metadata,
  onShared,
}: WorkflowLinkSharerProps) {
  const { isAvailable, broadcastWorkflowLink, raiseIntent } = useFDC3();
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
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <CardTitle className="text-slate-100">Share Workflow Link</CardTitle>
        <CardDescription className="text-slate-400">
          Share this workflow link via desktop (FDC3), native sharing, or copy to clipboard
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Link Display */}
        <div className="space-y-2">
          <Label htmlFor="workflow-link" className="text-slate-300">
            Workflow Link
          </Label>
          <div className="flex gap-2">
            <Input
              id="workflow-link"
              value={link}
              readOnly
              className="bg-slate-900 border-slate-600 text-slate-100 font-mono text-sm"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={handleCopy}
              className="border-slate-600 hover:bg-slate-700"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-400" />
              ) : (
                <Copy className="h-4 w-4 text-slate-400" />
              )}
            </Button>
          </div>
        </div>

        {/* Metadata Display */}
        {metadata && (
          <div className="bg-slate-900 rounded-lg p-4 space-y-2 text-sm">
            {metadata.title && (
              <div>
                <span className="text-slate-400">Title: </span>
                <span className="text-slate-200">{metadata.title}</span>
              </div>
            )}
            {metadata.description && (
              <div>
                <span className="text-slate-400">Description: </span>
                <span className="text-slate-200">{metadata.description}</span>
              </div>
            )}
            {metadata.workflowType && (
              <div>
                <span className="text-slate-400">Type: </span>
                <span className="text-slate-200 capitalize">{metadata.workflowType.replace('_', ' ')}</span>
              </div>
            )}
            {metadata.filesIncluded !== undefined && (
              <div>
                <span className="text-slate-400">Files: </span>
                <span className="text-slate-200">{metadata.filesIncluded} included</span>
              </div>
            )}
            {metadata.expiresAt && (
              <div>
                <span className="text-slate-400">Expires: </span>
                <span className="text-slate-200">
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
          {navigator.share && (
            <Button
              onClick={handleNativeShare}
              disabled={sharing}
              variant="outline"
              className="border-slate-600 hover:bg-slate-700"
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
            className="border-slate-600 hover:bg-slate-700"
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
            className="border-slate-600 hover:bg-slate-700"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Open Link
          </Button>
        </div>

        {/* FDC3 Status */}
        {isAvailable && (
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <div className="h-2 w-2 bg-green-400 rounded-full"></div>
            FDC3 Desktop Integration Available
          </div>
        )}
      </CardContent>
    </Card>
  );
}
