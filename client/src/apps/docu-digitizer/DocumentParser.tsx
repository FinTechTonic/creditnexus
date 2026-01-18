import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/components/ui/toast';
import { Upload, FileText, Send, Check, X, Loader2, Edit2, Save, BookOpen, Sparkles, Mic, Image as ImageIcon, Search, Type, Calculator } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useFDC3 } from '@/context/FDC3Context';
import { useAuth, fetchWithAuth } from '@/context/AuthContext';
import type { CreditAgreementData, CreditNexusLoanContext } from '@/context/FDC3Context';
import { MultimodalInputTabs } from './MultimodalInputTabs';
import type { TranscriptionResult, ExtractionResult, DocumentResult } from './MultimodalInputTabs';
import { ClauseEditor } from '@/components/ClauseEditor';
import { CdmAccordionEditor } from '@/components/CdmAccordionEditor';
import { DigitizerChatbot } from './DigitizerChatbot';
import { AccountingDocumentDisplay } from './AccountingDocumentDisplay';

interface DocumentParserProps {
  onBroadcast?: () => void;
  onSaveToLibrary?: () => void;
  onGenerateFromTemplate?: (data: CreditAgreementData) => void;
  initialData?: CreditAgreementData | null;
  initialContent?: string | null;
}

export function DocumentParser({
  onBroadcast,
  onSaveToLibrary,
  onGenerateFromTemplate,
  initialData,
  initialContent
}: DocumentParserProps) {
  const { broadcast } = useFDC3();
  const { isAuthenticated } = useAuth();
  const { addToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [documentText, setDocumentText] = useState(initialContent || '');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [extractedData, setExtractedData] = useState<CreditAgreementData | null>(initialData || null);
  const [editableData, setEditableData] = useState<CreditAgreementData | null>(initialData || null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warningMessage, setWarningMessage] = useState<string | null>(null);
  const [broadcastSuccess, setBroadcastSuccess] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [sourceFilename, setSourceFilename] = useState<string | null>(null);
  const [isLoadingDocument, setIsLoadingDocument] = useState(false);
  
  // Tab state management
  const [activeTab, setActiveTab] = useState<string>('summary');
  const [_tabHistory, setTabHistory] = useState<string[]>(['summary']); // Prefix with _ - setter is used
  
  // Clause editor state
  const [_showClauseEditor, setShowClauseEditor] = useState(false); // Prefix with _ - setter is used
  // const [selectedClauses, setSelectedClauses] = useState<any[]>([]); // Unused - kept for future use
  const [clauseEditorDocumentId, setClauseEditorDocumentId] = useState<number | null>(null);
  
  // Multimodal sources state
  const [multimodalSources, setMultimodalSources] = useState<{
    audio?: { text?: string; cdm?: Record<string, unknown> };
    image?: { text?: string; cdm?: Record<string, unknown> };
    document?: { cdm?: Record<string, unknown>; documentId?: number };
    text?: { text: string; cdm?: Record<string, unknown> };
  }>({});

  // Chatbot state
  const [isChatbotOpen, setIsChatbotOpen] = useState(false);
  const [documentId, setDocumentId] = useState<number | null>(null);

  // Document type state (credit agreement vs accounting document)
  const [documentType, setDocumentType] = useState<'credit_agreement' | 'accounting'>('credit_agreement');
  const [accountingDocumentType, setAccountingDocumentType] = useState<string>('balance_sheet'); // balance_sheet, income_statement, cash_flow_statement, tax_return

  const isPdfFile = (file: File) => {
    return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setExtractedData(null);
    setEditableData(null);
    setError(null);
    setBroadcastSuccess(false);
    setSaveSuccess(false);
    setSourceFilename(file.name);

    if (isPdfFile(file)) {
      setUploadedFile(file);
      setDocumentText(`[PDF File: ${file.name}]`);
    } else {
      const text = await file.text();
      setDocumentText(text);
      setUploadedFile(null);
    }
  };

  const handleExtract = async () => {
    // Check if we have multimodal sources
    const hasMultimodalSources = Object.keys(multimodalSources).length > 0;
    const hasFileOrText = documentText.trim() || uploadedFile;
    
    if (!hasFileOrText && !hasMultimodalSources) return;

    setIsExtracting(true);
    setError(null);
    setWarningMessage(null);
    setBroadcastSuccess(false);

    try {
      let response: Response;

      // If we have multimodal sources, use fusion API
      if (hasMultimodalSources) {
        const fusionRequest: Record<string, unknown> = {
          use_llm_fusion: true,
        };

        // Add CDM data and text from each source
        if (multimodalSources.audio) {
          if (multimodalSources.audio.cdm) {
            fusionRequest.audio_cdm = multimodalSources.audio.cdm;
          }
          if (multimodalSources.audio.text) {
            fusionRequest.audio_text = multimodalSources.audio.text;
          }
        }
        if (multimodalSources.image) {
          if (multimodalSources.image.cdm) {
            fusionRequest.image_cdm = multimodalSources.image.cdm;
          }
          if (multimodalSources.image.text) {
            fusionRequest.image_text = multimodalSources.image.text;
          }
        }
        if (multimodalSources.document) {
          if (multimodalSources.document.cdm) {
            fusionRequest.document_cdm = multimodalSources.document.cdm;
          }
        }
        if (multimodalSources.text) {
          if (multimodalSources.text.cdm) {
            fusionRequest.text_cdm = multimodalSources.text.cdm;
          }
          if (multimodalSources.text.text) {
            fusionRequest.text_input = multimodalSources.text.text;
          }
        }

        // Also include file/text if available
        if (uploadedFile) {
          // For file uploads with multimodal, we'd need to extract first
          // For now, prioritize multimodal sources
        } else if (documentText.trim()) {
          fusionRequest.text_input = documentText;
        }

        response = await fetchWithAuth('/api/multimodal/fuse', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(fusionRequest),
        });
      } else if (uploadedFile) {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        response = await fetchWithAuth('/api/upload', {
          method: 'POST',
          body: formData,
        });
      } else {
        // Use accounting endpoint if accounting document type is selected
        if (documentType === 'accounting') {
          if (uploadedFile) {
            const formData = new FormData();
            formData.append('file', uploadedFile);
            formData.append('document_type', accountingDocumentType);
            response = await fetchWithAuth('/api/extract/accounting', {
              method: 'POST',
              body: formData,
            });
          } else {
            response = await fetchWithAuth('/api/extract/accounting', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                text: documentText,
                document_type: accountingDocumentType
              }),
            });
          }
        } else {
          response = await fetchWithAuth('/api/extract', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: documentText }),
          });
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = errorData.detail;
        if (typeof detail === 'object' && detail.message) {
          setError(detail.message);
        } else if (typeof detail === 'string') {
          setError(detail);
        } else {
          setError(`Extraction failed with status ${response.status}`);
        }
        return;
      }

      const result = await response.json();

      // Handle accounting document response format
      if (documentType === 'accounting') {
        if (result.status === 'error' || result.extraction_status === 'irrelevant_document') {
          setError(result.message || result.detail?.message || 'This document does not appear to be an accounting document.');
          return;
        }

        if (result.agreement) {
          if (result.extracted_text && uploadedFile) {
            setDocumentText(result.extracted_text);
            setUploadedFile(null);
          }
          const data = {
            ...result.agreement,
            extraction_status: result.extraction_status || result.status || 'success',
            document_type: accountingDocumentType,
            is_accounting_document: true,
          };
          setExtractedData(data as any);
          setEditableData(data as any);
          
          // Extract document ID if available
          if (result.document_id) {
            setDocumentId(result.document_id);
          }
          
          // Clear multimodal sources after successful extraction
          setMultimodalSources({});
          
          if (result.extraction_status === 'partial_data_missing' && result.message) {
            setWarningMessage(result.message);
            addToast('Accounting document extracted with some missing data', 'warning');
          } else {
            addToast('Accounting document extracted successfully', 'success');
          }
        } else {
          setError('No accounting data could be extracted from this document.');
          addToast('No accounting data could be extracted', 'error');
        }
        return;
      }

      // Handle credit agreement response format (existing logic)
      if (result.status === 'irrelevant_document' || result.status === 'error') {
        setError(result.message || 'This document does not appear to be a credit agreement.');
        return;
      }

      if (result.agreement) {
        if (result.extracted_text && uploadedFile) {
          setDocumentText(result.extracted_text);
          setUploadedFile(null);
        }
        const data = {
          ...result.agreement,
          extraction_status: result.status || 'success',
          is_accounting_document: false,
        };
        setExtractedData(data);
        setEditableData(data);
        
        // Extract document ID if available
        if (result.document_id) {
          setDocumentId(result.document_id);
        }
        
        // Clear multimodal sources after successful extraction
        const hadMultimodalSources = Object.keys(multimodalSources).length > 0;
        setMultimodalSources({});
        
        if (hadMultimodalSources) {
          if (result.conflicts_count > 0) {
            addToast(`Data fused successfully with ${result.conflicts_count} conflict(s) resolved`, 'success');
          } else {
            addToast('Data fused and extracted successfully', 'success');
          }
        } else if (result.status === 'partial_data_missing' && result.message) {
          setWarningMessage(result.message);
          addToast('Document extracted with some missing data', 'warning');
        } else {
          addToast('Document extracted successfully', 'success');
        }
      } else {
        setError('No data could be extracted from this document.');
        addToast('No data could be extracted', 'error');
      }
    } catch (err) {
      console.error('Extraction error:', err);
      setError('Failed to connect to extraction service. Please try again.');
      addToast('Failed to extract document', 'error');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleBroadcast = () => {
    if (!editableData) return;

    const context: CreditNexusLoanContext = {
      type: 'finos.creditnexus.loan',
      id: {
        LIN: editableData.loan_identification_number,
        DealID: editableData.deal_id,
      },
      loan: {
        ...editableData,
        document_text: documentText
      },
    };

    broadcast(context);
    setBroadcastSuccess(true);
    addToast('Data broadcast to connected apps', 'success');

    if (onBroadcast) {
      onBroadcast();
    }

    setTimeout(() => setBroadcastSuccess(false), 3000);
  };

  const handleFieldChange = (field: keyof CreditAgreementData, value: unknown) => {
    if (!editableData) return;
    setEditableData({ ...editableData, [field]: value });
  };

  const handleSaveToLibrary = async () => {
    if (!editableData || !isAuthenticated) return;

    setIsSaving(true);
    setError(null);

    try {
      const borrower = editableData.parties?.find(p => p.role.toLowerCase().includes('borrower'));
      const title = borrower?.name
        ? `${borrower.name} Credit Agreement`
        : `Credit Agreement - ${editableData.agreement_date || 'Untitled'}`;

      const response = await fetchWithAuth('/api/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          agreement_data: editableData,
          original_text: documentText || null,
          source_filename: sourceFilename,
          extraction_method: 'simple',
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        const errorMessage = typeof data.detail === 'string'
          ? data.detail
          : data.detail?.message || 'Failed to save document';
        throw new Error(errorMessage);
      }

      const data = await response.json();
      if (data.document?.id) {
        setClauseEditorDocumentId(data.document.id);
        setDocumentId(data.document.id);
        setShowClauseEditor(true);
      }

      setSaveSuccess(true);
      addToast('Document saved to library', 'success');
      if (onSaveToLibrary) {
        onSaveToLibrary();
      }
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Error saving document:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to save document';
      setError(errorMessage);
      addToast(errorMessage, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setDocumentText('');
    setUploadedFile(null);
    setExtractedData(null);
    setEditableData(null);
    setError(null);
    setWarningMessage(null);
    setBroadcastSuccess(false);
    setSaveSuccess(false);
    setIsEditing(false);
    setSourceFilename(null);
    setMultimodalSources({});
  };

  const handleAudioComplete = (result: TranscriptionResult) => {
    setMultimodalSources(prev => ({
      ...prev,
      audio: {
        text: result.transcription,
        cdm: result.agreement as Record<string, unknown> | undefined
      }
    }));
    
    if (result.agreement) {
      const agreementData = result.agreement as CreditAgreementData;
      setExtractedData(agreementData);
      setEditableData(agreementData);
    }
  };

  const handleImageComplete = (result: ExtractionResult) => {
    setMultimodalSources(prev => ({
      ...prev,
      image: {
        text: result.ocr_text,
        cdm: result.agreement as Record<string, unknown> | undefined
      }
    }));
    
    if (result.agreement) {
      const agreementData = result.agreement as CreditAgreementData;
      setExtractedData(agreementData);
      setEditableData(agreementData);
    }
  };

  const handleDocumentSelect = (document: DocumentResult) => {
    setMultimodalSources(prev => ({
      ...prev,
      document: {
        documentId: document.document_id,
        cdm: document.cdm_data as Record<string, unknown> | undefined
      }
    }));
    
    if (document.cdm_data) {
      const agreementData = document.cdm_data as CreditAgreementData;
      setExtractedData(agreementData);
      setEditableData(agreementData);
    }
  };

  const handleTextInput = (text: string, cdmData?: Record<string, unknown>) => {
    setMultimodalSources(prev => ({
      ...prev,
      text: {
        text,
        cdm: cdmData
      }
    }));
    
    setDocumentText(text);
    
    if (cdmData) {
      const agreementData = cdmData as CreditAgreementData;
      setExtractedData(agreementData);
      setEditableData(agreementData);
    }
  };

  // Track which document ID was last loaded to prevent reloading the same document
  // Use ref to persist across component re-mounts
  const loadedDocumentIdRef = useRef<string | null>(null);
  // const [loadedDocumentId, setLoadedDocumentId] = useState<string | null>(null); // Unused - using ref instead
  const isLoadingDocumentRef = useRef(false);

  // Sync tab state from URL
  useEffect(() => {
    const tab = searchParams.get('tab') || 'summary';
    if (tab !== activeTab) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  // Load document from URL query param
  useEffect(() => {
    const documentId = searchParams.get('documentId');
    const tab = searchParams.get('tab');
    
    // Only load if:
    // 1. documentId exists in URL
    // 2. It's different from the last loaded document (prevents reload loops)
    // 3. We're not currently loading (use ref to avoid race conditions)
    if (documentId && documentId !== loadedDocumentIdRef.current && !isLoadingDocumentRef.current && !isLoadingDocument) {
      // Set refs immediately to prevent double-loading
      isLoadingDocumentRef.current = true;
      loadedDocumentIdRef.current = documentId;
      setIsLoadingDocument(true);
      
      fetchWithAuth(`/api/documents/${documentId}`)
        .then(async (response) => {
          if (response.ok) {
            const data = await response.json();
            const doc = data.document;
            if (doc.current_version_id && doc.versions) {
              const version = doc.versions.find((v: any) => v.id === doc.current_version_id) || doc.versions[0];
              if (version.extracted_data) {
                const agreementData = version.extracted_data as CreditAgreementData;
                setExtractedData(agreementData);
                setEditableData(agreementData);
              }
            } else if (doc.source_cdm_data) {
              const agreementData = doc.source_cdm_data as CreditAgreementData;
              setExtractedData(agreementData);
              setEditableData(agreementData);
            }
            if (doc.versions && doc.versions[0] && doc.versions[0].original_text) {
              setDocumentText(doc.versions[0].original_text);
            }
            if (doc.versions && doc.versions[0] && doc.versions[0].source_filename) {
              setSourceFilename(doc.versions[0].source_filename);
            }
            // setLoadedDocumentId(documentId); // Unused - using ref instead
            addToast('Document loaded from library', 'success');
            
            // Restore tab state if specified in URL
            if (tab) {
              setActiveTab(tab);
            }
          } else {
            // Reset refs on failure to allow retry
            loadedDocumentIdRef.current = null;
            addToast('Failed to load document', 'error');
          }
        })
        .catch((err) => {
          console.error('Error loading document:', err);
          // Reset refs on failure to allow retry
          loadedDocumentIdRef.current = null;
          addToast('Failed to load document', 'error');
        })
        .finally(() => {
          isLoadingDocumentRef.current = false;
          setIsLoadingDocument(false);
        });
    }
  }, [searchParams, isLoadingDocument, addToast]);

  const borrower = editableData?.parties?.find(p => p.role.toLowerCase().includes('borrower'));
  const totalCommitment = editableData?.facilities?.reduce((sum, f) => sum + (f.commitment_amount?.amount || 0), 0) || 0;
  const currency = editableData?.facilities?.[0]?.commitment_amount?.currency || 'USD';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Docu-Digitizer</h2>
          <p className="text-muted-foreground">Extract and digitize credit agreement data</p>
        </div>
        {extractedData && (
          <Button variant="outline" size="sm" onClick={handleReset}>
            <X className="h-4 w-4 mr-2" />
            New Extraction
          </Button>
        )}
      </div>

      {!extractedData ? (
        <Card className="border-slate-700 bg-slate-800/50">
          <CardContent className="p-6">
            <div className="space-y-6">
              <Tabs defaultValue="file" className="w-full">
                <TabsList className="grid w-full grid-cols-2 bg-slate-800/50 border border-slate-700">
                  <TabsTrigger
                    value="file"
                    className="data-[state=active]:bg-emerald-600 data-[state=active]:text-white text-slate-300"
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    File Upload
                  </TabsTrigger>
                  <TabsTrigger
                    value="multimodal"
                    className="data-[state=active]:bg-emerald-600 data-[state=active]:text-white text-slate-300"
                  >
                    <Sparkles className="h-4 w-4 mr-2" />
                    Multimodal Input
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="file" className="mt-4">
                  <div className="space-y-6">
                    {/* Document Type Selector */}
                    <div className="flex items-center gap-4">
                      <label className="text-sm font-medium text-slate-300">Document Type:</label>
                      <div className="flex gap-2">
                        <Button
                          variant={documentType === 'credit_agreement' ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setDocumentType('credit_agreement')}
                          className={documentType === 'credit_agreement' ? 'bg-emerald-600 hover:bg-emerald-700' : ''}
                        >
                          <FileText className="h-4 w-4 mr-2" />
                          Credit Agreement
                        </Button>
                        <Button
                          variant={documentType === 'accounting' ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setDocumentType('accounting')}
                          className={documentType === 'accounting' ? 'bg-emerald-600 hover:bg-emerald-700' : ''}
                        >
                          <Calculator className="h-4 w-4 mr-2" />
                          Accounting Document
                        </Button>
                      </div>
                      {documentType === 'accounting' && (
                        <div className="flex items-center gap-2">
                          <label className="text-sm text-slate-400">Type:</label>
                          <Select
                            value={accountingDocumentType}
                            onValueChange={setAccountingDocumentType}
                            className="w-48 bg-slate-900 border-slate-600 text-slate-100"
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select accounting document type" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="balance_sheet">Balance Sheet</SelectItem>
                              <SelectItem value="income_statement">Income Statement</SelectItem>
                              <SelectItem value="cash_flow_statement">Cash Flow Statement</SelectItem>
                              <SelectItem value="tax_return">Tax Return</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      )}
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                      <label className="group cursor-pointer">
                        <input
                          type="file"
                          accept=".pdf,.txt"
                          onChange={handleFileUpload}
                          className="hidden"
                        />
                        <div className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center transition-all hover:border-emerald-500 hover:bg-emerald-500/5">
                          <div className="w-16 h-16 rounded-full bg-slate-700 flex items-center justify-center mx-auto mb-4 group-hover:bg-emerald-500/20">
                            <Upload className="h-8 w-8 text-slate-400 group-hover:text-emerald-400" />
                          </div>
                          <p className="font-medium mb-1">Drop file here or click to upload</p>
                          <p className="text-sm text-muted-foreground">Supports PDF and TXT files</p>
                        </div>
                      </label>

                      <div className="space-y-3">
                        <textarea
                          placeholder={documentType === 'accounting' 
                            ? `Or paste your ${accountingDocumentType.replace('_', ' ')} text here...`
                            : "Or paste your credit agreement text here..."}
                          value={uploadedFile ? '' : documentText}
                          onChange={(e) => {
                            setDocumentText(e.target.value);
                            setUploadedFile(null);
                            setError(null);
                          }}
                          disabled={!!uploadedFile}
                          className="w-full h-[180px] px-4 py-3 text-sm border border-slate-600 rounded-xl bg-slate-900/50 resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 disabled:opacity-50"
                        />
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="multimodal" className="mt-4">
                  <MultimodalInputTabs
                    onAudioComplete={handleAudioComplete}
                    onImageComplete={handleImageComplete}
                    onDocumentSelect={handleDocumentSelect}
                    onTextInput={handleTextInput}
                    onError={(err) => {
                      setError(err);
                      addToast(err, 'error');
                    }}
                  />
                </TabsContent>
              </Tabs>

              {/* Active sources indicator */}
              {Object.keys(multimodalSources).length > 0 && (
                <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-emerald-400" />
                      <p className="font-medium text-slate-100">
                        Active Sources ({Object.keys(multimodalSources).length})
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setMultimodalSources({})}
                      className="text-slate-400 hover:text-slate-200"
                    >
                      <X className="h-4 w-4 mr-1" />
                      Clear All
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {multimodalSources.audio && (
                      <div className="px-3 py-1 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-sm text-emerald-300 flex items-center gap-2">
                        <Mic className="h-3 w-3" />
                        Audio
                      </div>
                    )}
                    {multimodalSources.image && (
                      <div className="px-3 py-1 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-sm text-emerald-300 flex items-center gap-2">
                        <ImageIcon className="h-3 w-3" />
                        Image
                      </div>
                    )}
                    {multimodalSources.document && (
                      <div className="px-3 py-1 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-sm text-emerald-300 flex items-center gap-2">
                        <Search className="h-3 w-3" />
                        Document
                      </div>
                    )}
                    {multimodalSources.text && (
                      <div className="px-3 py-1 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-sm text-emerald-300 flex items-center gap-2">
                        <Type className="h-3 w-3" />
                        Text
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Extract button - shown when file/text or multimodal sources are available */}
              {(documentText || uploadedFile || Object.keys(multimodalSources).length > 0) && (
                <div className="flex items-center justify-between p-4 bg-slate-900/50 rounded-xl border border-slate-700">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                      <FileText className="h-5 w-5 text-emerald-400" />
                    </div>
                    <div>
                      <p className="font-medium">
                        {uploadedFile 
                          ? uploadedFile.name 
                          : Object.keys(multimodalSources).length > 0
                          ? `${Object.keys(multimodalSources).length} source(s) ready`
                          : 'Document Ready'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {uploadedFile
                          ? `PDF file - ${(uploadedFile.size / 1024).toFixed(1)} KB`
                          : Object.keys(multimodalSources).length > 0
                          ? 'Click to fuse and extract CDM data'
                          : `${documentText.length.toLocaleString()} characters`}
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={handleExtract}
                    disabled={isExtracting}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    {isExtracting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        {Object.keys(multimodalSources).length > 0 && <Sparkles className="h-4 w-4 mr-2" />}
                        Extract Data
                      </>
                    )}
                  </Button>
                </div>
              )}

              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                  {error}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {warningMessage && (
            <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl text-yellow-400 text-sm">
              {warningMessage}
            </div>
          )}

          <div className="flex gap-4 flex-wrap">
            <Button
              variant={isEditing ? "default" : "outline"}
              onClick={() => setIsEditing(!isEditing)}
              className={isEditing ? "bg-emerald-600 hover:bg-emerald-700" : ""}
            >
              {isEditing ? <Save className="h-4 w-4 mr-2" /> : <Edit2 className="h-4 w-4 mr-2" />}
              {isEditing ? 'Done Editing' : 'Edit Data'}
            </Button>
            {isAuthenticated ? (
              <Button
                onClick={handleSaveToLibrary}
                disabled={isSaving || saveSuccess}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : saveSuccess ? (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Saved!
                  </>
                ) : (
                  <>
                    <BookOpen className="h-4 w-4 mr-2" />
                    Save to Library
                  </>
                )}
              </Button>
            ) : (
              <Button
                variant="outline"
                disabled
                className="cursor-not-allowed opacity-60"
                title="Log in to save documents"
              >
                <BookOpen className="h-4 w-4 mr-2" />
                Log in to Save
              </Button>
            )}
            <Button
              onClick={() => setIsChatbotOpen(true)}
              className="bg-purple-600 hover:bg-purple-700"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              AI Assistant
            </Button>
            <Button
              onClick={handleBroadcast}
              disabled={broadcastSuccess}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {broadcastSuccess ? (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  Broadcasted!
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Broadcast to Desktop
                </>
              )}
            </Button>
            <Button
              onClick={() => {
                if (editableData && onGenerateFromTemplate) {
                  onGenerateFromTemplate(editableData);
                }
              }}
              disabled={!editableData}
              className="bg-purple-600 hover:bg-purple-700"
              title="Generate LMA document from template using extracted data"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Generate from Template
            </Button>
          </div>

          <Tabs value={activeTab} onValueChange={(value) => {
            setActiveTab(value);
            setSearchParams(prev => {
              const newParams = new URLSearchParams(prev);
              newParams.set('tab', value);
              return newParams;
            });
            setTabHistory((prev: string[]) => [...prev, value]);
          }} className="w-full">
            <TabsList className="bg-slate-800 border border-slate-700">
              <TabsTrigger value="summary">Summary</TabsTrigger>
              <TabsTrigger value="parties">Parties</TabsTrigger>
              <TabsTrigger value="facilities">Facilities</TabsTrigger>
              <TabsTrigger value="edit">Edit CDM</TabsTrigger>
              <TabsTrigger value="clauses">Clauses</TabsTrigger>
              <TabsTrigger value="json">JSON</TabsTrigger>
            </TabsList>

            <TabsContent value="summary">
              {editableData?.is_accounting_document ? (
                <AccountingDocumentDisplay 
                  data={editableData} 
                  extractionStatus={editableData?.extraction_status}
                />
              ) : (
                <Card className="border-slate-700 bg-slate-800/50">
                  <CardContent className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-xs text-muted-foreground">Agreement Date</label>
                        {isEditing ? (
                          <input
                            type="date"
                            value={editableData?.agreement_date || ''}
                            onChange={(e) => handleFieldChange('agreement_date', e.target.value)}
                            className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                          />
                        ) : (
                          <p className="font-medium">{editableData?.agreement_date || 'N/A'}</p>
                        )}
                      </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Governing Law</label>
                      {isEditing ? (
                        <select
                          value={editableData?.governing_law || ''}
                          onChange={(e) => handleFieldChange('governing_law', e.target.value)}
                          className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                        >
                          <option value="">Select...</option>
                          <option value="NY">New York</option>
                          <option value="English">English</option>
                          <option value="Delaware">Delaware</option>
                          <option value="California">California</option>
                        </select>
                      ) : (
                        <p className="font-medium">{editableData?.governing_law || 'N/A'}</p>
                      )}
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Borrower</label>
                      <p className="font-medium">{borrower?.name || 'N/A'}</p>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Total Commitment</label>
                      <p className="font-medium text-emerald-400">
                        {currency} {totalCommitment.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Deal ID</label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editableData?.deal_id || ''}
                          onChange={(e) => handleFieldChange('deal_id', e.target.value)}
                          placeholder="Enter Deal ID"
                          className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                        />
                      ) : (
                        <p className="font-medium">{editableData?.deal_id || 'N/A'}</p>
                      )}
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Sustainability Linked</label>
                      {isEditing ? (
                        <select
                          value={editableData?.sustainability_linked ? 'yes' : 'no'}
                          onChange={(e) => handleFieldChange('sustainability_linked', e.target.value === 'yes')}
                          className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                        >
                          <option value="no">No</option>
                          <option value="yes">Yes</option>
                        </select>
                      ) : (
                        <p className="font-medium">
                          {editableData?.sustainability_linked ? (
                            <span className="text-emerald-400">Yes</span>
                          ) : (
                            'No'
                          )}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
              )}
            </TabsContent>

            <TabsContent value="parties">
              <Card className="border-slate-700 bg-slate-800/50">
                <CardContent className="p-6">
                  {editableData?.parties && editableData.parties.length > 0 ? (
                    <div className="space-y-3">
                      {editableData.parties.map((party, idx) => (
                        <div key={idx} className="p-3 bg-slate-900/50 rounded-lg border border-slate-700">
                          {isEditing ? (
                            <div className="space-y-2">
                              <div>
                                <label className="text-xs text-muted-foreground">Name</label>
                                <input
                                  type="text"
                                  value={party.name || ''}
                                  onChange={(e) => {
                                    const updatedParties = [...(editableData.parties || [])];
                                    updatedParties[idx] = { ...party, name: e.target.value };
                                    handleFieldChange('parties', updatedParties);
                                  }}
                                  className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-muted-foreground">Role</label>
                                <input
                                  type="text"
                                  value={party.role || ''}
                                  onChange={(e) => {
                                    const updatedParties = [...(editableData.parties || [])];
                                    updatedParties[idx] = { ...party, role: e.target.value };
                                    handleFieldChange('parties', updatedParties);
                                  }}
                                  className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-muted-foreground">LEI</label>
                                <input
                                  type="text"
                                  value={party.lei || ''}
                                  onChange={(e) => {
                                    const updatedParties = [...(editableData.parties || [])];
                                    updatedParties[idx] = { ...party, lei: e.target.value };
                                    handleFieldChange('parties', updatedParties);
                                  }}
                                  className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm font-mono"
                                />
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium">{party.name}</p>
                                <p className="text-sm text-muted-foreground">{party.role}</p>
                              </div>
                              {party.lei && (
                                <span className="text-xs font-mono bg-slate-700 px-2 py-1 rounded">
                                  LEI: {party.lei}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No parties found. {isEditing && 'Add parties in the Edit CDM tab.'}</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="facilities">
              <Card className="border-slate-700 bg-slate-800/50">
                <CardContent className="p-6">
                  {editableData?.facilities && editableData.facilities.length > 0 ? (
                    <div className="space-y-3">
                      {editableData.facilities.map((facility, idx) => (
                        <div key={idx} className="p-4 bg-slate-900/50 rounded-lg border border-slate-700">
                          {isEditing ? (
                            <div className="space-y-3">
                              <div>
                                <label className="text-xs text-muted-foreground">Facility Name</label>
                                <input
                                  type="text"
                                  value={facility.facility_name || ''}
                                  onChange={(e) => {
                                    const updatedFacilities = [...(editableData.facilities || [])];
                                    updatedFacilities[idx] = { ...facility, facility_name: e.target.value };
                                    handleFieldChange('facilities', updatedFacilities);
                                  }}
                                  className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                                />
                              </div>
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <label className="text-xs text-muted-foreground">Amount</label>
                                  <input
                                    type="number"
                                    value={facility.commitment_amount?.amount || ''}
                                    onChange={(e) => {
                                      const updatedFacilities = [...(editableData.facilities || [])];
                                      updatedFacilities[idx] = {
                                        ...facility,
                                        commitment_amount: {
                                          ...facility.commitment_amount,
                                          amount: parseFloat(e.target.value) || 0,
                                          currency: facility.commitment_amount?.currency || 'USD'
                                        }
                                      };
                                      handleFieldChange('facilities', updatedFacilities);
                                    }}
                                    className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-muted-foreground">Currency</label>
                                  <input
                                    type="text"
                                    value={facility.commitment_amount?.currency || 'USD'}
                                    onChange={(e) => {
                                      const updatedFacilities = [...(editableData.facilities || [])];
                                      updatedFacilities[idx] = {
                                        ...facility,
                                        commitment_amount: {
                                          ...facility.commitment_amount,
                                          currency: e.target.value,
                                          amount: facility.commitment_amount?.amount || 0
                                        }
                                      };
                                      handleFieldChange('facilities', updatedFacilities);
                                    }}
                                    className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                                  />
                                </div>
                              </div>
                              <div>
                                <label className="text-xs text-muted-foreground">Maturity Date</label>
                                <input
                                  type="date"
                                  value={facility.maturity_date || ''}
                                  onChange={(e) => {
                                    const updatedFacilities = [...(editableData.facilities || [])];
                                    updatedFacilities[idx] = { ...facility, maturity_date: e.target.value };
                                    handleFieldChange('facilities', updatedFacilities);
                                  }}
                                  className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                                />
                              </div>
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <label className="text-xs text-muted-foreground">Benchmark</label>
                                  <input
                                    type="text"
                                    value={facility.interest_terms?.rate_option?.benchmark || ''}
                                    onChange={(e) => {
                                      const updatedFacilities = [...(editableData.facilities || [])];
                                      updatedFacilities[idx] = {
                                        ...facility,
                                        interest_terms: {
                                          ...facility.interest_terms,
                                          rate_option: {
                                            ...facility.interest_terms?.rate_option,
                                            benchmark: e.target.value
                                          }
                                        }
                                      };
                                      handleFieldChange('facilities', updatedFacilities);
                                    }}
                                    className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-muted-foreground">Spread (bps)</label>
                                  <input
                                    type="number"
                                    value={facility.interest_terms?.rate_option?.spread_bps || ''}
                                    onChange={(e) => {
                                      const updatedFacilities = [...(editableData.facilities || [])];
                                      updatedFacilities[idx] = {
                                        ...facility,
                                        interest_terms: {
                                          ...facility.interest_terms,
                                          rate_option: {
                                            ...facility.interest_terms?.rate_option,
                                            spread_bps: parseFloat(e.target.value) || 0
                                          }
                                        }
                                      };
                                      handleFieldChange('facilities', updatedFacilities);
                                    }}
                                    className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm"
                                  />
                                </div>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className="flex items-center justify-between mb-2">
                                <p className="font-medium">{facility.facility_name}</p>
                                <span className="text-emerald-400 font-medium">
                                  {facility.commitment_amount?.currency} {facility.commitment_amount?.amount?.toLocaleString()}
                                </span>
                              </div>
                              <div className="grid grid-cols-3 gap-4 text-sm">
                                <div>
                                  <span className="text-muted-foreground">Maturity:</span>{' '}
                                  {facility.maturity_date}
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Benchmark:</span>{' '}
                                  {facility.interest_terms?.rate_option?.benchmark}
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Spread:</span>{' '}
                                  {facility.interest_terms?.rate_option?.spread_bps} bps
                                </div>
                              </div>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No facilities found. {isEditing && 'Add facilities in the Edit CDM tab.'}</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="edit">
              <Card className="border-slate-700 bg-slate-800/50">
                <CardContent className="p-6">
                  {editableData ? (
                    <CdmAccordionEditor
                      cdmData={editableData}
                      onUpdate={setEditableData}
                      documentId={clauseEditorDocumentId || undefined}
                      multimodalSources={multimodalSources}
                    />
                  ) : (
                    <p className="text-muted-foreground">No data to edit</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="clauses">
              <Card className="border-slate-700 bg-slate-800/50">
                <CardContent className="p-6">
                  {clauseEditorDocumentId ? (
                    <ClauseEditor />
                  ) : (
                    <p className="text-muted-foreground">Save document to library to enable clause editing</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="json">
              <Card className="border-slate-700 bg-slate-800/50">
                <CardContent className="p-6">
                  <pre className="text-xs font-mono bg-slate-900 p-4 rounded-lg overflow-auto max-h-96 text-slate-300">
                    {JSON.stringify(editableData, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      )}

      {/* Digitizer Chatbot Modal */}
      <DigitizerChatbot
        isOpen={isChatbotOpen}
        onClose={() => setIsChatbotOpen(false)}
        dealId={extractedData?.deal_id ? parseInt(extractedData.deal_id) : null}
        documentId={documentId}
        documentContext={extractedData ? (extractedData as unknown as Record<string, unknown>) : undefined}
        onWorkflowLaunched={(workflowType, result) => {
          console.log('Workflow launched:', workflowType, result);
          addToast(`${workflowType} workflow launched successfully`, 'success');
        }}
      />
    </div>
  );
}
