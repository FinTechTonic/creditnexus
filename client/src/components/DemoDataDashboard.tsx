import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, FileText, BarChart3, Settings, RefreshCw, Play, Trash2, Loader2, Search, Filter, Eye, ChevronLeft, ChevronRight, AlertCircle, CheckCircle, Clock, Download, RotateCcw, Radio, Copy } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Progress } from './ui/progress';
import { useDemoData } from '@/hooks/useDemoData';
import { DealDetailModal } from './DealDetailModal';
import { DemoDealCard, type DemoDeal } from './DemoDealCard';
import { fetchWithAuth } from '@/context/AuthContext';
import { useFDC3, createAgreementContext, createDocumentContext, createPortfolioContext, type AgreementContext, type DocumentContext, type PortfolioContext } from '@/context/FDC3Context';
import { useToast } from '@/components/ui/toast';

interface DemoDataStats {
  total_deals: number;
  total_documents: number;
  total_applications: number;
  last_seeded_at: string | null;
}

interface SeedOptions {
  seed_users: boolean;
  seed_templates: boolean;
  seed_policies: boolean;
  seed_policy_templates: boolean;
  generate_deals: boolean;
  deal_count: number;
  dry_run: boolean;
}

interface SeedResult {
  stage: string;
  created: number;
  updated: number;
  errors: string[];
}

interface DemoDeal {
  id: number;
  deal_id: string;
  deal_type: string;
  status: string;
  borrower_name?: string;
  total_commitment?: number;
  currency?: string;
  created_at: string;
  deal_data?: {
    loan_amount?: number;
    interest_rate?: number;
  };
}

export function DemoDataDashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('seed');
  const [stats, setStats] = useState<DemoDataStats>({
    total_deals: 0,
    total_documents: 0,
    total_applications: 0,
    last_seeded_at: null
  });
  
  const [seedOptions, setSeedOptions] = useState<SeedOptions>({
    seed_users: true,
    seed_templates: true,
    seed_policies: true,
    seed_policy_templates: true,
    generate_deals: true,
    deal_count: 12,
    dry_run: false
  });
  
  const [seedResults, setSeedResults] = useState<Record<string, SeedResult>>({});
  const [userCredentials, setUserCredentials] = useState<Array<{email: string; password: string; role: string; display_name: string}>>([]);
  
  // Generated Deals state
  const [dealFilterStatus, setDealFilterStatus] = useState<string>('all');
  const [dealFilterType, setDealFilterType] = useState<string>('all');
  const [dealSearchQuery, setDealSearchQuery] = useState('');
  const [dealPage, setDealPage] = useState(1);
  const dealsPerPage = 10;
  
  // Use the useDemoData hook
  const {
    seedData,
    generateDeals,
    getSeedingStatus,
    resetDemoData,
    getGeneratedDeals,
    loading,
    error,
    seedingStatus,
    isPolling,
    startPolling,
    stopPolling,
  } = useDemoData();
  
  // FDC3 and Toast
  const { broadcast, broadcastOnChannel, isAvailable } = useFDC3();
  const { addToast } = useToast();
  
  // Fetch demo deals using the hook
  const fetchDeals = useCallback(async () => {
    try {
      const result = await getGeneratedDeals({
        page: dealPage,
        limit: dealsPerPage,
        status: dealFilterStatus,
        deal_type: dealFilterType,
        search: dealSearchQuery,
      });
      setStats(prev => ({
        ...prev,
        total_deals: result.total,
      }));
    } catch (err) {
      console.error('Failed to fetch deals:', err);
    }
  }, [getGeneratedDeals, dealFilterStatus, dealFilterType, dealSearchQuery, dealPage]);
  
  useEffect(() => {
    if (activeTab === 'deals') {
      fetchDeals();
    }
  }, [activeTab, fetchDeals]);
  
  const formatCurrency = (amount: number | undefined, currency: string = 'USD') => {
    if (!amount) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };
  
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };
  
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-slate-500/20 text-slate-300',
      submitted: 'bg-blue-500/20 text-blue-300',
      under_review: 'bg-yellow-500/20 text-yellow-300',
      approved: 'bg-green-500/20 text-green-300',
      rejected: 'bg-red-500/20 text-red-300',
      active: 'bg-emerald-500/20 text-emerald-300',
      closed: 'bg-slate-600/20 text-slate-400',
    };
    return colors[status] || 'bg-slate-500/20 text-slate-300';
  };
  
  // Fetch deals when tab is active or filters change
  const [deals, setDeals] = useState<DemoDeal[]>([]);
  const [dealTotal, setDealTotal] = useState(0);
  
  // Deal detail modal state
  const [selectedDeal, setSelectedDeal] = useState<DemoDeal | null>(null);
  const [isDealModalOpen, setIsDealModalOpen] = useState(false);
  
  // Documents state
  const [documents, setDocuments] = useState<any[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [documentSearchQuery, setDocumentSearchQuery] = useState('');
  const [documentWorkflowFilter, setDocumentWorkflowFilter] = useState<string>('all');
  const [documentPage, setDocumentPage] = useState(1);
  const [documentTotal, setDocumentTotal] = useState(0);
  const documentsPerPage = 20;
  
  // Fetch deals data
  useEffect(() => {
    const loadDeals = async () => {
      if (activeTab !== 'deals') return;
      
      try {
        const result = await getGeneratedDeals({
          page: dealPage,
          limit: dealsPerPage,
          status: dealFilterStatus !== 'all' ? dealFilterStatus : undefined,
          deal_type: dealFilterType !== 'all' ? dealFilterType : undefined,
          search: dealSearchQuery.trim() || undefined,
        });
        setDeals(result.deals);
        setDealTotal(result.total);
        setStats(prev => ({
          ...prev,
          total_deals: result.total,
        }));
      } catch (err) {
        console.error('Failed to load deals:', err);
      }
    };
    
    loadDeals();
  }, [activeTab, dealPage, dealFilterStatus, dealFilterType, dealSearchQuery, getGeneratedDeals]);
  
  const totalPages = Math.ceil(dealTotal / dealsPerPage);
  
  // Fetch documents when documents tab is active
  useEffect(() => {
    const loadDocuments = async () => {
      if (activeTab !== 'documents') return;
      
      setDocumentsLoading(true);
      setDocumentsError(null);
      
      try {
        const params = new URLSearchParams();
        params.append('limit', documentsPerPage.toString());
        params.append('offset', ((documentPage - 1) * documentsPerPage).toString());
        params.append('is_demo', 'true'); // Request only demo documents from API
        
        if (documentSearchQuery.trim()) {
          params.append('search', documentSearchQuery.trim());
        }
        
        const response = await fetchWithAuth(`/api/documents?${params.toString()}`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch documents');
        }
        
        const data = await response.json();
        
        // Filter by workflow state (is_demo filtering is now done by API)
        let filteredDocs = data.documents || [];
        
        // Filter by workflow state
        if (documentWorkflowFilter !== 'all') {
          filteredDocs = filteredDocs.filter((doc: any) => 
            doc.workflow_state === documentWorkflowFilter
          );
        }
        
        setDocuments(filteredDocs);
        setDocumentTotal(filteredDocs.length);
        setStats(prev => ({
          ...prev,
          total_documents: filteredDocs.length,
        }));
      } catch (err) {
        setDocumentsError(err instanceof Error ? err.message : 'Failed to load documents');
      } finally {
        setDocumentsLoading(false);
      }
    };
    
    loadDocuments();
  }, [activeTab, documentPage, documentSearchQuery, documentWorkflowFilter]);
  
  // Fetch seeding status when status tab is active
  useEffect(() => {
    if (activeTab === 'status') {
      getSeedingStatus();
      
      // Start polling if any stage is running
      const hasRunning = Object.values(seedingStatus).some(s => s.status === 'running');
      if (hasRunning && !isPolling) {
        startPolling();
      } else if (!hasRunning && isPolling) {
        stopPolling();
      }
    }
    
    return () => {
      if (activeTab !== 'status') {
        stopPolling();
      }
    };
  }, [activeTab, seedingStatus, isPolling, startPolling, stopPolling, getSeedingStatus]);
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'running':
        return <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-slate-400" />;
    }
  };
  
  const getStatusColorForCard = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'running':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'failed':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };
  
  // Handle seeding
  const handleStartSeeding = async () => {
    try {
      // Start polling for status updates
      startPolling();
      
      if (seedOptions.generate_deals) {
        // Generate deals separately
        await generateDeals(seedOptions.deal_count);
      }
      
      // Seed other data
      const result = await seedData({
        seed_users: seedOptions.seed_users,
        seed_templates: seedOptions.seed_templates,
        seed_policies: seedOptions.seed_policies,
        seed_policy_templates: seedOptions.seed_policy_templates,
        generate_deals: false, // Already handled above
        dry_run: seedOptions.dry_run,
      });
      
      // Store user credentials if available
      if (result.user_credentials && Array.isArray(result.user_credentials)) {
        setUserCredentials(result.user_credentials);
      }
      
      // Convert result to SeedResult format
      const results: Record<string, SeedResult> = {};
      Object.entries(result.created).forEach(([stage, count]) => {
        results[stage] = {
          stage,
          created: count,
          updated: result.updated[stage] || 0,
          errors: result.errors[stage] || [],
        };
      });
      setSeedResults(results);
      
      // Update stats
      setStats(prev => ({
        ...prev,
        last_seeded_at: new Date().toISOString(),
      }));
      
      // Refresh deals if on deals tab
      if (activeTab === 'deals') {
        const result = await getGeneratedDeals({
          page: dealPage,
          limit: dealsPerPage,
          status: dealFilterStatus !== 'all' ? dealFilterStatus : undefined,
          deal_type: dealFilterType !== 'all' ? dealFilterType : undefined,
          search: dealSearchQuery.trim() || undefined,
        });
        setDeals(result.deals);
        setDealTotal(result.total);
      }
    } catch (err) {
      console.error('Seeding failed:', err);
    } finally {
      // Stop polling after a delay to catch final status
      setTimeout(() => {
        stopPolling();
      }, 3000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Demo Data Management</h1>
          <p className="text-slate-400 mt-1">
            Seed and manage demo data for testing and demonstrations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try {
                // Broadcast portfolio context with all demo deals
                if (deals.length > 0) {
                  const portfolioContext: PortfolioContext = createPortfolioContext('demo-portfolio', {
                    name: 'Demo Portfolio',
                    agreementIds: deals.map(d => d.deal_id),
                    totalCommitment: {
                      amount: deals.reduce((sum, d) => sum + (d.total_commitment || d.deal_data?.loan_amount || 0), 0),
                      currency: deals[0]?.currency || 'USD'
                    },
                    agreementCount: deals.length
                  });
                  
                  await broadcast(portfolioContext);
                  await broadcastOnChannel('portfolio', portfolioContext);
                  
                  addToast(`Broadcasted ${deals.length} deals to FDC3 network`, 'success');
                } else {
                  addToast('No deals available to broadcast. Generate deals first.', 'warning');
                }
              } catch (err) {
                console.error('Broadcast failed:', err);
                addToast(`Broadcast failed: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
              }
            }}
            disabled={!isAvailable || deals.length === 0}
            title={!isAvailable ? 'FDC3 not available' : 'Broadcast portfolio to FDC3 network'}
          >
            <Radio className="w-4 h-4 mr-2" />
            Broadcast Portfolio
          </Button>
          <Button variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Total Deals</CardTitle>
            <FileText className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{stats.total_deals}</div>
            <p className="text-xs text-slate-500 mt-1">Generated deals</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Total Documents</CardTitle>
            <FileText className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{stats.total_documents}</div>
            <p className="text-xs text-slate-500 mt-1">Document records</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Applications</CardTitle>
            <Database className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{stats.total_applications}</div>
            <p className="text-xs text-slate-500 mt-1">Loan applications</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Last Seeded</CardTitle>
            <BarChart3 className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {stats.last_seeded_at ? 'Yes' : 'Never'}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {stats.last_seeded_at 
                ? new Date(stats.last_seeded_at).toLocaleDateString()
                : 'No data seeded yet'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>Demo Data Operations</CardTitle>
          <CardDescription>
            Manage demo data seeding, generation, and configuration
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="seed">
                <Database className="w-4 h-4 mr-2" />
                Seed Data
              </TabsTrigger>
              <TabsTrigger value="deals">
                <FileText className="w-4 h-4 mr-2" />
                Generated Deals
              </TabsTrigger>
              <TabsTrigger value="documents">
                <FileText className="w-4 h-4 mr-2" />
                Documents
              </TabsTrigger>
              <TabsTrigger value="status">
                <BarChart3 className="w-4 h-4 mr-2" />
                Status
              </TabsTrigger>
              <TabsTrigger value="settings">
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </TabsTrigger>
            </TabsList>

            <TabsContent value="seed" className="mt-6">
              <div className="space-y-6">
                {/* Seed Options */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-white">Seed Options</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={seedOptions.seed_users}
                        onChange={(e) => setSeedOptions({ ...seedOptions, seed_users: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Seed Users</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={seedOptions.seed_templates}
                        onChange={(e) => setSeedOptions({ ...seedOptions, seed_templates: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Seed Templates</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={seedOptions.seed_policies}
                        onChange={(e) => setSeedOptions({ ...seedOptions, seed_policies: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Seed Policies</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={seedOptions.seed_policy_templates}
                        onChange={(e) => setSeedOptions({ ...seedOptions, seed_policy_templates: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Seed Policy Templates</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={seedOptions.generate_deals}
                        onChange={(e) => setSeedOptions({ ...seedOptions, generate_deals: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Generate Deals</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={seedOptions.dry_run}
                        onChange={(e) => setSeedOptions({ ...seedOptions, dry_run: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Dry Run (Preview Only)</span>
                    </label>
                  </div>
                  
                  {seedOptions.generate_deals && (
                    <div className="flex items-center gap-4">
                      <label className="text-sm text-slate-300">Deal Count:</label>
                      <input
                        type="number"
                        min="1"
                        max="50"
                        value={seedOptions.deal_count}
                        onChange={(e) => setSeedOptions({ ...seedOptions, deal_count: parseInt(e.target.value) || 12 })}
                        className="w-24 px-3 py-1.5 rounded-lg border border-slate-600 bg-slate-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                  )}
                </div>

                {/* Progress Indicator */}
                {loading && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-slate-300">Seeding in progress...</span>
                      <span className="text-slate-400">
                        {Object.values(seedingStatus).length > 0
                          ? `${Math.round(
                              Object.values(seedingStatus).reduce((sum, s) => sum + s.progress, 0) /
                              Object.values(seedingStatus).length * 100
                            )}%`
                          : '0%'}
                      </span>
                    </div>
                    <Progress 
                      value={
                        Object.values(seedingStatus).length > 0
                          ? Object.values(seedingStatus).reduce((sum, s) => sum + s.progress, 0) /
                            Object.values(seedingStatus).length * 100
                          : 0
                      } 
                      className="h-2" 
                    />
                  </div>
                )}

                {/* Error Display */}
                {error && (
                  <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                    {error}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleStartSeeding}
                    disabled={loading}
                    className="bg-indigo-600 hover:bg-indigo-700"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Seeding...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-2" />
                        Start Seeding
                      </>
                    )}
                  </Button>
                  
                  <Button
                    variant="outline"
                    onClick={() => {
                      setSeedResults({});
                      setUserCredentials([]);
                    }}
                    disabled={loading}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Clear Results
                  </Button>
                  
                  <Button
                    variant="outline"
                    onClick={async () => {
                      try {
                        await resetDemoData();
                        setSeedResults({});
                        setStats(prev => ({
                          ...prev,
                          total_deals: 0,
                          last_seeded_at: null,
                        }));
                        if (activeTab === 'deals') {
                          fetchDeals();
                        }
                      } catch (err) {
                        console.error('Failed to reset demo data:', err);
                      }
                    }}
                    disabled={loading}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Reset All
                  </Button>
                </div>

                {/* Results Table */}
                {Object.keys(seedResults).length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-white">Seeding Results</h3>
                    <div className="border border-slate-700 rounded-lg overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-slate-800">
                          <tr>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Stage</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Created</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Updated</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Errors</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {Object.entries(seedResults).map(([stage, result]) => (
                            <tr key={stage} className="hover:bg-slate-800/50">
                              <td className="px-4 py-3 text-sm text-white capitalize">{stage.replace('_', ' ')}</td>
                              <td className="px-4 py-3 text-sm text-green-400">{result.created}</td>
                              <td className="px-4 py-3 text-sm text-blue-400">{result.updated}</td>
                              <td className="px-4 py-3 text-sm text-red-400">
                                {result.errors.length > 0 ? result.errors.length : 'None'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* User Credentials Display */}
                {userCredentials.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold text-white">Generated User Credentials</h3>
                    <div className="border border-slate-700 rounded-lg overflow-hidden bg-slate-800/50">
                      <div className="p-4">
                        <p className="text-sm text-slate-400 mb-4">
                          Use these credentials to log in to the application:
                        </p>
                        <div className="space-y-2">
                          {userCredentials.map((user, index) => (
                            <div
                              key={index}
                              className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg border border-slate-700"
                            >
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-sm font-medium text-white">{user.display_name}</span>
                                  <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                                    {user.role}
                                  </span>
                                </div>
                                <div className="flex items-center gap-4 text-sm">
                                  <div>
                                    <span className="text-slate-400">Email: </span>
                                    <span className="text-white font-mono">{user.email}</span>
                                  </div>
                                  <div>
                                    <span className="text-slate-400">Password: </span>
                                    <span className="text-emerald-400 font-mono">{user.password}</span>
                                  </div>
                                </div>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const text = `Email: ${user.email}\nPassword: ${user.password}`;
                                  navigator.clipboard.writeText(text);
                                  addToast('Credentials copied to clipboard', 'success');
                                }}
                                className="text-slate-400 hover:text-white"
                                title="Copy credentials"
                              >
                                <Copy className="w-4 h-4" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="deals" className="mt-6">
              <div className="space-y-4">
                {/* Filters */}
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search by Deal ID or Borrower..."
                      value={dealSearchQuery}
                      onChange={(e) => {
                        setDealSearchQuery(e.target.value);
                        setDealPage(1);
                      }}
                      className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-slate-400" />
                    <select
                      value={dealFilterStatus}
                      onChange={(e) => {
                        setDealFilterStatus(e.target.value);
                        setDealPage(1);
                      }}
                      className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="all">All Status</option>
                      <option value="draft">Draft</option>
                      <option value="submitted">Submitted</option>
                      <option value="under_review">Under Review</option>
                      <option value="approved">Approved</option>
                      <option value="rejected">Rejected</option>
                      <option value="active">Active</option>
                      <option value="closed">Closed</option>
                    </select>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <select
                      value={dealFilterType}
                      onChange={(e) => {
                        setDealFilterType(e.target.value);
                        setDealPage(1);
                      }}
                      className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="all">All Types</option>
                      <option value="loan_application">Loan Application</option>
                      <option value="refinancing">Refinancing</option>
                      <option value="restructuring">Restructuring</option>
                    </select>
                  </div>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      try {
                        const result = await getGeneratedDeals({
                          page: dealPage,
                          limit: dealsPerPage,
                          status: dealFilterStatus !== 'all' ? dealFilterStatus : undefined,
                          deal_type: dealFilterType !== 'all' ? dealFilterType : undefined,
                          search: dealSearchQuery.trim() || undefined,
                        });
                        setDeals(result.deals);
                        setDealTotal(result.total);
                      } catch (err) {
                        console.error('Failed to refresh deals:', err);
                      }
                    }}
                    disabled={loading}
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                </div>

                {/* Deals Table */}
                {loading ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
                  </div>
                ) : error ? (
                  <div className="text-center py-8 text-red-400">{error}</div>
                ) : deals.length === 0 ? (
                  <div className="text-center py-8 text-slate-400">
                    No demo deals found. Generate deals using the Seed Data tab.
                  </div>
                ) : (
                  <>
                    <div className="border border-slate-700 rounded-lg overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-slate-800">
                          <tr>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Deal ID</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Type</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Status</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Borrower</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Amount</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Date</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {deals.map((deal) => (
                            <tr key={deal.id} className="hover:bg-slate-800/50">
                              <td className="px-4 py-3 text-sm font-mono text-white">{deal.deal_id}</td>
                              <td className="px-4 py-3 text-sm text-slate-300 capitalize">
                                {deal.deal_type?.replace('_', ' ') || 'N/A'}
                              </td>
                              <td className="px-4 py-3">
                                <span className={`text-xs px-2 py-1 rounded ${getStatusColor(deal.status)}`}>
                                  {deal.status?.replace('_', ' ') || 'N/A'}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm text-slate-300">
                                {deal.borrower_name || 'N/A'}
                              </td>
                              <td className="px-4 py-3 text-sm text-white">
                                {formatCurrency(
                                  deal.total_commitment || deal.deal_data?.loan_amount,
                                  deal.currency
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm text-slate-400">
                                {formatDate(deal.created_at)}
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex items-center gap-1">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      setSelectedDeal(deal);
                                      setIsDealModalOpen(true);
                                    }}
                                    title="View Deal Details"
                                  >
                                    <Eye className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={async () => {
                                      try {
                                        // Fetch full deal data with CDM
                                        const response = await fetchWithAuth(`/api/deals/${deal.id}`);
                                        if (response.ok) {
                                          const data = await response.json();
                                          const dealData = data.deal;
                                          
                                          // Create AgreementContext for FDC3
                                          const agreementContext: AgreementContext = createAgreementContext(
                                            deal.deal_id,
                                            {
                                              name: deal.deal_id,
                                              borrower: deal.borrower_name,
                                              agreementDate: deal.created_at,
                                              totalCommitment: deal.total_commitment || deal.deal_data?.loan_amount
                                                ? {
                                                    amount: deal.total_commitment || deal.deal_data?.loan_amount || 0,
                                                    currency: deal.currency || 'USD'
                                                  }
                                                : undefined,
                                              workflowStatus: deal.status as any,
                                              parties: dealData?.deal_data?.parties?.map((p: any) => ({
                                                id: p.lei || p.id || '',
                                                name: p.name || '',
                                                role: p.role || '',
                                                lei: p.lei
                                              })) || [],
                                              facilities: dealData?.deal_data?.facilities?.map((f: any) => ({
                                                facility_name: f.facility_name || f.name || '',
                                                commitment_amount: {
                                                  amount: f.commitment_amount?.amount || f.amount || 0,
                                                  currency: f.commitment_amount?.currency || deal.currency || 'USD'
                                                },
                                                interest_terms: f.interest_terms || {
                                                  rate_option: {
                                                    benchmark: 'SOFR',
                                                    spread_bps: 250
                                                  },
                                                  payment_frequency: {
                                                    period: 'Monthly',
                                                    period_multiplier: 1
                                                  }
                                                },
                                                maturity_date: f.maturity_date || new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString()
                                              })) || []
                                            }
                                          );
                                          
                                          await broadcast(agreementContext);
                                          await broadcastOnChannel('portfolio', agreementContext);
                                          
                                          addToast(`Broadcasted ${deal.deal_id} to FDC3 network`, 'success');
                                        }
                                      } catch (err) {
                                        console.error('Broadcast failed:', err);
                                        addToast(`Broadcast failed: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
                                      }
                                    }}
                                    disabled={!isAvailable}
                                    title={!isAvailable ? 'FDC3 not available' : 'Broadcast deal to FDC3 network'}
                                  >
                                    <Radio className="w-4 h-4" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-between">
                        <div className="text-sm text-slate-400">
                          Showing {(dealPage - 1) * dealsPerPage + 1} to {Math.min(dealPage * dealsPerPage, dealTotal)} of {dealTotal} deals
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setDealPage(p => Math.max(1, p - 1))}
                            disabled={dealPage === 1}
                          >
                            <ChevronLeft className="w-4 h-4" />
                            Previous
                          </Button>
                          <div className="text-sm text-slate-300">
                            Page {dealPage} of {totalPages}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setDealPage(p => Math.min(totalPages, p + 1))}
                            disabled={dealPage === totalPages}
                          >
                            Next
                            <ChevronRight className="w-4 h-4 ml-1" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </TabsContent>

            <TabsContent value="documents" className="mt-6">
              <div className="space-y-4">
                {/* Filters */}
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search by title or borrower..."
                      value={documentSearchQuery}
                      onChange={(e) => {
                        setDocumentSearchQuery(e.target.value);
                        setDocumentPage(1);
                      }}
                      className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-slate-400" />
                    <select
                      value={documentWorkflowFilter}
                      onChange={(e) => {
                        setDocumentWorkflowFilter(e.target.value);
                        setDocumentPage(1);
                      }}
                      className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="all">All Workflows</option>
                      <option value="pending">Pending</option>
                      <option value="in_progress">In Progress</option>
                      <option value="completed">Completed</option>
                      <option value="rejected">Rejected</option>
                    </select>
                  </div>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const loadDocuments = async () => {
                        setDocumentsLoading(true);
                        try {
                          const params = new URLSearchParams();
                          params.append('limit', documentsPerPage.toString());
                          params.append('offset', ((documentPage - 1) * documentsPerPage).toString());
                          if (documentSearchQuery.trim()) {
                            params.append('search', documentSearchQuery.trim());
                          }
                          const response = await fetchWithAuth(`/api/documents?${params.toString()}`);
                          if (response.ok) {
                            const data = await response.json();
                            let filteredDocs = data.documents?.filter((doc: any) => doc.is_demo === true) || [];
                            if (documentWorkflowFilter !== 'all') {
                              filteredDocs = filteredDocs.filter((doc: any) => 
                                doc.workflow_state === documentWorkflowFilter
                              );
                            }
                            setDocuments(filteredDocs);
                            setDocumentTotal(filteredDocs.length);
                          }
                        } catch (err) {
                          console.error('Failed to refresh documents:', err);
                        } finally {
                          setDocumentsLoading(false);
                        }
                      };
                      loadDocuments();
                    }}
                    disabled={documentsLoading}
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${documentsLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                </div>

                {/* Documents Table */}
                {documentsLoading ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
                  </div>
                ) : documentsError ? (
                  <div className="text-center py-8 text-red-400">{documentsError}</div>
                ) : documents.length === 0 ? (
                  <div className="text-center py-8 text-slate-400">
                    No demo documents found. Generate documents using the Seed Data tab.
                  </div>
                ) : (
                  <>
                    <div className="border border-slate-700 rounded-lg overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-slate-800">
                          <tr>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Title</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Borrower</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Workflow State</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Created</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {documents.map((doc) => (
                            <tr key={doc.id} className="hover:bg-slate-800/50">
                              <td className="px-4 py-3 text-sm text-white">{doc.title || 'Untitled'}</td>
                              <td className="px-4 py-3 text-sm text-slate-300">
                                {doc.borrower_name || 'N/A'}
                              </td>
                              <td className="px-4 py-3">
                                <span className={`text-xs px-2 py-1 rounded ${
                                  doc.workflow_state === 'completed' 
                                    ? 'bg-green-500/20 text-green-300'
                                    : doc.workflow_state === 'in_progress'
                                    ? 'bg-blue-500/20 text-blue-300'
                                    : doc.workflow_state === 'rejected'
                                    ? 'bg-red-500/20 text-red-300'
                                    : 'bg-yellow-500/20 text-yellow-300'
                                }`}>
                                  {doc.workflow_state?.replace('_', ' ') || 'N/A'}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm text-slate-400">
                                {formatDate(doc.created_at)}
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex items-center gap-2">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      // Navigate to document parser with document ID
                                      navigate(`/app/document-parser?documentId=${doc.id}`);
                                    }}
                                    title="View/Edit Document Extraction"
                                  >
                                    <Eye className="w-4 h-4" />
                                  </Button>
                                  {doc.has_cdm_data && (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => {
                                        // Navigate to verification demo with document ID
                                        navigate(`/app/verification-demo?documentId=${doc.id}`);
                                      }}
                                      title="Verify Document"
                                    >
                                      <CheckCircle className="w-4 h-4" />
                                    </Button>
                                  )}
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={async () => {
                                      try {
                                        // Fetch document content
                                        const response = await fetchWithAuth(`/api/documents/${doc.id}`);
                                        if (response.ok) {
                                          const data = await response.json();
                                          const document = data.document;
                                          
                                          // Get document text from latest version or extracted_text
                                          let content = '';
                                          if (document.latest_version?.extracted_text) {
                                            content = document.latest_version.extracted_text;
                                          } else if (document.extracted_text) {
                                            content = document.extracted_text;
                                          } else {
                                            content = JSON.stringify(document.extracted_data || {}, null, 2);
                                          }
                                          
                                          // Create DocumentContext for FDC3
                                          const documentContext: DocumentContext = createDocumentContext(
                                            content,
                                            doc.id.toString(),
                                            doc.title || 'Untitled Document'
                                          );
                                          
                                          await broadcast(documentContext);
                                          await broadcastOnChannel('extraction', documentContext);
                                          
                                          addToast(`Broadcasted document "${doc.title || 'Untitled'}" to FDC3 network`, 'success');
                                        }
                                      } catch (err) {
                                        console.error('Broadcast failed:', err);
                                        addToast(`Broadcast failed: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
                                      }
                                    }}
                                    disabled={!isAvailable}
                                    title={!isAvailable ? 'FDC3 not available' : 'Broadcast document to FDC3 network'}
                                  >
                                    <Radio className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={async () => {
                                      try {
                                        const response = await fetchWithAuth(`/api/documents/${doc.id}/export?format=json`);
                                        if (response.ok) {
                                          const blob = await response.blob();
                                          const url = window.URL.createObjectURL(blob);
                                          const a = document.createElement('a');
                                          a.href = url;
                                          a.download = `${doc.title || 'document'}-${doc.id}.json`;
                                          document.body.appendChild(a);
                                          a.click();
                                          window.URL.revokeObjectURL(url);
                                          document.body.removeChild(a);
                                        }
                                      } catch (err) {
                                        console.error('Failed to download document:', err);
                                      }
                                    }}
                                    title="Download Document"
                                  >
                                    <Download className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={async () => {
                                      try {
                                        const formData = new FormData();
                                        formData.append('document_id', doc.id.toString());
                                        const response = await fetchWithAuth('/api/documents/re-extract', {
                                          method: 'POST',
                                          body: formData
                                        });
                                        if (response.ok) {
                                          // Refresh documents list
                                          const params = new URLSearchParams();
                                          params.append('limit', documentsPerPage.toString());
                                          params.append('offset', ((documentPage - 1) * documentsPerPage).toString());
                                          if (documentSearchQuery.trim()) {
                                            params.append('search', documentSearchQuery.trim());
                                          }
                                          const refreshResponse = await fetchWithAuth(`/api/documents?${params.toString()}`);
                                          if (refreshResponse.ok) {
                                            const data = await refreshResponse.json();
                                            let filteredDocs = data.documents?.filter((d: any) => d.is_demo === true) || [];
                                            if (documentWorkflowFilter !== 'all') {
                                              filteredDocs = filteredDocs.filter((d: any) => 
                                                d.workflow_state === documentWorkflowFilter
                                              );
                                            }
                                            setDocuments(filteredDocs);
                                          }
                                        }
                                      } catch (err) {
                                        console.error('Failed to regenerate document:', err);
                                      }
                                    }}
                                    title="Regenerate Document"
                                  >
                                    <RotateCcw className="w-4 h-4" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination */}
                    {Math.ceil(documentTotal / documentsPerPage) > 1 && (
                      <div className="flex items-center justify-between">
                        <div className="text-sm text-slate-400">
                          Showing {(documentPage - 1) * documentsPerPage + 1} to {Math.min(documentPage * documentsPerPage, documentTotal)} of {documentTotal} documents
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setDocumentPage(p => Math.max(1, p - 1))}
                            disabled={documentPage === 1}
                          >
                            <ChevronLeft className="w-4 h-4" />
                            Previous
                          </Button>
                          <div className="text-sm text-slate-300">
                            Page {documentPage} of {Math.ceil(documentTotal / documentsPerPage)}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setDocumentPage(p => Math.min(Math.ceil(documentTotal / documentsPerPage), p + 1))}
                            disabled={documentPage >= Math.ceil(documentTotal / documentsPerPage)}
                          >
                            Next
                            <ChevronRight className="w-4 h-4 ml-1" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </TabsContent>

            <TabsContent value="status" className="mt-6">
              <div className="space-y-6">
                {/* Header with refresh */}
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-white">Seeding Status</h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => getSeedingStatus()}
                    disabled={loading}
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                </div>

                {/* Status Cards */}
                {Object.keys(seedingStatus).length === 0 ? (
                  <div className="text-center py-8 text-slate-400">
                    No seeding operations found. Start seeding from the Seed Data tab.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.entries(seedingStatus).map(([stage, status]) => (
                      <Card key={stage} className={`border ${getStatusColorForCard(status.status).split(' ')[2]}`}>
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              {getStatusIcon(status.status)}
                              <div>
                                <CardTitle className="text-base capitalize">
                                  {stage.replace('_', ' ')}
                                </CardTitle>
                                <CardDescription className="text-xs mt-1">
                                  {status.status === 'running' && status.total > 0
                                    ? `Processing ${status.current} of ${status.total} items`
                                    : status.status === 'completed'
                                    ? `Completed ${status.total} items`
                                    : status.status}
                                </CardDescription>
                              </div>
                            </div>
                            <span className={`text-xs px-2 py-1 rounded border ${getStatusColorForCard(status.status)}`}>
                              {status.status.toUpperCase()}
                            </span>
                          </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          {/* Progress Bar */}
                          {status.total > 0 && (
                            <div className="space-y-2">
                              <div className="flex items-center justify-between text-sm">
                                <span className="text-slate-400">Progress</span>
                                <span className="text-slate-300">
                                  {Math.round(status.progress * 100)}% ({status.current}/{status.total})
                                </span>
                              </div>
                              <Progress value={status.progress * 100} className="h-2" />
                            </div>
                          )}

                          {/* Timestamps */}
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            {status.started_at && (
                              <div>
                                <span className="text-slate-500">Started:</span>
                                <span className="text-slate-300 ml-2">
                                  {new Date(status.started_at).toLocaleString()}
                                </span>
                              </div>
                            )}
                            {status.completed_at && (
                              <div>
                                <span className="text-slate-500">Completed:</span>
                                <span className="text-slate-300 ml-2">
                                  {new Date(status.completed_at).toLocaleString()}
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Error Log */}
                          {status.errors && status.errors.length > 0 && (
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm font-medium text-red-400">
                                <AlertCircle className="w-4 h-4" />
                                Errors ({status.errors.length})
                              </div>
                              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 max-h-48 overflow-y-auto">
                                <ul className="space-y-1 text-xs text-red-300">
                                  {status.errors.map((error, idx) => (
                                    <li key={idx} className="font-mono">• {error}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}

                {/* Last Seeded Info */}
                {stats.last_seeded_at && (
                  <Card className="bg-slate-800/50">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3">
                        <Clock className="w-5 h-5 text-slate-400" />
                        <div>
                          <p className="text-sm font-medium text-white">Last Seeded</p>
                          <p className="text-xs text-slate-400">
                            {new Date(stats.last_seeded_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>

            <TabsContent value="settings" className="mt-6">
              <div className="space-y-6">
                {/* Deal Generation Settings */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-white">Deal Generation Settings</h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Default Deal Count
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="50"
                        value={seedOptions.deal_count}
                        onChange={(e) => setSeedOptions({ ...seedOptions, deal_count: parseInt(e.target.value) || 12 })}
                        className="w-full px-3 py-2 rounded-lg border border-slate-600 bg-slate-800 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <p className="text-xs text-slate-500 mt-1">Number of deals to generate (1-50)</p>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Deal Types
                      </label>
                      <div className="space-y-2">
                        {['loan_application', 'refinancing', 'restructuring'].map((type) => (
                          <label key={type} className="flex items-center space-x-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={true} // TODO: Add state for selected deal types
                              onChange={() => {}}
                              className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                            />
                            <span className="text-sm text-slate-300 capitalize">{type.replace('_', ' ')}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Document Generation Options */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-white">Document Generation Options</h3>
                  
                  <div className="space-y-3">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={true} // TODO: Add state
                        onChange={() => {}}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Generate documents from templates</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={true} // TODO: Add state
                        onChange={() => {}}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Create document revision history</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={true} // TODO: Add state
                        onChange={() => {}}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Generate deal notes</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={true} // TODO: Add state
                        onChange={() => {}}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-slate-300">Create policy decisions</span>
                    </label>
                  </div>
                </div>

                {/* Cache Management */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-white">Cache Management</h3>
                  
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                      <div>
                        <p className="text-sm font-medium text-white">Cache Status</p>
                        <p className="text-xs text-slate-400">CDM data and deal scenarios</p>
                      </div>
                      <span className="text-sm text-green-400">Enabled</span>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        onClick={() => {
                          // TODO: Clear cache
                          console.log('Clear cache');
                        }}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Clear Cache
                      </Button>
                      
                      <Button
                        variant="outline"
                        onClick={() => {
                          // TODO: Get cache stats
                          console.log('Get cache stats');
                        }}
                      >
                        <BarChart3 className="w-4 h-4 mr-2" />
                        View Cache Stats
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Storage Settings */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-white">Storage Settings</h3>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                      <span className="text-sm text-slate-300">Storage Path</span>
                      <span className="text-sm font-mono text-slate-400">storage/deals/demo</span>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                      <span className="text-sm text-slate-300">ChromaDB Indexing</span>
                      <span className="text-sm text-green-400">Enabled</span>
                    </div>
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Deal Detail Modal */}
      <DealDetailModal
        deal={selectedDeal}
        open={isDealModalOpen}
        onClose={() => {
          setIsDealModalOpen(false);
          setSelectedDeal(null);
        }}
        onViewDocument={(documentId) => {
          navigate(`/dashboard/documents/${documentId}`);
        }}
        onDownloadDocument={(documentId) => {
          // TODO: Download document
          console.log('Download document:', documentId);
        }}
      />
    </div>
  );
}
