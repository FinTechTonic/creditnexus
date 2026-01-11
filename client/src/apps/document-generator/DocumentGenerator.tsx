/**
 * Document Generator - Main component for LMA template generation.
 * 
 * Allows users to:
 * - Select an LMA template
 * - Input or import CDM data
 * - Generate documents from templates
 * - Preview and export generated documents
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth, useAuth } from '../../context/AuthContext';
import { useFDC3 } from '../../context/FDC3Context';
import type { GeneratedDocumentContext, CreditAgreementData as FDC3CreditAgreementData } from '../../context/FDC3Context';
import { Loader2, FileText, Sparkles, AlertCircle, CheckCircle2, Merge, Info } from 'lucide-react';
import { ChatbotPanel } from './ChatbotPanel';
import { ProcessingStatus } from './ProcessingStatus';
import { DocumentCdmSelector } from './DocumentCdmSelector';
import { FloatingChatbotButton } from './FloatingChatbotButton';
import { CdmDataPreview } from './CdmDataPreview';
import { CdmFieldEditor } from '../../components/CdmFieldEditor';
import { FieldEditorModal } from './FieldEditorModal';
import { TemplateGrid } from './TemplateGrid';
import { UnifiedSelectionGrid } from './UnifiedSelectionGrid';
import { PreGenerationStats } from './PreGenerationStats';
import { FieldFillingPanel } from './FieldFillingPanel';
import { Dialog, DialogContent } from '../../components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { Button } from '../../components/ui/button';

// Types
interface LMATemplate {
  id: number;
  template_code: string;
  name: string;
  category: string;
  subcategory?: string;
  governing_law?: string;
  version: string;
  required_fields?: string[];
  optional_fields?: string[];
  ai_generated_sections?: string[];
}

interface GeneratedDocument {
  id: number;
  template_id: number;
  file_path: string;
  status: string;
  generation_summary?: {
    total_fields: number;
    mapped_fields_count: number;
    ai_fields_count: number;
    missing_required_fields: string[];
  };
  created_at: string;
}

// Use CreditAgreementData from FDC3Context for consistency
type CreditAgreementData = FDC3CreditAgreementData;

interface DocumentGeneratorProps {
  initialCdmData?: CreditAgreementData;
  onDocumentGenerated?: (document: GeneratedDocument) => void;
}

export function DocumentGenerator({ initialCdmData, onDocumentGenerated }: DocumentGeneratorProps) {
  const { broadcast } = useFDC3();
  const { isAuthenticated } = useAuth();
  
  // State
  const [templates, setTemplates] = useState<LMATemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<LMATemplate | null>(null);
  const [cdmData, setCdmData] = useState<CreditAgreementData>(initialCdmData || {});
  const [generatedDocument, setGeneratedDocument] = useState<GeneratedDocument | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [showPreview, setShowPreview] = useState(false);
  const [inputMode, setInputMode] = useState<'library' | 'manual'>('library');
  const [sourceDocumentId, setSourceDocumentId] = useState<number | null>(null);
  const [selectedDocumentTitle, setSelectedDocumentTitle] = useState<string | null>(null);
  const [isChatbotOpen, setIsChatbotOpen] = useState(false);
  const [previewCdmData, setPreviewCdmData] = useState<CreditAgreementData | null>(null);
  const [previewDocumentTitle, setPreviewDocumentTitle] = useState<string | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isFieldEditorOpen, setIsFieldEditorOpen] = useState(false);
  const [fieldOverrides, setFieldOverrides] = useState<Record<string, any>>({});
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [availableDocuments, setAvailableDocuments] = useState<any[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);

  // Load templates and documents on mount
  useEffect(() => {
    loadTemplates();
    loadDocuments();
  }, []);

  const loadDocuments = useCallback(async () => {
    try {
      setLoadingDocuments(true);
      const response = await fetchWithAuth('/api/documents?limit=50&offset=0');
      if (response.ok) {
        const data = await response.json();
        const docs = data.documents || [];
        
        // Filter and enrich documents with CDM data
        const docsWithCdm = await Promise.all(
          docs.map(async (doc: any) => {
            try {
              const cdmResponse = await fetchWithAuth(`/api/documents/${doc.id}?include_cdm_data=true`);
              if (cdmResponse.ok) {
                const responseData = await cdmResponse.json();
                // Include document even if CDM data is missing (show with 0 completeness)
                let cdmData = responseData.cdm_data;
                let completenessScore = 0;
                
                if (cdmData) {
                  // Calculate completeness score
                  let score = 0;
                  let maxScore = 0;
                  if (cdmData.parties && Array.isArray(cdmData.parties) && cdmData.parties.length > 0) {
                    score += 30;
                    maxScore += 30;
                  }
                  if (cdmData.facilities && Array.isArray(cdmData.facilities) && cdmData.facilities.length > 0) {
                    score += 30;
                    maxScore += 30;
                  }
                  if (cdmData.agreement_date) {
                    score += 10;
                    maxScore += 10;
                  }
                  if (cdmData.governing_law) {
                    score += 10;
                    maxScore += 10;
                  }
                  if (cdmData.deal_id) {
                    score += 10;
                    maxScore += 10;
                  }
                  if (cdmData.loan_identification_number) {
                    score += 10;
                    maxScore += 10;
                  }
                  completenessScore = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;
                }
                
                return {
                  ...doc,
                  cdmData: cdmData || null,
                  completenessScore,
                };
              }
              // If CDM fetch failed, still include document but mark as no CDM
              return {
                ...doc,
                cdmData: null,
                completenessScore: 0,
              };
            } catch (err) {
              return null;
            }
          })
        );
        
        const filteredDocs = docsWithCdm.filter((doc: any) => doc !== null);
        setAvailableDocuments(filteredDocs);
      }
    } catch (err) {
      console.error('Error loading documents:', err);
    } finally {
      setLoadingDocuments(false);
    }
  }, []);

  // Update CDM data if initial data changes
  useEffect(() => {
    if (initialCdmData) {
      setCdmData(initialCdmData);
    }
  }, [initialCdmData]);

  // Handle CDM data selection from library
  const handleCdmDataSelect = useCallback((
    cdmData: CreditAgreementData,
    documentId: number
  ) => {
    // Ensure parties have 'id' field
    if (cdmData.parties) {
      cdmData.parties = cdmData.parties.map((party, idx) => ({
        ...party,
        id: party.id || `party_${idx}`,
      }));
    }
    setCdmData(cdmData);
    setSourceDocumentId(documentId);
    setError(null);
    
    // Fetch document title for display
    fetchWithAuth(`/api/documents/${documentId}`)
      .then(res => res.json())
      .then(data => {
        if (data.document) {
          setSelectedDocumentTitle(data.document.title);
        }
      })
      .catch(() => {
        // Ignore errors fetching title
      });
  }, []);

  // Handle CDM data update from chatbot
  const handleCdmDataUpdate = useCallback((updatedCdmData: Record<string, unknown>) => {
    // Ensure parties have 'id' field if missing
    const updated = updatedCdmData as CreditAgreementData;
    if (updated.parties) {
      updated.parties = updated.parties.map((party, idx) => ({
        ...party,
        id: party.id || `party_${idx}`,
      }));
    }
    setCdmData(updated);
    setError(null);
  }, []);

  const loadTemplates = useCallback(async () => {
    try {
      setLoadingTemplates(true);
      setError(null);
      const response = await fetchWithAuth('/api/templates');
      if (response.ok) {
        const data = await response.json();
        setTemplates(data.templates || []);
      } else {
        throw new Error('Failed to load templates');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setLoadingTemplates(false);
    }
  }, []);

  const handleTemplateSelect = useCallback(async (templateId: number) => {
    try {
      setError(null);
      const response = await fetchWithAuth(`/api/templates/${templateId}`);
      if (response.ok) {
        const template = await response.json();
        setSelectedTemplate(template);
        setGeneratedDocument(null);
        setShowPreview(false);
        
        // Load template requirements
        const reqResponse = await fetchWithAuth(`/api/templates/${templateId}/requirements`);
        if (reqResponse.ok) {
          const requirements = await reqResponse.json();
          // Could use this to validate or highlight required fields
        }
      } else {
        throw new Error('Failed to load template details');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select template');
    }
  }, []);

  // Handle template selection from chatbot
  const handleChatbotTemplateSelect = useCallback((templateId: number) => {
    handleTemplateSelect(templateId);
  }, [handleTemplateSelect]);

  // Check if CDM data is valid for generation
  const hasValidCdmData = useCallback(() => {
    if (!cdmData || Object.keys(cdmData).length === 0) {
      return false;
    }
    // Check for at least one party and one facility
    const hasParties = cdmData.parties && Array.isArray(cdmData.parties) && cdmData.parties.length > 0;
    const hasFacilities = cdmData.facilities && Array.isArray(cdmData.facilities) && cdmData.facilities.length > 0;
    return hasParties && hasFacilities;
  }, [cdmData]);

  const handleGenerate = async () => {
    if (!selectedTemplate) {
      setError('Please select a template first');
      return;
    }

    // Check authentication before generating
    if (!isAuthenticated) {
      setError('You must be logged in to generate documents. Please log in and try again.');
      return;
    }

    // Proceed with generation (missing fields are shown in PreGenerationStats)
    await performGeneration();
  };

  const performGeneration = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // When sourceDocumentId is provided, use document_id to load CDM from library
      // Otherwise, send cdm_data directly
      const requestBody: {
        template_id: number;
        cdm_data?: CreditAgreementData;
        document_id?: number;
        source_document_id?: number;
        field_overrides?: Record<string, any>;
      } = {
        template_id: selectedTemplate.id,
      };
      
      // Add field overrides if any
      if (Object.keys(fieldOverrides).length > 0) {
        requestBody.field_overrides = fieldOverrides;
      }

      // Determine which CDM source to use
      // Priority: library document (if sourceDocumentId is set and inputMode is library)
      // Otherwise: use manual CDM data
      if (sourceDocumentId && inputMode === 'library') {
        // Load CDM data from library document
        requestBody.document_id = sourceDocumentId;
        requestBody.source_document_id = sourceDocumentId;
      } else if (Object.keys(cdmData).length > 0) {
        // Use manually entered CDM data
        requestBody.cdm_data = cdmData;
      } else {
        throw new Error('No CDM data provided. Please select a document from the library or enter CDM data manually.');
      }

      const response = await fetchWithAuth('/api/templates/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (response.status === 401) {
        // Handle authentication error
        const errorData = await response.json().catch(() => ({}));
        setError('Authentication required. Please log in and try again.');
        return;
      }

      if (response.ok) {
        const doc = await response.json();
        setGeneratedDocument(doc);
        setShowPreview(true);
        
        // Broadcast FDC3 context for generated document
        if (selectedTemplate) {
          const context: GeneratedDocumentContext = {
            type: 'finos.creditnexus.generatedDocument',
            id: {
              documentId: doc.document_id || `doc_${doc.id}`,
              templateId: selectedTemplate.id,
            },
            template: {
              id: selectedTemplate.id,
              code: selectedTemplate.template_code,
              name: selectedTemplate.name,
              category: selectedTemplate.category,
            },
            sourceCdmData: cdmData,
            generatedAt: new Date().toISOString(),
            filePath: doc.generated_file_path || doc.file_path,
            status: doc.status || 'generated',
          };
          
          try {
            // Cast to CreditNexusContext for broadcast (GeneratedDocumentContext extends Context)
            // Note: GeneratedDocumentContext should be added to CreditNexusContext union type
            await broadcast(context as any);
          } catch (err) {
            // Don't fail the generation if broadcast fails
          }
        }
        
        if (onDocumentGenerated) {
          onDocumentGenerated(doc);
        }
      } else if (response.status === 401) {
        // Handle authentication error specifically
        const errorData = await response.json().catch(() => ({}));
        setError('Authentication required. Please log in to generate documents.');
      } else {
        // Handle other error responses
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail?.message || errorData.detail || errorData.message || 'Document generation failed';
        setError(errorMessage);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Document generation failed';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleFieldEditorSave = (overrides: Record<string, any>) => {
    try {
      // Merge field overrides into existing field_overrides state
      setFieldOverrides(prev => ({ ...prev, ...overrides }));
      
      // CRITICAL: Also merge overrides into cdmData so the UI reflects the changes
      // This ensures validators see the updated data and the CDM object is editable
      setCdmData(prev => {
        const updated = { ...prev };
        for (const [path, value] of Object.entries(overrides)) {
          // Apply each override to the CDM data using nested path
          applyNestedValue(updated, path, value);
        }
        return updated;
      });
      
      setIsFieldEditorOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save field overrides');
    }
    // Don't trigger generation automatically - let user click Generate button
    // The field overrides will be applied during generation
  };
  
  // Helper function to apply a nested path value to an object
  const applyNestedValue = (obj: any, path: string, value: any): void => {
    const parts = path.split('.');
    let current = obj;
    
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      
      // Handle array access like parties[0]
      if (part.includes('[')) {
        const [key, indexStr] = part.split('[');
        const indexMatch = indexStr.match(/^(\d+)\]$/);
        
        if (!current[key]) {
          current[key] = [];
        }
        
        if (indexMatch) {
          const index = parseInt(indexMatch[1], 10);
          if (!current[key][index]) {
            current[key][index] = {};
          }
          current = current[key][index];
        }
      } else {
        if (!current[part]) {
          current[part] = {};
        }
        current = current[part];
      }
    }
    
    const lastPart = parts[parts.length - 1];
    if (lastPart.includes('[')) {
      const [key, indexStr] = lastPart.split('[');
      const indexMatch = indexStr.match(/^(\d+)\]$/);
      if (indexMatch) {
        const index = parseInt(indexMatch[1], 10);
        if (!current[key]) {
          current[key] = [];
        }
        current[key][index] = value;
      }
    } else {
      current[lastPart] = value;
    }
  };

  const handleExport = async (format: 'word' | 'pdf') => {
    if (!generatedDocument) return;

    try {
      const response = await fetchWithAuth(`/api/generated-documents/${generatedDocument.id}/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ format }),
      });

      if (response.ok) {
        // Download file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `generated_document.${format === 'pdf' ? 'pdf' : 'docx'}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        throw new Error('Export failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <Sparkles className="w-6 h-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">LMA Document Generator</h1>
            </div>
            <p className="text-sm text-gray-600 mt-1">
              Generate LMA-compliant documents from templates using CDM data
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative group">
              <Button
                variant="outline"
                size="sm"
                className="text-gray-600 hover:text-gray-900"
                title="Workflow guidance"
              >
                <Info className="w-4 h-4" />
              </Button>
              <div className="absolute right-0 top-full mt-2 w-80 p-4 bg-white border border-gray-200 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                <h4 className="font-semibold text-gray-900 mb-2">Workflow Guide</h4>
                <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
                  <li>Select a template from the sidebar</li>
                  <li>Choose CDM data from your library or enter manually</li>
                  <li>Review the data summary and completeness</li>
                  <li>Click "Generate Document" to create your document</li>
                  <li>Preview and export the generated document</li>
                </ol>
                <p className="text-xs text-gray-500 mt-3">
                  💡 Tip: Use the floating chatbot button for AI assistance with template selection and field filling.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Unified Selection Grid - CDM Documents (Row 1) and Templates (Row 2) */}
        {/* Only show when both are not selected, or allow changing selection */}
        {(!selectedTemplate || !sourceDocumentId) && (
          <div className="flex-1 overflow-y-auto bg-slate-900 p-6">
            {loadingTemplates || loadingDocuments ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
              </div>
            ) : (
              <UnifiedSelectionGrid
                documents={availableDocuments}
                selectedDocumentId={sourceDocumentId}
                onDocumentSelect={(documentId) => {
                  const doc = availableDocuments.find(d => d.id === documentId);
                  if (doc) {
                    if (doc.cdmData) {
                      handleCdmDataSelect(doc.cdmData, documentId);
                    } else {
                      // Document has no CDM data - show warning but allow selection
                      setError('This document has no CDM data. Please extract data first or select another document.');
                      // Still set the document ID so user can see it's selected
                      setSourceDocumentId(documentId);
                    }
                  }
                }}
                templates={templates}
                selectedTemplateId={selectedTemplate?.id || null}
                onTemplateSelect={handleTemplateSelect}
              />
            )}
          </div>
        )}

        {/* Main Content Area - Document Generation Interface */}
        <div className="flex-1 flex flex-col overflow-hidden border-t border-slate-700 bg-slate-900">
          {error && (
            <div className="bg-red-900/30 border-l-4 border-red-500 p-4 m-4">
              <div className="flex items-center">
                <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
                <p className="text-sm text-red-300">{error}</p>
              </div>
            </div>
          )}

          {!selectedTemplate || !sourceDocumentId ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FileText className="w-16 h-16 mx-auto mb-4 text-slate-400" />
                <h3 className="text-lg font-medium text-slate-100 mb-2">
                  {!sourceDocumentId && !selectedTemplate 
                    ? 'Select a CDM Document and Template'
                    : !sourceDocumentId
                    ? 'Select a CDM Document from Row 1'
                    : 'Select a Template from Row 2'}
                </h3>
                <p className="text-sm text-slate-400">
                  {!sourceDocumentId && !selectedTemplate
                    ? 'Choose a CDM document from the first row and a template from the second row to begin generation'
                    : !sourceDocumentId
                    ? 'Choose a CDM document from the first row above'
                    : 'Choose an LMA template from the second row above'}
                </p>
              </div>
            </div>
          ) : showPreview && generatedDocument ? (
            <div className="flex-1 flex flex-col p-6">
              <div className="bg-emerald-900/30 border border-emerald-700 rounded-lg p-4 mb-4">
                <div className="flex items-center">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 mr-2" />
                  <span className="text-sm font-medium text-emerald-300">
                    Document generated successfully!
                  </span>
                </div>
                {generatedDocument.generation_summary && (
                  <div className="mt-2 text-xs text-emerald-400">
                    {generatedDocument.generation_summary.mapped_fields_count} mapped fields,{' '}
                    {generatedDocument.generation_summary.ai_fields_count} AI-generated sections
                  </div>
                )}
              </div>

              <div className="flex-1 bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-100">Document Preview</h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleExport('word')}
                      className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 text-sm font-medium"
                    >
                      Export Word
                    </button>
                    <button
                      onClick={() => setShowPreview(false)}
                      className="px-4 py-2 bg-slate-700 text-slate-200 rounded-lg hover:bg-slate-600 text-sm font-medium"
                    >
                      Edit
                    </button>
                  </div>
                </div>
                <div className="border border-slate-700 rounded p-4 bg-slate-900/50">
                  <p className="text-sm text-slate-300">
                    Document preview will be available here. File saved at:{' '}
                    <code className="text-xs bg-slate-800 px-2 py-1 rounded text-slate-200">
                      {generatedDocument.file_path}
                    </code>
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col p-6 overflow-y-auto">
              {/* Main Content */}
              <div className="flex-1 flex flex-col max-w-7xl mx-auto w-full space-y-6">
                {/* Template Info */}
                <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
                  <h2 className="text-lg font-semibold text-slate-100 mb-4">
                    Template: {selectedTemplate.name}
                  </h2>
                  <div className="text-sm text-slate-300 space-y-1">
                    <p><span className="font-medium">Category:</span> {selectedTemplate.category}</p>
                    {selectedTemplate.subcategory && (
                      <p><span className="font-medium">Subcategory:</span> {selectedTemplate.subcategory}</p>
                    )}
                    {selectedTemplate.governing_law && (
                      <p><span className="font-medium">Governing Law:</span> {selectedTemplate.governing_law}</p>
                    )}
                    <p><span className="font-medium">Version:</span> {selectedTemplate.version}</p>
                  </div>
                </div>

                {/* Pre-Generation Statistics */}
                <PreGenerationStats
                  templateId={selectedTemplate.id}
                  documentId={sourceDocumentId}
                  cdmData={cdmData}
                  fieldOverrides={fieldOverrides}
                  onMissingFieldsDetected={(missing) => {
                    setMissingFields(missing);
                  }}
                />

                {/* Field Filling Panel - Show if there are missing fields */}
                {missingFields.length > 0 && (
                  <FieldFillingPanel
                    templateId={selectedTemplate.id}
                    documentId={sourceDocumentId}
                    cdmData={cdmData}
                    missingFields={missingFields}
                    onFieldsFilled={(newOverrides) => {
                      setFieldOverrides(prev => ({ ...prev, ...newOverrides }));
                      // Also update cdmData so the UI reflects the changes
                      setCdmData(prev => {
                        const updated = { ...prev };
                        for (const [path, value] of Object.entries(newOverrides)) {
                          applyNestedValue(updated, path, value);
                        }
                        return updated;
                      });
                      setMissingFields([]); // Clear missing fields after filling
                    }}
                  />
                )}

                {/* CDM Data Summary */}
                {Object.keys(cdmData).length > 0 && (
                  <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
                    <h3 className="text-md font-semibold text-slate-100 mb-4">CDM Data Summary</h3>
                    <div className="p-3 bg-emerald-900/30 border border-emerald-700 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span className="text-sm font-medium text-emerald-300">CDM Data Ready</span>
                      </div>
                      {selectedDocumentTitle && (
                        <div className="text-xs text-emerald-200 mb-2 font-medium">
                          Source: {selectedDocumentTitle}
                        </div>
                      )}
                      <div className="text-xs text-emerald-300 space-y-1">
                        {cdmData.parties && (
                          <p>• {cdmData.parties.length} party(ies)</p>
                        )}
                        {cdmData.facilities && (
                          <p>• {cdmData.facilities.length} facility(ies)</p>
                        )}
                        {cdmData.agreement_date && (
                          <p>• Agreement Date: {cdmData.agreement_date}</p>
                        )}
                        {cdmData.governing_law && (
                          <p>• Governing Law: {cdmData.governing_law}</p>
                        )}
                      </div>
                      <div className="mt-4">
                        <button
                          onClick={() => setIsFieldEditorOpen(true)}
                          className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 text-sm font-medium"
                        >
                          Edit Fields
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Generate Button */}
                <div className="flex justify-end gap-3">
                <button
                  onClick={() => setSelectedTemplate(null)}
                  className="px-4 py-2 bg-slate-700 text-slate-200 rounded-lg hover:bg-slate-600 font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleGenerate}
                  disabled={loading || !cdmData || !hasValidCdmData() || !isAuthenticated}
                  className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  title={
                    !isAuthenticated
                      ? 'Please log in to generate documents'
                      : !cdmData
                      ? 'Please provide CDM data'
                      : !hasValidCdmData()
                      ? 'CDM data is incomplete. Please ensure parties and facilities are provided.'
                      : 'Generate document'
                  }
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Generate Document
                    </>
                  )}
                </button>
                </div>
              </div>

            </div>
          )}
        </div>
      </div>

      {/* Floating Chatbot Button */}
      <FloatingChatbotButton
        isOpen={isChatbotOpen}
        onClick={() => setIsChatbotOpen(!isChatbotOpen)}
      />

      {/* Chatbot Modal */}
      <Dialog open={isChatbotOpen} onOpenChange={setIsChatbotOpen}>
        <DialogContent className="max-w-4xl max-h-[85vh] p-0 overflow-hidden bg-slate-800 border-slate-700">
          <div className="h-[85vh]">
            <ChatbotPanel
              cdmData={cdmData as Record<string, unknown>}
              onCdmDataUpdate={handleCdmDataUpdate}
              onTemplateSelect={handleChatbotTemplateSelect}
              onClose={() => setIsChatbotOpen(false)}
              className="h-full"
              dealId={cdmData?.deal_id ? Number(cdmData.deal_id) : null}
            />
          </div>
        </DialogContent>
      </Dialog>

      {/* CDM Data Preview Modal */}
      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto bg-slate-800 border-slate-700">
          {previewCdmData && (
            <CdmDataPreview
              cdmData={previewCdmData}
              documentTitle={previewDocumentTitle || undefined}
              onClose={() => setIsPreviewOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Field Editor Modal - showAllFields=true to allow editing existing CDM fields */}
      <FieldEditorModal
        isOpen={isFieldEditorOpen}
        onClose={() => setIsFieldEditorOpen(false)}
        onSave={handleFieldEditorSave}
        templateId={selectedTemplate?.id || null}
        cdmData={cdmData}
        missingFields={missingFields}
        showAllFields={true}
      />
    </div>
  );
}

