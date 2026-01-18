/**
 * DeepResearch Result View Component
 * 
 * Displays DeepResearch analysis results with:
 * - Research answer
 * - Knowledge items
 * - Visited URLs
 * - Search queries used
 * - Token usage statistics
 */

import { useState, useEffect } from 'react';
import {
  Search,
  ExternalLink,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Copy,
  Download,
  X,
  Link as LinkIcon,
  List,
  Globe
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/components/ui/toast';

interface DeepResearchResult {
  id: number;
  research_id: string;
  query: string;
  answer: string | null;
  knowledge_items: Array<{
    title?: string;
    content?: string;
    url?: string;
    relevance_score?: number;
  }> | null;
  visited_urls: string[] | null;
  searched_queries: string[] | null;
  token_usage: {
    total_tokens?: number;
    prompt_tokens?: number;
    completion_tokens?: number;
  } | null;
  status: string;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  deal_id: number | null;
}

interface DeepResearchResultViewProps {
  researchId: string;
  onClose?: () => void;
  dealId?: number | null;
}

export function DeepResearchResultView({
  researchId,
  onClose,
  dealId: _dealId // Prefix with _ - unused
}: DeepResearchResultViewProps) {
  const [result, setResult] = useState<DeepResearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { addToast } = useToast();

  useEffect(() => {
    const fetchResult = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetchWithAuth(`/api/deep-research/results/${researchId}`);
        
        if (!response.ok) {
          if (response.status === 501) {
            // Endpoint not implemented yet - try alternative
            throw new Error('Research results retrieval not yet implemented. Please check back later.');
          }
          const errorData = await response.json().catch(() => ({ message: 'Failed to load result' }));
          throw new Error(errorData.detail?.message || errorData.message || 'Failed to load result');
        }
        
        const data = await response.json();
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load research result');
        addToast({
          title: 'Error',
          description: err instanceof Error ? err.message : 'Failed to load research result',
          variant: 'destructive'
        });
      } finally {
        setLoading(false);
      }
    };
    
    fetchResult();
  }, [researchId, addToast]);

  const handleCopyAnswer = () => {
    if (result?.answer) {
      navigator.clipboard.writeText(result.answer);
      addToast({
        title: 'Copied',
        description: 'Answer copied to clipboard',
        variant: 'default'
      });
    }
  };

  const handleDownloadReport = () => {
    if (!result) return;
    
    const report = {
      research_id: result.research_id,
      query: result.query,
      answer: result.answer,
      knowledge_items: result.knowledge_items,
      visited_urls: result.visited_urls,
      searched_queries: result.searched_queries,
      token_usage: result.token_usage,
      created_at: result.created_at,
      completed_at: result.completed_at
    };
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `deepresearch_${result.research_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    addToast({
      title: 'Downloaded',
      description: 'Research report downloaded',
      variant: 'default'
    });
  };

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-emerald-500 mb-4" />
            <p className="text-slate-400">Loading research result...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
            <p className="text-red-400 mb-2">Error loading result</p>
            <p className="text-slate-400 text-sm">{error}</p>
            {onClose && (
              <Button onClick={onClose} variant="outline" className="mt-4">
                Close
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-12">
            <FileText className="h-12 w-12 text-slate-500 mb-4" />
            <p className="text-slate-400">No result found</p>
            {onClose && (
              <Button onClick={onClose} variant="outline" className="mt-4">
                Close
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  const statusColors: Record<string, { bg: string; text: string }> = {
    completed: { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
    processing: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
    pending: { bg: 'bg-amber-500/20', text: 'text-amber-400' },
    failed: { bg: 'bg-red-500/20', text: 'text-red-400' }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-3">
            <Search className="h-6 w-6 text-emerald-400" />
            <div>
              <CardTitle className="text-slate-100">DeepResearch Result</CardTitle>
              <p className="text-sm text-slate-400 mt-1">
                Research ID: {result.research_id}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={statusColors[result.status]?.bg || 'bg-slate-500/20'}>
              <span className={statusColors[result.status]?.text || 'text-slate-400'}>
                {result.status}
              </span>
            </Badge>
            {onClose && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="text-slate-400 hover:text-slate-100"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Query */}
            <div>
              <label className="text-sm font-medium text-slate-300 mb-1 block">Research Query</label>
              <p className="text-slate-100 bg-slate-900/50 p-3 rounded-lg">{result.query}</p>
            </div>

            {/* Timestamps */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-slate-300 mb-1 block">Created</label>
                <div className="flex items-center gap-2 text-slate-400">
                  <Clock className="h-4 w-4" />
                  <span>{new Date(result.created_at).toLocaleString()}</span>
                </div>
              </div>
              {result.completed_at && (
                <div>
                  <label className="text-sm font-medium text-slate-300 mb-1 block">Completed</label>
                  <div className="flex items-center gap-2 text-slate-400">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>{new Date(result.completed_at).toLocaleString()}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Error message if failed */}
            {result.error_message && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <div className="flex items-center gap-2 text-red-400 mb-2">
                  <AlertCircle className="h-5 w-5" />
                  <span className="font-medium">Error</span>
                </div>
                <p className="text-sm text-red-300">{result.error_message}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs defaultValue="answer" className="w-full">
        <TabsList className="bg-slate-800 border-slate-700">
          <TabsTrigger value="answer">Answer</TabsTrigger>
          <TabsTrigger value="knowledge">Knowledge Items</TabsTrigger>
          <TabsTrigger value="sources">Sources</TabsTrigger>
          <TabsTrigger value="stats">Statistics</TabsTrigger>
        </TabsList>

        {/* Answer Tab */}
        <TabsContent value="answer" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-slate-100">Research Answer</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyAnswer}
                  disabled={!result.answer}
                >
                  <Copy className="h-4 w-4 mr-2" />
                  Copy
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadReport}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {result.answer ? (
                <div className="prose prose-invert max-w-none">
                  <p className="text-slate-200 whitespace-pre-wrap">{result.answer}</p>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No answer available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Knowledge Items Tab */}
        <TabsContent value="knowledge" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Knowledge Items</CardTitle>
            </CardHeader>
            <CardContent>
              {result.knowledge_items && result.knowledge_items.length > 0 ? (
                <div className="space-y-4">
                  {result.knowledge_items.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-4 bg-slate-900/50 rounded-lg border border-slate-700"
                    >
                      {item.title && (
                        <h4 className="font-medium text-slate-100 mb-2">{item.title}</h4>
                      )}
                      {item.content && (
                        <p className="text-slate-300 text-sm mb-2">{item.content}</p>
                      )}
                      {item.url && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-emerald-400 hover:text-emerald-300 text-sm"
                        >
                          <ExternalLink className="h-4 w-4" />
                          {item.url}
                        </a>
                      )}
                      {item.relevance_score !== undefined && (
                        <div className="mt-2">
                          <Badge variant="outline" className="text-xs">
                            Relevance: {(item.relevance_score * 100).toFixed(1)}%
                          </Badge>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <List className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No knowledge items available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sources Tab */}
        <TabsContent value="sources" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Sources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Visited URLs */}
              {result.visited_urls && result.visited_urls.length > 0 && (
                <div>
                  <h4 className="font-medium text-slate-300 mb-3 flex items-center gap-2">
                    <Globe className="h-4 w-4" />
                    Visited URLs ({result.visited_urls.length})
                  </h4>
                  <div className="space-y-2">
                    {result.visited_urls.map((url, idx) => (
                      <a
                        key={idx}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 p-2 bg-slate-900/50 rounded hover:bg-slate-900 transition-colors"
                      >
                        <LinkIcon className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                        <span className="text-slate-300 text-sm truncate flex-1">{url}</span>
                        <ExternalLink className="h-4 w-4 text-slate-500 flex-shrink-0" />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Searched Queries */}
              {result.searched_queries && result.searched_queries.length > 0 && (
                <div>
                  <h4 className="font-medium text-slate-300 mb-3 flex items-center gap-2">
                    <Search className="h-4 w-4" />
                    Search Queries ({result.searched_queries.length})
                  </h4>
                  <div className="space-y-2">
                    {result.searched_queries.map((query, idx) => (
                      <div
                        key={idx}
                        className="p-2 bg-slate-900/50 rounded text-slate-300 text-sm"
                      >
                        {query}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {(!result.visited_urls || result.visited_urls.length === 0) &&
               (!result.searched_queries || result.searched_queries.length === 0) && (
                <div className="text-center py-8 text-slate-400">
                  <Globe className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No sources available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Statistics Tab */}
        <TabsContent value="stats" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              {result.token_usage ? (
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-4 bg-slate-900/50 rounded-lg">
                    <label className="text-sm text-slate-400 mb-1 block">Total Tokens</label>
                    <p className="text-2xl font-semibold text-slate-100">
                      {result.token_usage.total_tokens?.toLocaleString() || 'N/A'}
                    </p>
                  </div>
                  <div className="p-4 bg-slate-900/50 rounded-lg">
                    <label className="text-sm text-slate-400 mb-1 block">Prompt Tokens</label>
                    <p className="text-2xl font-semibold text-slate-100">
                      {result.token_usage.prompt_tokens?.toLocaleString() || 'N/A'}
                    </p>
                  </div>
                  <div className="p-4 bg-slate-900/50 rounded-lg">
                    <label className="text-sm text-slate-400 mb-1 block">Completion Tokens</label>
                    <p className="text-2xl font-semibold text-slate-100">
                      {result.token_usage.completion_tokens?.toLocaleString() || 'N/A'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No statistics available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
