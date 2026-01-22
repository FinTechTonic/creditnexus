import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Download, FileText, Loader2 } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

export function NexusFileGenerator({
  dealId,
  documentId,
  onFileGenerated,
}: {
  dealId?: number;
  documentId?: number;
  onFileGenerated?: (filename: string) => void;
}) {
  const [generating, setGenerating] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expiresInHours, setExpiresInHours] = useState(72);
  const [downloadTtlHours, setDownloadTtlHours] = useState<number | null>(168);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const response = await fetchWithAuth('/api/nexus/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_type: 'verification',
          deal_id: dealId,
          document_id: documentId,
          include_files: true,
          expires_in_hours: expiresInHours,
          download_ttl_hours: downloadTtlHours,
        }),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const contentDisposition = response.headers.get('Content-Disposition');
        const extractedFilename = contentDisposition
          ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
          : `deal_share_${Date.now()}.nexus`;

        setDownloadUrl(url);
        setFilename(extractedFilename);
        onFileGenerated?.(extractedFilename);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to generate .nexus file' }));
        setError(errorData.detail || 'Failed to generate .nexus file');
      }
    } catch (err) {
      console.error('Failed to generate .nexus file:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate .nexus file');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (downloadUrl && filename) {
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      a.click();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Generate .nexus File
        </CardTitle>
        <CardDescription>
          Create a self-contained .nexus file for sharing workflows offline
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="expires-in-hours">Link Expiration (hours)</Label>
          <Input
            id="expires-in-hours"
            type="number"
            min="1"
            max="720"
            value={expiresInHours}
            onChange={(e) => setExpiresInHours(parseInt(e.target.value) || 72)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="download-ttl-hours">Download TTL (hours, optional)</Label>
          <Input
            id="download-ttl-hours"
            type="number"
            min="1"
            placeholder="Leave empty for no TTL"
            value={downloadTtlHours || ''}
            onChange={(e) => setDownloadTtlHours(e.target.value ? parseInt(e.target.value) : null)}
          />
        </div>

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md text-red-700 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        <Button onClick={handleGenerate} disabled={generating} className="w-full">
          {generating ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <FileText className="h-4 w-4 mr-2" />
              Generate .nexus File
            </>
          )}
        </Button>

        {downloadUrl && filename && (
          <Button onClick={handleDownload} variant="outline" className="w-full">
            <Download className="h-4 w-4 mr-2" />
            Download {filename}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
