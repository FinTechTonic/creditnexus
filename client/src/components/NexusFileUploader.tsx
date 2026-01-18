import { useState } from 'react';
// Button removed - unused
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Upload, Check, Loader2, AlertCircle } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

export function NexusFileUploader({
  onFileParsed,
}: {
  onFileParsed?: (data: any) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    if (!file.name.endsWith('.nexus')) {
      setError('Please select a .nexus file');
      return;
    }

    setUploading(true);
    setError(null);
    setUploaded(false);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetchWithAuth('/api/nexus/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setUploaded(true);
        setResult(data);
        onFileParsed?.(data);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to upload .nexus file' }));
        setError(errorData.detail || 'Failed to upload .nexus file');
      }
    } catch (err) {
      console.error('Failed to upload .nexus file:', err);
      setError(err instanceof Error ? err.message : 'Failed to upload .nexus file');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload .nexus File
        </CardTitle>
        <CardDescription>
          Upload and parse a .nexus file to process shared workflows
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <input
            type="file"
            accept=".nexus"
            onChange={handleUpload}
            disabled={uploading}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-md file:border-0
              file:text-sm file:font-semibold
              file:bg-primary file:text-primary-foreground
              hover:file:bg-primary/90
              disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md text-red-700 dark:text-red-400 text-sm flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {uploading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Uploading and parsing file...
          </div>
        )}

        {uploaded && result && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <Check className="h-4 w-4" />
              <span className="font-medium">File uploaded and processed successfully</span>
            </div>
            <div className="p-3 bg-muted rounded-md text-sm space-y-1">
              <div><strong>Workflow ID:</strong> {result.workflow_id}</div>
              <div><strong>Workflow Type:</strong> {result.workflow_type}</div>
              {result.deal_id && <div><strong>Deal ID:</strong> {result.deal_id}</div>}
              <div><strong>Files Processed:</strong> {result.files_processed}</div>
              <div><strong>Embedded Files:</strong> {result.embedded_files}</div>
              <div><strong>Large File References:</strong> {result.large_file_references}</div>
              {result.blockchain_tx_hash && (
                <div><strong>Blockchain TX:</strong> {result.blockchain_tx_hash.substring(0, 16)}...</div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
