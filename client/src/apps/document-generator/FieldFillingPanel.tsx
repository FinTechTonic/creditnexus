/**
 * Field Filling Panel Component
 * 
 * Provides multiple methods for filling missing CDM fields:
 * 1. Manual entry via form
 * 2. Multimodal re-extraction (append text/image/audio to original document)
 * 3. AI suggestions (use LLM to suggest values)
 */

import { useState, useCallback } from 'react';
import { 
  FileText, 
  Image, 
  Mic, 
  Sparkles, 
  Edit, 
  Upload,
  Loader2,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { fetchWithAuth } from '@/context/AuthContext';
import type { CreditAgreementData } from '@/context/FDC3Context';

interface FieldFillingPanelProps {
  templateId: number | null;
  documentId: number | null;
  cdmData: CreditAgreementData;
  missingFields: string[];
  onFieldsFilled: (fieldOverrides: Record<string, any>) => void;
  onClose?: () => void;
  className?: string;
}

export function FieldFillingPanel({
  templateId,
  documentId,
  cdmData,
  missingFields,
  onFieldsFilled,
  onClose,
  className = '',
}: FieldFillingPanelProps) {
  const [activeTab, setActiveTab] = useState<'manual' | 'multimodal' | 'ai'>('manual');
  const [fieldValues, setFieldValues] = useState<Record<string, any>>({});
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Multimodal state
  const [multimodalText, setMultimodalText] = useState('');
  const [multimodalFile, setMultimodalFile] = useState<File | null>(null);
  const [multimodalFileType, setMultimodalFileType] = useState<'image' | 'audio' | null>(null);

  // AI suggestions state
  const [aiSuggestions, setAiSuggestions] = useState<Record<string, any> | null>(null);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  const handleFieldChange = (fieldPath: string, value: any) => {
    setFieldValues(prev => ({
      ...prev,
      [fieldPath]: value
    }));
  };

  const handleManualSave = () => {
    if (Object.keys(fieldValues).length === 0) {
      setError('Please fill at least one field');
      return;
    }
    onFieldsFilled(fieldValues);
    setSuccess('Fields saved successfully');
  };

  const handleMultimodalExtract = async () => {
    if (!documentId) {
      setError('Document ID is required for multimodal extraction');
      return;
    }

    if (!multimodalText && !multimodalFile) {
      setError('Please provide text, image, or audio input');
      return;
    }

    try {
      setIsProcessing(true);
      setError(null);
      setSuccess(null);

      // Create form data for multimodal extraction
      const formData = new FormData();
      formData.append('document_id', documentId.toString());
      
      if (multimodalText) {
        formData.append('additional_text', multimodalText);
      }
      
      if (multimodalFile) {
        formData.append('file', multimodalFile);
        formData.append('file_type', multimodalFileType || 'text');
      }

      // Call re-extraction endpoint (to be implemented)
      const response = await fetchWithAuth('/api/documents/re-extract', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Re-extraction failed');
      }

      const data = await response.json();
      
      // Extract new field values from updated CDM data
      if (data.cdm_data) {
        // Compare with original to find new/missing fields
        const newFields: Record<string, any> = {};
        for (const fieldPath of missingFields) {
          // Simple field extraction - in production, use FieldPathParser
          const value = extractFieldValue(data.cdm_data, fieldPath);
          if (value !== null && value !== undefined) {
            newFields[fieldPath] = value;
          }
        }
        
        if (Object.keys(newFields).length > 0) {
          onFieldsFilled(newFields);
          setSuccess(`Extracted ${Object.keys(newFields).length} new field(s)`);
        } else {
          setError('No new fields extracted. Try providing more information.');
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Multimodal extraction failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleGetAISuggestions = async () => {
    if (!templateId || missingFields.length === 0) {
      setError('Template ID and missing fields are required');
      return;
    }

    try {
      setLoadingSuggestions(true);
      setError(null);

      const response = await fetchWithAuth('/api/chatbot/fill-fields', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cdm_data: cdmData,
          required_fields: missingFields,
          conversation_context: 'User is filling missing fields for document generation',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to get AI suggestions');
      }

      const data = await response.json();
      
      // Handle both response formats for compatibility
      const suggestions = data.field_guidance?.suggested_values || data.suggestions || {};
      
      if (Object.keys(suggestions).length > 0) {
        setAiSuggestions(suggestions);
        setSuccess('AI suggestions loaded');
      } else {
        setError('No AI suggestions available');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get AI suggestions');
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleApplyAISuggestions = () => {
    if (!aiSuggestions) {
      setError('No AI suggestions available');
      return;
    }

    onFieldsFilled(aiSuggestions);
    setSuccess('AI suggestions applied');
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setMultimodalFile(file);
    
    // Determine file type
    if (file.type.startsWith('image/')) {
      setMultimodalFileType('image');
    } else if (file.type.startsWith('audio/')) {
      setMultimodalFileType('audio');
    } else {
      setMultimodalFileType(null);
    }
  };

  // Simple field value extractor (simplified - in production, use proper parser)
  const extractFieldValue = (obj: any, path: string): any => {
    const parts = path.split('.');
    let current = obj;
    for (const part of parts) {
      if (part.includes('[')) {
        // Handle array/index access
        const [key, indexStr] = part.split('[');
        const index = parseInt(indexStr.replace(']', ''));
        if (current[key] && Array.isArray(current[key]) && current[key][index]) {
          current = current[key][index];
        } else {
          return null;
        }
      } else {
        current = current?.[part];
        if (current === undefined || current === null) {
          return null;
        }
      }
    }
    return current;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Edit className="w-5 h-5" />
          Fill Missing Fields
        </CardTitle>
        <p className="text-sm text-gray-600 mt-1">
          {missingFields.length} missing field(s) detected. Choose a method to fill them.
        </p>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="manual" className="flex items-center gap-2">
              <Edit className="w-4 h-4" />
              Manual
            </TabsTrigger>
            <TabsTrigger value="multimodal" className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              Multimodal
            </TabsTrigger>
            <TabsTrigger value="ai" className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              AI Suggestions
            </TabsTrigger>
          </TabsList>

          {/* Manual Entry Tab */}
          <TabsContent value="manual" className="mt-4 space-y-4">
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {missingFields.slice(0, 10).map((fieldPath, idx) => {
                const fieldName = fieldPath.split('.').pop() || fieldPath;
                const fieldLabel = fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                
                return (
                  <div key={idx} className="space-y-2">
                    <Label htmlFor={`field-${idx}`} className="text-sm font-medium">
                      {fieldLabel}
                      <span className="text-xs text-gray-500 ml-2">({fieldPath})</span>
                    </Label>
                    <Input
                      id={`field-${idx}`}
                      value={fieldValues[fieldPath] || ''}
                      onChange={(e) => handleFieldChange(fieldPath, e.target.value)}
                      placeholder={`Enter ${fieldLabel.toLowerCase()}`}
                      className="w-full"
                    />
                  </div>
                );
              })}
              {missingFields.length > 10 && (
                <p className="text-xs text-gray-500">
                  Showing first 10 fields. Fill remaining fields after saving.
                </p>
              )}
            </div>
            <div className="flex gap-2 pt-4 border-t">
              <Button
                onClick={handleManualSave}
                disabled={Object.keys(fieldValues).length === 0}
                className="flex-1"
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Save Fields
              </Button>
              {onClose && (
                <Button variant="outline" onClick={onClose}>
                  Cancel
                </Button>
              )}
            </div>
          </TabsContent>

          {/* Multimodal Re-extraction Tab */}
          <TabsContent value="multimodal" className="mt-4 space-y-4">
            <div className="space-y-4">
              <div>
                <Label htmlFor="multimodal-text" className="text-sm font-medium">
                  Additional Text
                </Label>
                <Textarea
                  id="multimodal-text"
                  value={multimodalText}
                  onChange={(e) => setMultimodalText(e.target.value)}
                  placeholder="Paste additional text from the document or enter new information..."
                  className="mt-1 min-h-[100px]"
                />
              </div>

              <div>
                <Label htmlFor="multimodal-file" className="text-sm font-medium">
                  Upload Image or Audio
                </Label>
                <div className="mt-1 flex items-center gap-4">
                  <Input
                    id="multimodal-file"
                    type="file"
                    accept="image/*,audio/*"
                    onChange={handleFileSelect}
                    className="flex-1"
                  />
                  {multimodalFile && (
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      {multimodalFileType === 'image' && <Image className="w-4 h-4" />}
                      {multimodalFileType === 'audio' && <Mic className="w-4 h-4" />}
                      <span>{multimodalFile.name}</span>
                    </div>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Upload images (OCR) or audio files (transcription) to extract additional information
                </p>
              </div>
            </div>

            <div className="flex gap-2 pt-4 border-t">
              <Button
                onClick={handleMultimodalExtract}
                disabled={isProcessing || (!multimodalText && !multimodalFile)}
                className="flex-1"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Extracting...
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4 mr-2" />
                    Re-extract Fields
                  </>
                )}
              </Button>
              {onClose && (
                <Button variant="outline" onClick={onClose}>
                  Cancel
                </Button>
              )}
            </div>
          </TabsContent>

          {/* AI Suggestions Tab */}
          <TabsContent value="ai" className="mt-4 space-y-4">
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800">
                  AI will analyze your CDM data and suggest values for missing fields based on
                  the template requirements and existing data patterns.
                </p>
              </div>

              {!aiSuggestions && (
                <Button
                  onClick={handleGetAISuggestions}
                  disabled={loadingSuggestions}
                  className="w-full"
                >
                  {loadingSuggestions ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating Suggestions...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Get AI Suggestions
                    </>
                  )}
                </Button>
              )}

              {aiSuggestions && (
                <div className="space-y-4">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <p className="text-sm text-green-800 font-medium mb-2">
                      AI Suggestions Generated
                    </p>
                    <div className="space-y-2">
                      {Object.entries(aiSuggestions).slice(0, 5).map(([fieldPath, value]) => (
                        <div key={fieldPath} className="text-xs">
                          <span className="font-medium">{fieldPath.split('.').pop()}:</span>{' '}
                          <span className="text-gray-600">{String(value)}</span>
                        </div>
                      ))}
                      {Object.keys(aiSuggestions).length > 5 && (
                        <p className="text-xs text-gray-500">
                          +{Object.keys(aiSuggestions).length - 5} more suggestions
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      onClick={handleApplyAISuggestions}
                      className="flex-1"
                    >
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Apply Suggestions
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setAiSuggestions(null)}
                    >
                      Regenerate
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {/* Error/Success Messages */}
        {error && (
          <div className="mt-4 flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="mt-4 flex items-center gap-2 text-sm text-green-600 bg-green-50 border border-green-200 rounded-lg p-3">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{success}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
