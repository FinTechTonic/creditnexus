/**
 * AI CDM Operations Component
 * 
 * Provides AI-powered operations for CDM data:
 * - Add new CDM fields using multimodal fusion
 * - Remove CDM fields with safety evaluation
 * - Edit CDM fields with AI assistance
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Sparkles, Trash2, Edit2, Loader2, AlertCircle } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import type { CreditAgreementData } from '@/context/FDC3Context';

interface AiCdmOperationsProps {
  cdmData: CreditAgreementData;
  multimodalSources: {
    audio?: { text?: string; cdm?: Record<string, unknown> };
    image?: { text?: string; cdm?: Record<string, unknown> };
    document?: { cdm?: Record<string, unknown>; documentId?: number };
    text?: { text: string; cdm?: Record<string, unknown> };
  };
  onUpdate: (updatedData: CreditAgreementData) => void;
  documentId?: number;
}

export function AiCdmOperations({
  cdmData,
  multimodalSources,
  onUpdate,
  documentId
}: AiCdmOperationsProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [operationType, setOperationType] = useState<'add' | 'remove' | 'edit' | null>(null);
  const [showRemoveDialog, setShowRemoveDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [removeFieldPath, setRemoveFieldPath] = useState('');
  const [editFieldPath, setEditFieldPath] = useState('');
  const [editNewValue, setEditNewValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Prepare fusion request from multimodal sources
  const prepareFusionRequest = () => {
    const request: Record<string, unknown> = {
      use_llm_fusion: true,
    };

    if (multimodalSources.audio) {
      if (multimodalSources.audio.cdm) {
        request.audio_cdm = multimodalSources.audio.cdm;
      }
      if (multimodalSources.audio.text) {
        request.audio_text = multimodalSources.audio.text;
      }
    }

    if (multimodalSources.image) {
      if (multimodalSources.image.cdm) {
        request.image_cdm = multimodalSources.image.cdm;
      }
      if (multimodalSources.image.text) {
        request.image_text = multimodalSources.image.text;
      }
    }

    if (multimodalSources.document) {
      if (multimodalSources.document.cdm) {
        request.document_cdm = multimodalSources.document.cdm;
      }
    }

    if (multimodalSources.text) {
      if (multimodalSources.text.cdm) {
        request.text_cdm = multimodalSources.text.cdm;
      }
      if (multimodalSources.text.text) {
        request.text_input = multimodalSources.text.text;
      }
    }

    return request;
  };

  const handleAddCdm = async () => {
    setIsProcessing(true);
    setOperationType('add');
    setError(null);

    try {
      // First, fuse multimodal inputs to get new CDM data
      const fusionRequest = prepareFusionRequest();
      
      // Check if we have any sources
      const hasSources = Object.keys(multimodalSources).length > 0;
      if (!hasSources) {
        throw new Error('No multimodal sources available. Please provide audio, image, document, or text input.');
      }

      // Call fusion endpoint to get new CDM from multimodal sources
      const fusionResponse = await fetchWithAuth('/api/multimodal/fuse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fusionRequest),
      });

      if (!fusionResponse.ok) {
        const errorData = await fusionResponse.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to fuse multimodal inputs');
      }

      await fusionResponse.json(); // fusionResult removed - unused

      // Now call the add endpoint to merge with existing CDM
      const addResponse = await fetchWithAuth('/api/cdm/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...fusionRequest,
          existing_cdm: cdmData,
        }),
      });

      if (!addResponse.ok) {
        const errorData = await addResponse.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to add CDM data');
      }

      const result = await addResponse.json();
      onUpdate(result.agreement);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add CDM data';
      setError(errorMessage);
      console.error('Error adding CDM:', err);
    } finally {
      setIsProcessing(false);
      setOperationType(null);
    }
  };

  const handleRemoveCdm = async () => {
    if (!removeFieldPath.trim()) {
      setError('Please enter a field path to remove');
      return;
    }

    setIsProcessing(true);
    setOperationType('remove');
    setError(null);

    try {
      const response = await fetchWithAuth('/api/cdm/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: documentId,
          field_path: removeFieldPath,
          cdm_data: cdmData,
          multimodal_context: {
            audio_text: multimodalSources.audio?.text || '',
            image_text: multimodalSources.image?.text || '',
            document_text: '',
            text_input: multimodalSources.text?.text || '',
          },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to remove CDM field');
      }

      const result = await response.json();
      onUpdate(result.cdm_data);
      setShowRemoveDialog(false);
      setRemoveFieldPath('');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to remove CDM field';
      setError(errorMessage);
      console.error('Error removing CDM:', err);
    } finally {
      setIsProcessing(false);
      setOperationType(null);
    }
  };

  const handleEditFields = async () => {
    if (!editFieldPath.trim()) {
      setError('Please enter a field path to edit');
      return;
    }

    setIsProcessing(true);
    setOperationType('edit');
    setError(null);

    try {
      let newValue: any = editNewValue;
      // Try to parse as JSON if it looks like JSON
      if (editNewValue.trim().startsWith('{') || editNewValue.trim().startsWith('[')) {
        try {
          newValue = JSON.parse(editNewValue);
        } catch {
          // Not valid JSON, use as string
        }
      }

      const response = await fetchWithAuth('/api/cdm/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: documentId,
          field_path: editFieldPath,
          new_value: newValue,
          cdm_data: cdmData,
          multimodal_context: {
            audio_text: multimodalSources.audio?.text || '',
            image_text: multimodalSources.image?.text || '',
            document_text: '',
            text_input: multimodalSources.text?.text || '',
          },
          use_ai: true,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to edit CDM field');
      }

      const result = await response.json();
      onUpdate(result.cdm_data);
      setShowEditDialog(false);
      setEditFieldPath('');
      setEditNewValue('');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to edit CDM field';
      setError(errorMessage);
      console.error('Error editing CDM:', err);
    } finally {
      setIsProcessing(false);
      setOperationType(null);
    }
  };

  const hasMultimodalSources = Object.keys(multimodalSources).length > 0;

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        <Button
          onClick={handleAddCdm}
          disabled={isProcessing && operationType !== 'add' || !hasMultimodalSources}
          className="bg-emerald-600 hover:bg-emerald-700"
        >
          {isProcessing && operationType === 'add' ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Adding...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4 mr-2" />
              Add CDM
            </>
          )}
        </Button>
        <Button
          onClick={() => setShowRemoveDialog(true)}
          disabled={isProcessing}
          variant="destructive"
        >
          <Trash2 className="h-4 w-4 mr-2" />
          Remove CDM
        </Button>
        <Button
          onClick={() => setShowEditDialog(true)}
          disabled={isProcessing}
          variant="outline"
        >
          <Edit2 className="h-4 w-4 mr-2" />
          Edit Fields
        </Button>
      </div>

      {/* Remove Dialog */}
      <Dialog open={showRemoveDialog} onOpenChange={setShowRemoveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove CDM Field</DialogTitle>
            <DialogDescription>
              Enter the field path to remove (e.g., "parties[0].lei", "facilities[1].interest_terms")
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="remove-path">Field Path</Label>
              <Input
                id="remove-path"
                value={removeFieldPath}
                onChange={(e) => setRemoveFieldPath(e.target.value)}
                placeholder="parties[0].lei"
                className="mt-1"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowRemoveDialog(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleRemoveCdm} disabled={isProcessing}>
                {isProcessing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Removing...
                  </>
                ) : (
                  'Remove'
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit CDM Field</DialogTitle>
            <DialogDescription>
              Enter the field path and new value. AI will assist with validation and formatting.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-path">Field Path</Label>
              <Input
                id="edit-path"
                value={editFieldPath}
                onChange={(e) => setEditFieldPath(e.target.value)}
                placeholder="parties[0].name"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="edit-value">New Value</Label>
              <Input
                id="edit-value"
                value={editNewValue}
                onChange={(e) => setEditNewValue(e.target.value)}
                placeholder="New value or JSON"
                className="mt-1"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowEditDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleEditFields} disabled={isProcessing}>
                {isProcessing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Editing...
                  </>
                ) : (
                  'Edit'
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
