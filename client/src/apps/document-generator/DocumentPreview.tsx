/**
 * Document Preview Component
 * 
 * Displays a preview of the generated document with options to:
 * - View document in iframe or PDF viewer
 * - Download the document
 * - Edit/regenerate
 */

import { useState } from 'react';
import { Download, Edit, FileText, Loader2, AlertCircle } from 'lucide-react';
import { fetchWithAuth } from '../../context/AuthContext';

interface GeneratedDocument {
  id: number;
  document_id: string;
  generated_file_path: string;
  status: string;
  generation_summary?: {
    total_fields: number;
    mapped_fields_count: number;
    ai_fields_count: number;
    missing_required_fields: string[];
  };
}

interface DocumentPreviewProps {
  document: GeneratedDocument;
  onEdit?: () => void;
  onExport?: (format: 'word' | 'pdf') => void;
}

export function DocumentPreview({ document: generatedDocument, onEdit, onExport }: DocumentPreviewProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, _setPreviewUrl] = useState<string | null>(null); // Prefix setter with _ - getter is used

  // For Word documents, we'll need to convert to PDF or use Office Online viewer
  // For now, we'll show a placeholder with download option
  const isWordDocument = generatedDocument.generated_file_path?.endsWith('.docx');
  const isPdfDocument = generatedDocument.generated_file_path?.endsWith('.pdf');

  const handleDownload = async (format: 'word' | 'pdf') => {
    if (onExport) {
      onExport(format);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth(`/api/generated-documents/${generatedDocument.id}/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ format }),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = window.document.createElement('a');
        a.href = url;
        a.download = `generated_document.${format === 'pdf' ? 'pdf' : 'docx'}`;
        window.document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        window.document.body.removeChild(a);
      } else {
        throw new Error('Export failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Document Preview</h3>
        </div>
        <div className="flex items-center gap-2">
          {onEdit && (
            <button
              onClick={onEdit}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
            >
              <Edit className="h-4 w-4" />
              Edit
            </button>
          )}
          <button
            onClick={() => handleDownload('word')}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Download Word
          </button>
          <button
            onClick={() => handleDownload('pdf')}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Download PDF
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 m-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Preview Content */}
      <div className="flex-1 overflow-hidden">
        {isPdfDocument && previewUrl ? (
          <iframe
            src={previewUrl}
            className="w-full h-full border-0"
            title="Document Preview"
          />
        ) : isWordDocument ? (
          <div className="flex flex-col items-center justify-center h-full p-8 text-center">
            <FileText className="w-16 h-16 text-gray-400 mb-4" />
            <h4 className="text-lg font-medium text-gray-900 mb-2">
              Word Document Generated
            </h4>
            <p className="text-sm text-gray-600 mb-4">
              Preview for Word documents is not available in the browser.
              Please download the document to view it.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => handleDownload('word')}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Download Word
              </button>
              <button
                onClick={() => handleDownload('pdf')}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Export as PDF
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full p-8 text-center">
            <FileText className="w-16 h-16 text-gray-400 mb-4" />
            <h4 className="text-lg font-medium text-gray-900 mb-2">
              Document Generated Successfully
            </h4>
            <p className="text-sm text-gray-600 mb-4">
              File saved at: <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                {generatedDocument.generated_file_path}
              </code>
            </p>
            {generatedDocument.generation_summary && (
              <div className="bg-gray-50 rounded-lg p-4 mb-4 text-left max-w-md">
                <h5 className="text-sm font-semibold text-gray-900 mb-2">Generation Summary</h5>
                <div className="text-xs text-gray-600 space-y-1">
                  <div>Total fields: {generatedDocument.generation_summary.total_fields}</div>
                  <div>Mapped fields: {generatedDocument.generation_summary.mapped_fields_count}</div>
                  <div>AI-generated sections: {generatedDocument.generation_summary.ai_fields_count}</div>
                  {generatedDocument.generation_summary.missing_required_fields.length > 0 && (
                    <div className="text-red-600 mt-2">
                      Missing required fields: {generatedDocument.generation_summary.missing_required_fields.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => handleDownload('word')}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Download Word
              </button>
              <button
                onClick={() => handleDownload('pdf')}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Export as PDF
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-600">
        <div className="flex items-center justify-between">
          <span>Status: <span className="font-medium">{generatedDocument.status}</span></span>
          <span>Document ID: <span className="font-mono">{generatedDocument.document_id}</span></span>
        </div>
      </div>
    </div>
  );
}
















