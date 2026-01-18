/**
 * Input Tabs Component
 * 
 * Tabbed interface for Audio, Image, Document, and Text inputs.
 * Provides a clean interface for selecting input sources.
 */

import React from 'react';
import { Mic, Image as ImageIcon, FileText, Type } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { AudioRecorder } from './AudioRecorder';
import { ImageUploader } from './ImageUploader';
import { DocumentSearch } from './DocumentSearch';
import type { ExtractionResult, DocumentResult } from '../../apps/docu-digitizer/MultimodalInputTabs';

interface InputTabsProps {
  onAudioComplete?: (result: {
    transcription: string;
    agreement?: Record<string, unknown>;
    extraction_status?: string;
  }) => void;
  onImageComplete?: (result: ExtractionResult) => void;
  onDocumentSelect?: (document: DocumentResult | {
    id: number;
    title: string;
    cdm_data?: Record<string, unknown>;
  }) => void;
  onTextInput?: (text: string) => void;
  onError?: (error: string) => void;
  className?: string;
}

export function InputTabs({
  onAudioComplete,
  onImageComplete,
  onDocumentSelect,
  onTextInput,
  onError,
  className = '',
}: InputTabsProps) {
  const [textInput, setTextInput] = React.useState('');

  const handleTextSubmit = () => {
    if (textInput.trim() && onTextInput) {
      onTextInput(textInput.trim());
      setTextInput('');
    }
  };

  const handleTextKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleTextSubmit();
    }
  };

  return (
    <div className={className}>
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
            onTranscriptionComplete={(result) => {
              if (onAudioComplete) {
                onAudioComplete({
                  transcription: result.transcription || '',
                  agreement: result.agreement,
                  extraction_status: result.extraction_status,
                });
              }
            }}
            onError={onError}
            extractCdm={true}
          />
        </TabsContent>

        <TabsContent value="image" className="mt-4">
          <ImageUploader
            onExtractionComplete={(result) => {
              if (onImageComplete) {
                onImageComplete(result);
              }
            }}
            onError={onError}
            extractCdm={true}
          />
        </TabsContent>

        <TabsContent value="document" className="mt-4">
          <DocumentSearch
            onDocumentSelect={(doc) => {
              if (onDocumentSelect) {
                // Pass the full DocumentResult directly
                onDocumentSelect(doc);
              }
            }}
            onCdmDataSelect={(cdmData) => {
              if (onDocumentSelect) {
                onDocumentSelect({
                  id: 0,
                  title: 'Retrieved Document',
                  cdm_data: cdmData,
                });
              }
            }}
            onError={onError}
          />
        </TabsContent>

        <TabsContent value="text" className="mt-4">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Enter Text
              </label>
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyPress={handleTextKeyPress}
                placeholder="Paste or type text here..."
                className="w-full h-48 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              />
            </div>
            <button
              onClick={handleTextSubmit}
              disabled={!textInput.trim()}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Process Text
            </button>
            <p className="text-xs text-gray-500">
              Press Enter to submit, Shift+Enter for new line
            </p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}














