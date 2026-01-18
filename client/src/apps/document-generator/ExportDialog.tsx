/**
 * Export Dialog Component
 * 
 * Provides a dialog for exporting generated documents with format selection
 * and export options.
 */

import { useState } from 'react';
import { X, Download, FileText, File, Loader2 } from 'lucide-react';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (format: 'word' | 'pdf', options?: ExportOptions) => void;
  documentName?: string;
}

interface ExportOptions {
  includeTrackedChanges?: boolean;
  includeComments?: boolean;
  watermark?: string;
}

export function ExportDialog({ isOpen, onClose, onExport, documentName }: ExportDialogProps) {
  const [selectedFormat, setSelectedFormat] = useState<'word' | 'pdf'>('word');
  const [options, setOptions] = useState<ExportOptions>({
    includeTrackedChanges: false,
    includeComments: false,
    watermark: '',
  });
  const [exporting, setExporting] = useState(false);

  if (!isOpen) return null;

  const handleExport = async () => {
    setExporting(true);
    try {
      await onExport(selectedFormat, options);
      onClose();
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Download className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">Export Document</h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={exporting}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {documentName && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Document Name
              </label>
              <p className="text-sm text-gray-600">{documentName}</p>
            </div>
          )}

          {/* Format Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Export Format
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setSelectedFormat('word')}
                disabled={exporting}
                className={`p-4 border-2 rounded-lg transition-all ${
                  selectedFormat === 'word'
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                } ${exporting ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <FileText className={`h-8 w-8 mx-auto mb-2 ${
                  selectedFormat === 'word' ? 'text-blue-600' : 'text-gray-400'
                }`} />
                <div className={`text-sm font-medium ${
                  selectedFormat === 'word' ? 'text-blue-900' : 'text-gray-700'
                }`}>
                  Word (.docx)
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Editable format
                </div>
              </button>
              <button
                onClick={() => setSelectedFormat('pdf')}
                disabled={exporting}
                className={`p-4 border-2 rounded-lg transition-all ${
                  selectedFormat === 'pdf'
                    ? 'border-red-600 bg-red-50'
                    : 'border-gray-200 hover:border-gray-300'
                } ${exporting ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <File className={`h-8 w-8 mx-auto mb-2 ${
                  selectedFormat === 'pdf' ? 'text-red-600' : 'text-gray-400'
                }`} />
                <div className={`text-sm font-medium ${
                  selectedFormat === 'pdf' ? 'text-red-900' : 'text-gray-700'
                }`}>
                  PDF (.pdf)
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Read-only format
                </div>
              </button>
            </div>
          </div>

          {/* Export Options (for Word) */}
          {selectedFormat === 'word' && (
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                Export Options
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={options.includeTrackedChanges || false}
                    onChange={(e) => setOptions({ ...options, includeTrackedChanges: e.target.checked })}
                    disabled={exporting}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Include tracked changes</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={options.includeComments || false}
                    onChange={(e) => setOptions({ ...options, includeComments: e.target.checked })}
                    disabled={exporting}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Include comments</span>
                </label>
              </div>
            </div>
          )}

          {/* Watermark Option */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Watermark (Optional)
            </label>
            <input
              type="text"
              value={options.watermark || ''}
              onChange={(e) => setOptions({ ...options, watermark: e.target.value })}
              placeholder="e.g., DRAFT, CONFIDENTIAL"
              disabled={exporting}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            disabled={exporting}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
          >
            {exporting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                Export
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
















