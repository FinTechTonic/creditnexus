/**
 * Multimodal Input Tabs Component
 * 
 * Integrates audio, image, document search, and text input capabilities
 * into the Document Parser with dark theme styling.
 */

import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Mic, Image as ImageIcon, Type, Search } from 'lucide-react';
import { AudioRecorder } from '@/apps/document-generator/AudioRecorder';
import { ImageUploader } from '@/apps/document-generator/ImageUploader';
import { DocumentSearch } from '@/apps/document-generator/DocumentSearch';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';

export interface TranscriptionResult {
  status: string;
  transcription: string;
  transcription_length: number;
  source_filename: string;
  source_lang?: string;
  target_lang?: string;
  agreement?: Record<string, unknown>;
  extraction_status?: string;
  extraction_message?: string;
}

export interface ExtractionResult {
  status: string;
  ocr_text: string;
  ocr_text_length: number;
  source_filenames: string[];
  images_processed: number;
  ocr_texts_per_image: Array<{
    filename: string;
    text: string;
    length: number;
  }>;
  agreement?: Record<string, unknown>;
  extraction_status?: string;
  extraction_message?: string;
}

export interface DocumentResult {
  document_id: number;
  similarity_score: number;
  distance: number;
  document: {
    id: number;
    title: string;
    borrower_name: string | null;
    borrower_lei: string | null;
    governing_law: string | null;
    total_commitment: number | null;
    currency: string | null;
    agreement_date: string | null;
    sustainability_linked: boolean;
    created_at: string;
    updated_at: string;
  };
  cdm_data?: Record<string, unknown> | null;
  workflow?: {
    state: string;
    priority: string;
  } | null;
  latest_version?: {
    id: number;
    version_number: number;
    extracted_data: Record<string, unknown>;
  } | null;
}

interface MultimodalInputTabsProps {
  onAudioComplete?: (result: TranscriptionResult) => void;
  onImageComplete?: (result: ExtractionResult) => void;
  onDocumentSelect?: (document: DocumentResult) => void;
  onTextInput?: (text: string, cdmData?: Record<string, unknown>) => void;
  onError?: (error: string) => void;
  className?: string;
}

export function MultimodalInputTabs({
  onAudioComplete,
  onImageComplete,
  onDocumentSelect,
  onTextInput,
  onError,
  className = '',
}: MultimodalInputTabsProps) {
  const [textInput, setTextInput] = useState('');
  const [isProcessingText, setIsProcessingText] = useState(false);

  const handleAudioComplete = (result: TranscriptionResult) => {
    if (onAudioComplete) {
      onAudioComplete(result);
    }
  };

  const handleImageComplete = (result: ExtractionResult) => {
    if (onImageComplete) {
      onImageComplete(result);
    }
  };

  const handleDocumentSelect = (document: DocumentResult) => {
    if (onDocumentSelect) {
      onDocumentSelect(document);
    }
  };

  const handleTextSubmit = async () => {
    if (!textInput.trim()) {
      if (onError) {
        onError('Please enter some text');
      }
      return;
    }

    setIsProcessingText(true);
    try {
      // If onTextInput is provided, call it directly
      if (onTextInput) {
        onTextInput(textInput);
      }
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : 'Failed to process text');
      }
    } finally {
      setIsProcessingText(false);
    }
  };

  return (
    <div className={className}>
      <Tabs defaultValue="audio" className="w-full">
        <TabsList className="grid w-full grid-cols-4 bg-slate-800/50 border border-slate-700">
          <TabsTrigger
            value="audio"
            className="data-[state=active]:bg-emerald-600 data-[state=active]:text-white text-slate-300"
          >
            <Mic className="h-4 w-4 mr-2" />
            Audio
          </TabsTrigger>
          <TabsTrigger
            value="image"
            className="data-[state=active]:bg-emerald-600 data-[state=active]:text-white text-slate-300"
          >
            <ImageIcon className="h-4 w-4 mr-2" />
            Image
          </TabsTrigger>
          <TabsTrigger
            value="search"
            className="data-[state=active]:bg-emerald-600 data-[state=active]:text-white text-slate-300"
          >
            <Search className="h-4 w-4 mr-2" />
            Search
          </TabsTrigger>
          <TabsTrigger
            value="text"
            className="data-[state=active]:bg-emerald-600 data-[state=active]:text-white text-slate-300"
          >
            <Type className="h-4 w-4 mr-2" />
            Text
          </TabsTrigger>
        </TabsList>

        <TabsContent value="audio" className="mt-4">
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-6">
              <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                <AudioRecorder
                  onTranscriptionComplete={handleAudioComplete}
                  onError={onError}
                  extractCdm={true}
                  theme="dark"
                  className="bg-transparent border-0 p-0"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="image" className="mt-4">
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-6">
              <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                <ImageUploader
                  onExtractionComplete={handleImageComplete}
                  onError={onError}
                  extractCdm={true}
                  className="bg-transparent border-0 p-0"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="search" className="mt-4">
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-6">
              <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                <DocumentSearch
                  onDocumentSelect={handleDocumentSelect}
                  onCdmDataSelect={(cdmData) => {
                    if (onTextInput) {
                      onTextInput('', cdmData);
                    }
                  }}
                  theme="dark"
                  className="bg-transparent border-0 p-0"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="text" className="mt-4">
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-slate-400 mb-2 block">
                    Enter or paste credit agreement text
                  </label>
                  <Textarea
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    placeholder="Paste your credit agreement text here..."
                    className="bg-slate-900/50 border-slate-600 text-slate-100 min-h-[200px] focus:ring-emerald-500/20 focus:border-emerald-500"
                  />
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-slate-500">
                      {textInput.length.toLocaleString()} characters
                    </span>
                  </div>
                </div>
                <Button
                  onClick={handleTextSubmit}
                  disabled={!textInput.trim() || isProcessingText}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  {isProcessingText ? (
                    <>
                      <Send className="h-4 w-4 mr-2 animate-pulse" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Submit Text
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
