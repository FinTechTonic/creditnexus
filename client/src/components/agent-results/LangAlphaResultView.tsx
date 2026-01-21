/**
 * LangAlpha Result View Component
 *
 * Displays LangAlpha quantitative analysis results with:
 * - Executive summary, key findings, metrics, trading signals, policy evaluation.
 * FDC3: broadcasts finos.creditnexus.agentResult when result is loaded so Trading/Stock
 * Prediction can focus on mentioned symbols.
 */

import { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  AlertCircle,
  Loader2,
  Copy,
  Download,
  X,
  FileText,
  Target,
  DollarSign,
  Activity
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useFDC3 } from '@/context/FDC3Context';
import { createAgentResultContext } from '@/context/FDC3Context';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/components/ui/toast';

interface LangAlphaResult {
  id: number;
  analysis_id: string;
  analysis_type: string;
  query: string;
  report: {
    report?: string;
    structured_report?: {
      executive_summary?: string;
      key_findings?: string[];
      metrics?: Record<string, unknown>;
      recommendations?: string[];
      risk_assessment?: Record<string, unknown>;
      data_sources?: string[];
    };
    cdm_event?: unknown;
  } | null;
  market_data: Record<string, unknown> | null;
  fundamental_data: Record<string, unknown> | null;
  status: string;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  deal_id: number | null;
}

interface LangAlphaResultViewProps {
  analysisId: string;
  onClose?: () => void;
  dealId?: number | null;
}

export function LangAlphaResultView({
  analysisId,
  onClose,
  dealId: _dealId // Prefix with _ - unused
}: LangAlphaResultViewProps) {
  const { broadcast } = useFDC3();
  const [result, setResult] = useState<LangAlphaResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { addToast } = useToast();

  useEffect(() => {
    if (!result) return;
    const at = result.analysis_type?.toLowerCase() ?? '';
    const agentType: 'langalpha' | 'deep_research' | 'peoplehub' =
      at.includes('deep') || at.includes('research') ? 'deep_research'
      : at.includes('people') ? 'peoplehub'
      : 'langalpha';
    const md = result.market_data as Record<string, unknown> | null;
    const symbols: string[] = Array.isArray((result.report as { structured_report?: { metrics?: { symbols?: string[]; tickers?: string[] } } })?.structured_report?.metrics?.symbols)
      ? ((result.report as { structured_report?: { metrics?: { symbols?: string[] } } }).structured_report!.metrics!.symbols!)
      : Array.isArray((result.report as { structured_report?: { metrics?: { tickers?: string[] } } })?.structured_report?.metrics?.tickers)
        ? ((result.report as { structured_report?: { metrics?: { tickers?: string[] } } }).structured_report!.metrics!.tickers!)
        : md && typeof md === 'object' ? (Object.keys(md).filter((k) => typeof k === 'string' && k.length <= 6) as string[]) : [];
    const recs = (result.report as { structured_report?: { recommendations?: string[] } })?.structured_report?.recommendations;
    const summary = (result.report as { structured_report?: { executive_summary?: string }; report?: string })?.structured_report?.executive_summary
      ?? (typeof (result.report as { report?: string })?.report === 'string' ? ((result.report as { report: string }).report.slice(0, 500)) : undefined);
    try {
      broadcast(createAgentResultContext(result.analysis_id, agentType, {
        query: result.query,
        summary: summary ?? undefined,
        symbols: symbols.length ? symbols : undefined,
        recommendations: Array.isArray(recs) ? recs : undefined,
        deal_id: result.deal_id ?? undefined,
      }));
    } catch {
      // ignore FDC3 broadcast errors
    }
  }, [result, broadcast]);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetchWithAuth(`/api/quantitative-analysis/results/${analysisId}`);
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: 'Failed to load result' }));
          throw new Error(errorData.detail?.message || errorData.message || 'Failed to load result');
        }
        
        const data = await response.json();
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analysis result');
        addToast({
          title: 'Error',
          description: err instanceof Error ? err.message : 'Failed to load analysis result',
          variant: 'destructive'
        });
      } finally {
        setLoading(false);
      }
    };
    
    fetchResult();
  }, [analysisId, addToast]);

  const handleCopyReport = () => {
    if (result?.report?.report) {
      navigator.clipboard.writeText(result.report.report);
      addToast({
        title: 'Copied',
        description: 'Report copied to clipboard',
        variant: 'default'
      });
    }
  };

  const handleDownloadReport = () => {
    if (!result) return;
    
    const report = {
      analysis_id: result.analysis_id,
      analysis_type: result.analysis_type,
      query: result.query,
      report: result.report,
      market_data: result.market_data,
      fundamental_data: result.fundamental_data,
      created_at: result.created_at,
      completed_at: result.completed_at
    };
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `langalpha_${result.analysis_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    addToast({
      title: 'Downloaded',
      description: 'Analysis report downloaded',
      variant: 'default'
    });
  };

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-emerald-500 mb-4" />
            <p className="text-slate-400">Loading analysis result...</p>
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

  const structuredReport = result.report?.structured_report;
  const statusColors: Record<string, { bg: string; text: string }> = {
    completed: { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
    in_progress: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
    pending: { bg: 'bg-amber-500/20', text: 'text-amber-400' },
    failed: { bg: 'bg-red-500/20', text: 'text-red-400' }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-3">
            <BarChart3 className="h-6 w-6 text-emerald-400" />
            <div>
              <CardTitle className="text-slate-100">LangAlpha Analysis</CardTitle>
              <p className="text-sm text-slate-400 mt-1">
                {result.analysis_type.charAt(0).toUpperCase() + result.analysis_type.slice(1)} Analysis
                {' • '}
                ID: {result.analysis_id}
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
              <label className="text-sm font-medium text-slate-300 mb-1 block">Analysis Query</label>
              <p className="text-slate-100 bg-slate-900/50 p-3 rounded-lg">{result.query}</p>
            </div>

            {/* Timestamps */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-slate-300 mb-1 block">Created</label>
                <p className="text-slate-400 text-sm">
                  {new Date(result.created_at).toLocaleString()}
                </p>
              </div>
              {result.completed_at && (
                <div>
                  <label className="text-sm font-medium text-slate-300 mb-1 block">Completed</label>
                  <p className="text-slate-400 text-sm">
                    {new Date(result.completed_at).toLocaleString()}
                  </p>
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
      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="bg-slate-800 border-slate-700">
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="findings">Key Findings</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="data">Data</TabsTrigger>
          <TabsTrigger value="full">Full Report</TabsTrigger>
        </TabsList>

        {/* Executive Summary Tab */}
        <TabsContent value="summary" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-slate-100">Executive Summary</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyReport}
                  disabled={!result.report?.report}
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
              {structuredReport?.executive_summary ? (
                <div className="prose prose-invert max-w-none">
                  <p className="text-slate-200 whitespace-pre-wrap">
                    {structuredReport.executive_summary}
                  </p>
                </div>
              ) : result.report?.report ? (
                <div className="prose prose-invert max-w-none">
                  <p className="text-slate-200 whitespace-pre-wrap">
                    {result.report.report.substring(0, 1000)}
                    {result.report.report.length > 1000 && '...'}
                  </p>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No summary available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Key Findings Tab */}
        <TabsContent value="findings" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Key Findings</CardTitle>
            </CardHeader>
            <CardContent>
              {structuredReport?.key_findings && structuredReport.key_findings.length > 0 ? (
                <div className="space-y-3">
                  {structuredReport.key_findings.map((finding, idx) => (
                    <div
                      key={idx}
                      className="p-4 bg-slate-900/50 rounded-lg border border-slate-700 flex items-start gap-3"
                    >
                      <Target className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <p className="text-slate-200 flex-1">{finding}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <Target className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No key findings available</p>
                </div>
              )}

              {/* Recommendations */}
              {structuredReport?.recommendations && structuredReport.recommendations.length > 0 && (
                <div className="mt-6">
                  <h4 className="font-medium text-slate-300 mb-3">Recommendations</h4>
                  <div className="space-y-2">
                    {structuredReport.recommendations.map((rec, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-slate-900/50 rounded-lg border border-slate-700"
                      >
                        <p className="text-slate-200 text-sm">{rec}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Metrics Tab */}
        <TabsContent value="metrics" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              {structuredReport?.metrics && Object.keys(structuredReport.metrics).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(structuredReport.metrics).map(([key, value]) => (
                    <div key={key} className="p-4 bg-slate-900/50 rounded-lg">
                      <h4 className="font-medium text-slate-300 mb-2 capitalize">
                        {key.replace(/_/g, ' ')}
                      </h4>
                      <pre className="text-sm text-slate-200 overflow-auto">
                        {JSON.stringify(value, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No metrics available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Data Tab */}
        <TabsContent value="data" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Market & Fundamental Data</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="market" className="w-full">
                <TabsList className="bg-slate-900 border-slate-700">
                  <TabsTrigger value="market">Market Data</TabsTrigger>
                  <TabsTrigger value="fundamental">Fundamental Data</TabsTrigger>
                </TabsList>

                <TabsContent value="market" className="mt-4">
                  {result.market_data && Object.keys(result.market_data).length > 0 ? (
                    <div className="p-4 bg-slate-900/50 rounded-lg">
                      <pre className="text-sm text-slate-200 overflow-auto">
                        {JSON.stringify(result.market_data, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-slate-400">
                      <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No market data available</p>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="fundamental" className="mt-4">
                  {result.fundamental_data && Object.keys(result.fundamental_data).length > 0 ? (
                    <div className="p-4 bg-slate-900/50 rounded-lg">
                      <pre className="text-sm text-slate-200 overflow-auto">
                        {JSON.stringify(result.fundamental_data, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-slate-400">
                      <DollarSign className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No fundamental data available</p>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Full Report Tab */}
        <TabsContent value="full" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Full Report</CardTitle>
            </CardHeader>
            <CardContent>
              {result.report?.report ? (
                <div className="prose prose-invert max-w-none">
                  <pre className="text-slate-200 whitespace-pre-wrap text-sm bg-slate-900/50 p-4 rounded-lg overflow-auto max-h-[600px]">
                    {result.report.report}
                  </pre>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No full report available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
