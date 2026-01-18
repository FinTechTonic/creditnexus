/**
 * Agent Dashboard Component
 * 
 * Unified dashboard for viewing all agent results:
 * - DeepResearch results
 * - LangAlpha quantitative analysis results
 * - PeopleHub profile results
 * 
 * Features:
 * - Filter by agent type, status, deal
 * - Search and sort
 * - View detailed results
 * - Download reports
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Search,
  BarChart3,
  User,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  XCircle,
  FileText,
  Sparkles
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AgentResultCard } from '@/components/agent-results/AgentResultCard';
import type { AgentType } from '@/components/agent-results/AgentResultCard';
import { DeepResearchResultView } from '@/components/agent-results/DeepResearchResultView';
import { LangAlphaResultView } from '@/components/agent-results/LangAlphaResultView';
import { PeopleHubResultView } from '@/components/agent-results/PeopleHubResultView';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useToast } from '@/components/ui/toast';
import { SkeletonDocumentList } from '@/components/ui/skeleton';
import { DashboardChatbotPanel } from '@/components/DashboardChatbotPanel';

interface AgentResult {
  id: string;
  agentType: AgentType;
  title: string;
  query?: string;
  status: 'completed' | 'in_progress' | 'pending' | 'failed';
  timestamp: string;
  preview?: string;
  dealId?: number | null;
  // Type-specific IDs
  researchId?: string; // For DeepResearch
  analysisId?: string; // For LangAlpha
  profileId?: number; // For PeopleHub
}

export function AgentDashboard() {
  const [results, setResults] = useState<AgentResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<AgentType | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<'all' | 'completed' | 'in_progress' | 'pending' | 'failed'>('all');
  const [selectedResult, setSelectedResult] = useState<AgentResult | null>(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const { addToast } = useToast();

  // Fetch all agent results
  const fetchResults = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch from multiple endpoints
      const [deepResearchRes, langAlphaRes, peopleHubRes] = await Promise.allSettled([
        // DeepResearch - Note: API endpoint may need to be created for listing
        fetchWithAuth('/api/deep-research/results').catch(() => ({ ok: false })),
        // LangAlpha - Note: API endpoint may need to be created for listing
        fetchWithAuth('/api/quantitative-analysis/results').catch(() => ({ ok: false })),
        // PeopleHub - Note: API endpoint may need to be created for listing
        fetchWithAuth('/api/business-intelligence/individual-profiles').catch(() => ({ ok: false }))
      ]);

      const allResults: AgentResult[] = [];

      // Process DeepResearch results
      if (deepResearchRes.status === 'fulfilled' && deepResearchRes.value.ok && 'json' in deepResearchRes.value) {
        try {
          const data = await (deepResearchRes.value as Response).json();
          const items = Array.isArray(data) ? data : (data.results || data.items || []);
          items.forEach((item: any) => {
            allResults.push({
              id: item.research_id || item.id?.toString(),
              agentType: 'deepresearch',
              title: item.query || 'DeepResearch Query',
              query: item.query,
              status: item.status === 'completed' ? 'completed' : 
                     item.status === 'processing' ? 'in_progress' :
                     item.status === 'failed' ? 'failed' : 'pending',
              timestamp: item.created_at || new Date().toISOString(),
              preview: item.answer ? item.answer.substring(0, 200) : undefined,
              dealId: item.deal_id,
              researchId: item.research_id || item.id?.toString()
            });
          });
        } catch (e) {
          console.warn('Failed to parse DeepResearch results:', e);
        }
      }

      // Process LangAlpha results
      if (langAlphaRes.status === 'fulfilled' && langAlphaRes.value.ok && 'json' in langAlphaRes.value) {
        try {
          const data = await (langAlphaRes.value as Response).json();
          const items = Array.isArray(data) ? data : (data.results || data.items || []);
          items.forEach((item: any) => {
            const report = item.report || {};
            const structuredReport = report.structured_report || {};
            allResults.push({
              id: item.analysis_id || item.id?.toString(),
              agentType: 'langalpha',
              title: `${item.analysis_type || 'Analysis'} - ${item.query || 'Query'}`,
              query: item.query,
              status: item.status === 'completed' ? 'completed' :
                     item.status === 'in_progress' ? 'in_progress' :
                     item.status === 'failed' ? 'failed' : 'pending',
              timestamp: item.created_at || new Date().toISOString(),
              preview: structuredReport.executive_summary || report.report?.substring(0, 200) || undefined,
              dealId: item.deal_id,
              analysisId: item.analysis_id || item.id?.toString()
            });
          });
        } catch (e) {
          console.warn('Failed to parse LangAlpha results:', e);
        }
      }

      // Process PeopleHub results
      if (peopleHubRes.status === 'fulfilled' && peopleHubRes.value.ok && 'json' in peopleHubRes.value) {
        try {
          const data = await (peopleHubRes.value as Response).json();
          const items = Array.isArray(data) ? data : (data.results || data.items || []);
          items.forEach((item: any) => {
            const profileData = item.profile_data || {};
            allResults.push({
              id: item.id?.toString(),
              agentType: 'peoplehub',
              title: item.person_name || 'PeopleHub Profile',
              query: `Research profile for ${item.person_name}`,
              status: 'completed', // PeopleHub results are typically completed
              timestamp: item.created_at || item.updated_at || new Date().toISOString(),
              preview: profileData.research_report?.substring(0, 200) || undefined,
              dealId: item.deal_id,
              profileId: item.id
            });
          });
        } catch (e) {
          console.warn('Failed to parse PeopleHub results:', e);
        }
      }

      // Sort by timestamp (newest first)
      allResults.sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );

      setResults(allResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agent results');
      addToast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to load agent results',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  // Filter and search results
  const filteredResults = results.filter(result => {
    // Filter by type
    if (filterType !== 'all' && result.agentType !== filterType) {
      return false;
    }

    // Filter by status
    if (filterStatus !== 'all' && result.status !== filterStatus) {
      return false;
    }

    // Search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      return (
        result.title.toLowerCase().includes(query) ||
        result.query?.toLowerCase().includes(query) ||
        result.preview?.toLowerCase().includes(query)
      );
    }

    return true;
  });

  const handleViewResult = (result: AgentResult) => {
    setSelectedResult(result);
    setViewDialogOpen(true);
  };

  const handleCloseView = () => {
    setViewDialogOpen(false);
    setSelectedResult(null);
  };

  const handleDownloadResult = async (result: AgentResult) => {
    try {
      let endpoint = '';
      if (result.agentType === 'deepresearch' && result.researchId) {
        endpoint = `/api/deep-research/results/${result.researchId}`;
      } else if (result.agentType === 'langalpha' && result.analysisId) {
        endpoint = `/api/quantitative-analysis/results/${result.analysisId}`;
      } else if (result.agentType === 'peoplehub' && result.profileId) {
        endpoint = `/api/business-intelligence/individual-profile/${result.profileId}`;
      }

      if (!endpoint) {
        addToast({
          title: 'Error',
          description: 'Cannot download: missing result ID',
          variant: 'destructive'
        });
        return;
      }

      const response = await fetchWithAuth(endpoint);
      if (!response.ok) {
        throw new Error('Failed to fetch result for download');
      }

      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${result.agentType}_${result.id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      addToast({
        title: 'Downloaded',
        description: 'Result downloaded successfully',
        variant: 'default'
      });
    } catch (err) {
      addToast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to download result',
        variant: 'destructive'
      });
    }
  };

  // Statistics
  const stats = {
    total: results.length,
    deepresearch: results.filter(r => r.agentType === 'deepresearch').length,
    langalpha: results.filter(r => r.agentType === 'langalpha').length,
    peoplehub: results.filter(r => r.agentType === 'peoplehub').length,
    completed: results.filter(r => r.status === 'completed').length,
    in_progress: results.filter(r => r.status === 'in_progress').length,
    failed: results.filter(r => r.status === 'failed').length
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
            <Sparkles className="h-8 w-8 text-emerald-400" />
            Agent Dashboard
          </h1>
          <p className="text-slate-400 mt-1">
            View and manage all agent analysis results
          </p>
        </div>
        <Button
          variant="outline"
          onClick={fetchResults}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Total Results</p>
                <p className="text-2xl font-bold text-slate-100">{stats.total}</p>
              </div>
              <FileText className="h-8 w-8 text-emerald-400 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">DeepResearch</p>
                <p className="text-2xl font-bold text-slate-100">{stats.deepresearch}</p>
              </div>
              <Search className="h-8 w-8 text-blue-400 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">LangAlpha</p>
                <p className="text-2xl font-bold text-slate-100">{stats.langalpha}</p>
              </div>
              <BarChart3 className="h-8 w-8 text-purple-400 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">PeopleHub</p>
                <p className="text-2xl font-bold text-slate-100">{stats.peoplehub}</p>
              </div>
              <User className="h-8 w-8 text-amber-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search results..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-slate-900 border-slate-700 text-slate-100"
                />
              </div>
            </div>

            {/* Filter by Type */}
            <div className="flex gap-2">
              <Button
                variant={filterType === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterType('all')}
              >
                All Types
              </Button>
              <Button
                variant={filterType === 'deepresearch' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterType('deepresearch')}
              >
                <Search className="h-4 w-4 mr-2" />
                DeepResearch
              </Button>
              <Button
                variant={filterType === 'langalpha' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterType('langalpha')}
              >
                <BarChart3 className="h-4 w-4 mr-2" />
                LangAlpha
              </Button>
              <Button
                variant={filterType === 'peoplehub' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterType('peoplehub')}
              >
                <User className="h-4 w-4 mr-2" />
                PeopleHub
              </Button>
            </div>

            {/* Filter by Status */}
            <div className="flex gap-2">
              <Button
                variant={filterStatus === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterStatus('all')}
              >
                All Status
              </Button>
              <Button
                variant={filterStatus === 'completed' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterStatus('completed')}
              >
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Completed
              </Button>
              <Button
                variant={filterStatus === 'in_progress' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterStatus('in_progress')}
              >
                <Clock className="h-4 w-4 mr-2" />
                In Progress
              </Button>
              <Button
                variant={filterStatus === 'failed' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterStatus('failed')}
              >
                <XCircle className="h-4 w-4 mr-2" />
                Failed
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Grid */}
      {loading ? (
        <SkeletonDocumentList count={6} />
      ) : error ? (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6">
            <div className="flex flex-col items-center justify-center py-12">
              <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
              <p className="text-red-400 mb-2">Error loading results</p>
              <p className="text-slate-400 text-sm mb-4">{error}</p>
              <Button onClick={fetchResults} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : filteredResults.length === 0 ? (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6">
            <div className="flex flex-col items-center justify-center py-12">
              <FileText className="h-12 w-12 text-slate-500 mb-4" />
              <p className="text-slate-400">No results found</p>
              {searchQuery || filterType !== 'all' || filterStatus !== 'all' ? (
                <Button
                  onClick={() => {
                    setSearchQuery('');
                    setFilterType('all');
                    setFilterStatus('all');
                  }}
                  variant="outline"
                  className="mt-4"
                >
                  Clear Filters
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredResults.map((result) => (
            <AgentResultCard
              key={result.id}
              agentType={result.agentType}
              id={result.id}
              title={result.title}
              query={result.query}
              status={result.status}
              timestamp={result.timestamp}
              preview={result.preview}
              dealId={result.dealId}
              onView={() => handleViewResult(result)}
              onDownload={() => handleDownloadResult(result)}
            />
          ))}
        </div>
      )}

      {/* View Result Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto bg-slate-900 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-slate-100">
              {selectedResult?.title || 'View Result'}
            </DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            {selectedResult?.agentType === 'deepresearch' && selectedResult.researchId && (
              <DeepResearchResultView
                researchId={selectedResult.researchId}
                onClose={handleCloseView}
                dealId={selectedResult.dealId}
              />
            )}
            {selectedResult?.agentType === 'langalpha' && selectedResult.analysisId && (
              <LangAlphaResultView
                analysisId={selectedResult.analysisId}
                onClose={handleCloseView}
                dealId={selectedResult.dealId}
              />
            )}
            {selectedResult?.agentType === 'peoplehub' && selectedResult.profileId && (
              <PeopleHubResultView
                profileId={selectedResult.profileId}
                onClose={handleCloseView}
                dealId={selectedResult.dealId}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Chatbot Panel */}
      <div className="mt-6">
        <DashboardChatbotPanel />
      </div>
    </div>
  );
}
