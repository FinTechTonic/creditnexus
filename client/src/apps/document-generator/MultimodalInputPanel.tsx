/**
 * Multimodal Input Panel Component
 * 
 * Shows all input sources, extracted data, conflicts, and triggers fusion.
 * Integrates audio, image, document retrieval, and text inputs.
 */

import { useState, useCallback } from 'react';
import { 
  Mic, 
  Image as ImageIcon, 
  FileText, 
  Type, 
  Merge, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  AlertTriangle,
  X,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { fetchWithAuth } from '../../context/AuthContext';
import { AudioRecorder } from './AudioRecorder';
import { ImageUploader } from './ImageUploader';
import { DocumentSearch } from './DocumentSearch';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { Button } from '../../components/ui/button';

interface SourceData {
  type: 'audio' | 'image' | 'document' | 'text';
  cdmData?: Record<string, unknown>;
  rawText?: string;
  metadata?: Record<string, unknown>;
}

interface Conflict {
  field_path: string;
  values: Array<{
    value: string;
    source: {
      source_type: string;
      source_id?: string;
      confidence: number;
    };
  }>;
  resolution?: string;
  resolved_value?: string;
}

interface FusionResult {
  status: string;
  agreement: Record<string, unknown>;
  source_tracking: Record<string, {
    source_type: string;
    source_id?: string;
    confidence: number;
  }>;
  conflicts: Conflict[];
  fusion_method: string;
  conflicts_count: number;
}

interface MultimodalInputPanelProps {
  onFusionComplete?: (result: FusionResult) => void;
  onError?: (error: string) => void;
  className?: string;
}

export function MultimodalInputPanel({
  onFusionComplete,
  onError,
  className = '',
}: MultimodalInputPanelProps) {
  const [sources, setSources] = useState<Record<string, SourceData>>({});
  const [fusionResult, setFusionResult] = useState<FusionResult | null>(null);
  const [isFusing, setIsFusing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [expandedConflicts, setExpandedConflicts] = useState<Set<string>>(new Set());

  // Handle audio transcription complete
  const handleAudioComplete = useCallback((result: {
    transcription: string;
    agreement?: Record<string, unknown>;
    extraction_status?: string;
  }) => {
    setSources((prev) => ({
      ...prev,
      audio: {
        type: 'audio',
        cdmData: result.agreement,
        rawText: result.transcription,
        metadata: {
          extraction_status: result.extraction_status,
        },
      },
    }));
    setError(null);
  }, []);

  // Handle image extraction complete
  const handleImageComplete = useCallback((result: {
    ocr_text: string;
    agreement?: Record<string, unknown>;
    extraction_status?: string;
  }) => {
    setSources((prev) => ({
      ...prev,
      image: {
        type: 'image',
        cdmData: result.agreement,
        rawText: result.ocr_text,
        metadata: {
          extraction_status: result.extraction_status,
        },
      },
    }));
    setError(null);
  }, []);

  // Handle document selection
  const handleDocumentSelect = useCallback((document: {
    cdm_data?: Record<string, unknown> | null;
    document: {
      title: string;
    };
  }) => {
    setSources((prev) => ({
      ...prev,
      document: {
        type: 'document',
        cdmData: document.cdm_data || undefined,
        metadata: {
          document_title: document.document.title,
        },
      },
    }));
    setError(null);
  }, []);

  // Handle text input
  const handleTextInput = useCallback((text: string, cdmData?: Record<string, unknown>) => {
    if (!text.trim()) {
      // Remove text source if empty
      setSources((prev) => {
        const updated = { ...prev };
        delete updated.text;
        return updated;
      });
      return;
    }

    setSources((prev) => ({
      ...prev,
      text: {
        type: 'text',
        cdmData: cdmData,
        rawText: text,
      },
    }));
    setError(null);
  }, []);

  // Toggle source expansion
  const toggleSourceExpansion = useCallback((sourceType: string) => {
    setExpandedSources((prev) => {
      const updated = new Set(prev);
      if (updated.has(sourceType)) {
        updated.delete(sourceType);
      } else {
        updated.add(sourceType);
      }
      return updated;
    });
  }, []);

  // Toggle conflict expansion
  const toggleConflictExpansion = useCallback((fieldPath: string) => {
    setExpandedConflicts((prev) => {
      const updated = new Set(prev);
      if (updated.has(fieldPath)) {
        updated.delete(fieldPath);
      } else {
        updated.add(fieldPath);
      }
      return updated;
    });
  }, []);

  // Trigger fusion
  const handleFuse = useCallback(async () => {
    // Check if we have at least one source
    const sourceCount = Object.keys(sources).length;
    if (sourceCount === 0) {
      setError('Please provide at least one input source (audio, image, document, or text)');
      return;
    }

    try {
      setIsFusing(true);
      setError(null);
      setFusionResult(null);

      // Prepare fusion request
      const fusionRequest: Record<string, unknown> = {
        use_llm_fusion: true,
      };

      // Add CDM data and raw text from each source
      if (sources.audio) {
        if (sources.audio.cdmData) {
          fusionRequest.audio_cdm = sources.audio.cdmData;
        }
        if (sources.audio.rawText) {
          fusionRequest.audio_text = sources.audio.rawText;
        }
      }

      if (sources.image) {
        if (sources.image.cdmData) {
          fusionRequest.image_cdm = sources.image.cdmData;
        }
        if (sources.image.rawText) {
          fusionRequest.image_text = sources.image.rawText;
        }
      }

      if (sources.document) {
        if (sources.document.cdmData) {
          fusionRequest.document_cdm = sources.document.cdmData;
        }
        if (sources.document.rawText) {
          fusionRequest.document_text = sources.document.rawText;
        }
      }

      if (sources.text) {
        if (sources.text.cdmData) {
          fusionRequest.text_cdm = sources.text.cdmData;
        }
        if (sources.text.rawText) {
          fusionRequest.text_input = sources.text.rawText;
        }
      }

      // Call fusion endpoint
      const response = await fetchWithAuth('/api/multimodal/fuse', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(fusionRequest),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail?.message || errorData.detail || 'Fusion failed';
        throw new Error(errorMessage);
      }

      const result: FusionResult = await response.json();
      setFusionResult(result);
      onFusionComplete?.(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Fusion failed';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setIsFusing(false);
    }
  }, [sources, onFusionComplete, onError]);

  // Remove source
  const removeSource = useCallback((sourceType: string) => {
    setSources((prev) => {
      const updated = { ...prev };
      delete updated[sourceType];
      return updated;
    });
    setFusionResult(null);
  }, []);

  // Get source icon
  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'audio':
        return <Mic className="w-4 h-4" />;
      case 'image':
        return <ImageIcon className="w-4 h-4" />;
      case 'document':
        return <FileText className="w-4 h-4" />;
      case 'text':
        return <Type className="w-4 h-4" />;
      default:
        return null;
    }
  };

  // Get source status badge
  const getSourceStatusBadge = (source: SourceData) => {
    if (!source.cdmData) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
          No CDM Data
        </span>
      );
    }
    const status = source.metadata?.extraction_status;
    if (status === 'success') {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
          <CheckCircle2 className="w-3 h-3 mr-1" />
          Success
        </span>
      );
    }
    if (status === 'partial_data_missing') {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
          <AlertTriangle className="w-3 h-3 mr-1" />
          Partial
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200">
        Extracted
      </span>
    );
  };

  const hasSources = Object.keys(sources).length > 0;
  const canFuse = hasSources && !isFusing;

  return (
    <div className={`space-y-4 ${className}`}>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Merge className="w-5 h-5" />
            Multimodal Input Sources
          </CardTitle>
          <CardDescription>
            Combine data from multiple sources (audio, image, document, text) into unified CDM
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="audio" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="audio" className="flex items-center gap-2">
                <Mic className="w-4 h-4" />
                Audio
              </TabsTrigger>
              <TabsTrigger value="image" className="flex items-center gap-2">
                <ImageIcon className="w-4 h-4" />
                Image
              </TabsTrigger>
              <TabsTrigger value="document" className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Document
              </TabsTrigger>
              <TabsTrigger value="text" className="flex items-center gap-2">
                <Type className="w-4 h-4" />
                Text
              </TabsTrigger>
            </TabsList>

            <TabsContent value="audio" className="mt-4">
              <AudioRecorder
                onTranscriptionComplete={handleAudioComplete}
                onError={(err) => {
                  setError(err);
                  onError?.(err);
                }}
                extractCdm={true}
              />
            </TabsContent>

            <TabsContent value="image" className="mt-4">
              <ImageUploader
                onExtractionComplete={handleImageComplete}
                onError={(err) => {
                  setError(err);
                  onError?.(err);
                }}
                extractCdm={true}
              />
            </TabsContent>

            <TabsContent value="document" className="mt-4">
              <DocumentSearch
                onDocumentSelect={handleDocumentSelect}
                onCdmDataSelect={(cdmData) => {
                  handleDocumentSelect({ cdm_data: cdmData, document: { title: 'Selected Document' } });
                }}
              />
            </TabsContent>

            <TabsContent value="text" className="mt-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Text Input</label>
                <textarea
                  className="w-full min-h-[200px] p-3 border rounded-md resize-y font-mono text-sm"
                  placeholder="Paste or type text here..."
                  onChange={(e) => handleTextInput(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Text will be automatically extracted for CDM data
                </p>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Active Sources */}
      {hasSources && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Active Sources</CardTitle>
            <CardDescription>
              {Object.keys(sources).length} source(s) ready for fusion
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(sources).map(([key, source]) => (
                <div
                  key={key}
                  className="border rounded-lg p-3 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getSourceIcon(source.type)}
                      <span className="font-medium capitalize">{source.type}</span>
                      {getSourceStatusBadge(source)}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleSourceExpansion(key)}
                      >
                        {expandedSources.has(key) ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeSource(key)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>

                  {expandedSources.has(key) && (
                    <div className="mt-2 space-y-2 text-sm">
                      {source.rawText && (
                        <div>
                          <p className="font-medium mb-1">Raw Text:</p>
                          <p className="text-muted-foreground font-mono text-xs max-h-32 overflow-y-auto">
                            {source.rawText.substring(0, 500)}
                            {source.rawText.length > 500 && '...'}
                          </p>
                        </div>
                      )}
                      {source.cdmData && (
                        <div>
                          <p className="font-medium mb-1">CDM Data:</p>
                          <pre className="text-xs bg-muted p-2 rounded max-h-48 overflow-y-auto">
                            {JSON.stringify(source.cdmData, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Fusion Button */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Fuse Sources</h3>
              <p className="text-sm text-muted-foreground">
                Combine all sources into unified CDM data
              </p>
            </div>
            <Button
              onClick={handleFuse}
              disabled={!canFuse}
              className="flex items-center gap-2"
            >
              {isFusing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Fusing...
                </>
              ) : (
                <>
                  <Merge className="w-4 h-4" />
                  Fuse Sources
                </>
              )}
            </Button>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-800 dark:text-red-200">Error</p>
                <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Fusion Result */}
      {fusionResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
              Fusion Complete
            </CardTitle>
            <CardDescription>
              Method: {fusionResult.fusion_method} | Conflicts: {fusionResult.conflicts_count}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Fused Agreement */}
            <div>
              <h4 className="font-medium mb-2">Fused CDM Data</h4>
              <pre className="text-xs bg-muted p-3 rounded max-h-64 overflow-y-auto">
                {JSON.stringify(fusionResult.agreement, null, 2)}
              </pre>
            </div>

            {/* Conflicts */}
            {fusionResult.conflicts.length > 0 && (
              <div>
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-600" />
                  Conflicts Detected ({fusionResult.conflicts.length})
                </h4>
                <div className="space-y-2">
                  {fusionResult.conflicts.map((conflict, idx) => (
                    <div
                      key={idx}
                      className="border border-yellow-200 dark:border-yellow-800 rounded-lg p-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="font-medium text-sm">{conflict.field_path}</p>
                          {conflict.resolution && (
                            <p className="text-xs text-muted-foreground mt-1">
                              Resolution: {conflict.resolution}
                            </p>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleConflictExpansion(conflict.field_path)}
                        >
                          {expandedConflicts.has(conflict.field_path) ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </Button>
                      </div>

                      {expandedConflicts.has(conflict.field_path) && (
                        <div className="mt-2 space-y-1">
                          {conflict.values.map((val, valIdx) => (
                            <div
                              key={valIdx}
                              className="text-xs bg-muted p-2 rounded flex items-center justify-between"
                            >
                              <span className="font-mono">{val.value}</span>
                              <span className="text-muted-foreground">
                                ({val.source.source_type}, confidence: {val.source.confidence})
                              </span>
                            </div>
                          ))}
                          {conflict.resolved_value && (
                            <div className="text-xs bg-green-50 dark:bg-green-900/20 p-2 rounded mt-2">
                              <span className="font-medium">Resolved:</span>{' '}
                              <span className="font-mono">{conflict.resolved_value}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Source Tracking */}
            {Object.keys(fusionResult.source_tracking).length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Source Tracking</h4>
                <div className="text-xs space-y-1">
                  {Object.entries(fusionResult.source_tracking).map(([field, source]) => (
                    <div key={field} className="flex items-center justify-between p-2 bg-muted rounded">
                      <span className="font-mono">{field}</span>
                      <span className="text-muted-foreground">
                        {source.source_type} (confidence: {source.confidence})
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}















