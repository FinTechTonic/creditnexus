/**
 * LicenseViewer Component
 * 
 * Displays license files (LICENCE.md or RAIL.md) in a readable format
 * with theme-aware styling and navigation back to previous page.
 */

import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, FileText, Loader2 } from 'lucide-react';
import { useThemeClasses } from '@/utils/themeUtils';
import { fetchWithAuth } from '@/context/AuthContext';

interface LicenseViewerProps {
  licenseType?: 'license' | 'licence' | 'rail';
  onClose?: () => void;
}

/**
 * Simple markdown to HTML converter for basic formatting
 */
function markdownToHtml(markdown: string): string {
  let html = markdown
    // Headers
    .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mb-4 mt-6">$1</h1>')
    .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mb-3 mt-5">$1</h2>')
    .replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mb-2 mt-4">$1</h3>')
    // Bold
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    // Code blocks
    .replace(/```([\s\S]*?)```/gim, '<pre class="bg-slate-900 p-4 rounded-lg overflow-x-auto my-4"><code>$1</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/gim, '<code class="bg-slate-800 px-1 py-0.5 rounded text-sm">$1</code>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" class="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">$1</a>')
    // Lists
    .replace(/^\* (.*$)/gim, '<li class="ml-4 mb-1">$1</li>')
    .replace(/^- (.*$)/gim, '<li class="ml-4 mb-1">$1</li>')
    .replace(/^(\d+)\. (.*$)/gim, '<li class="ml-4 mb-1">$2</li>')
    // Paragraphs
    .split('\n\n')
    .map(para => {
      if (para.trim().startsWith('<')) {
        return para; // Already formatted
      }
      return `<p class="mb-4">${para.trim()}</p>`;
    })
    .join('\n');

  // Wrap list items in ul tags
  html = html.replace(/(<li[^>]*>.*<\/li>)/gim, (match, _p1) => { // Prefix with _ - unused
    if (!match.includes('<ul')) {
      return `<ul class="list-disc ml-6 mb-4">${match}</ul>`;
    }
    return match;
  });

  return html;
}

export function LicenseViewer({ licenseType, onClose }: LicenseViewerProps) {
  const navigate = useNavigate();
  const params = useParams();
  const classes = useThemeClasses();
  
  // Determine license type from props or URL params
  const type = licenseType || (params.licenseType as 'license' | 'licence' | 'rail') || 'license';
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLicense = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Normalize type for API and file fetch
        const normalizedType = (type === 'licence' || type === 'license') ? 'license' : 'rail';
        
        // Try to fetch from API first
        try {
          const response = await fetchWithAuth(`/api/licenses/${normalizedType}`);
          if (response.ok) {
            const data = await response.json();
            setContent(data.content || '');
            setLoading(false);
            return;
          }
        } catch (apiError) {
          console.warn('API fetch failed, trying direct file fetch:', apiError);
        }

        // Fallback: try to fetch directly from public folder or root
        try {
          const fileName = normalizedType === 'license' ? 'LICENSE.md' : 'RAIL.md';
          const baseUrl = import.meta.env.BASE_URL || '/';
          const filePath = baseUrl.endsWith('/') ? `${baseUrl}${fileName}` : `${baseUrl}/${fileName}`;
          const response = await fetch(filePath);
          if (response.ok) {
            const text = await response.text();
            setContent(text);
            setLoading(false);
            return;
          }
        } catch (fetchError) {
          console.warn('Direct file fetch failed:', fetchError);
        }

        // If both fail, show error
        setError(`License file not found. Please ensure ${normalizedType === 'license' ? 'LICENSE.md' : 'RAIL.md'} exists in the root directory.`);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load license file');
        setLoading(false);
      }
    };

    fetchLicense();
  }, [type]);

  const handleClose = () => {
    if (onClose) {
      onClose();
    } else {
      navigate(-1);
    }
  };

  const title = (type === 'licence' || type === 'license') ? 'License' : 'Responsible AI License (RAIL)';
  const htmlContent = content ? markdownToHtml(content) : '';

  return (
    <div className="min-h-screen p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <Card className={`${classes.background.card} ${classes.border.default}`}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className={`h-6 w-6 ${classes.text.primary}`} />
                <CardTitle className={classes.text.primary}>{title}</CardTitle>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClose}
                className={classes.text.secondary}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className={`h-8 w-8 animate-spin ${classes.text.secondary}`} />
                <span className={`ml-3 ${classes.text.secondary}`}>Loading license file...</span>
              </div>
            )}

            {error && (
              <div className={`p-4 rounded-lg bg-red-900/20 border border-red-500/30 ${classes.text.primary}`}>
                <p className="font-semibold mb-2">Error loading license file</p>
                <p className={classes.text.secondary}>{error}</p>
              </div>
            )}

            {!loading && !error && content && (
              <div 
                className={`prose prose-invert max-w-none ${classes.text.primary}`}
                dangerouslySetInnerHTML={{ __html: htmlContent }}
                style={{
                  color: 'inherit',
                }}
              />
            )}

            {!loading && !error && !content && (
              <div className={`p-4 rounded-lg ${classes.background.muted} ${classes.text.secondary}`}>
                <p>No content available.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
