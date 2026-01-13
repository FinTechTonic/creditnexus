import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth, fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft,
  Building2,
  DollarSign,
  Calendar,
  Shield,
  FileText,
  TrendingUp,
  Users,
  Wallet,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Eye,
  CreditCard,
  BarChart3
} from 'lucide-react';

interface PoolDetails {
  pool: {
    id: number;
    pool_id: string;
    pool_name: string;
    pool_type: string;
    total_pool_value: string;
    currency: string;
    status: string;
    created_at: string;
    updated_at: string;
    cdm_payload?: any;
  };
  tranches: Array<{
    id: number;
    tranche_id: string;
    tranche_name: string;
    tranche_class: string;
    size: string;
    currency: string;
    interest_rate: number;
    risk_rating: string | null;
    payment_priority: number;
    principal_remaining: string;
    interest_accrued: string;
    token_id: string | null;
    owner_wallet_address: string | null;
  }>;
  assets: Array<{
    id: number;
    asset_type: string;
    asset_id: string;
    deal_id: string | null;
    loan_asset_id: string | null;
    asset_value: string;
    currency: string;
  }>;
  filings: Array<{
    id: number;
    filing_type: string;
    status: string;
    filed_at: string | null;
    regulatory_body: string | null;
  }>;
  cdm_payload?: any;
}

export function SecuritizationPoolDetail() {
  const { poolId } = useParams<{ poolId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [poolDetails, setPoolDetails] = useState<PoolDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'tranches' | 'assets' | 'payments' | 'filings'>('overview');

  useEffect(() => {
    if (poolId) {
      fetchPoolDetails();
    }
  }, [poolId]);

  const fetchPoolDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth(`/api/securitization/pools/${poolId}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Pool not found');
        }
        throw new Error('Failed to fetch pool details');
      }
      const data = await response.json();
      
      // Handle both dict response from service and model_dump format
      if (data.pool && typeof data.pool === 'object' && 'pool' in data.pool) {
        // Service returns nested structure
        setPoolDetails(data.pool as PoolDetails);
      } else {
        // API might return flat structure
        setPoolDetails({
          pool: data.pool || data,
          tranches: data.tranches || [],
          assets: data.assets || [],
          filings: data.filings || [],
          cdm_payload: data.cdm_payload || data.pool?.cdm_payload
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pool details');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (error || !poolDetails) {
    return (
      <div className="p-6 space-y-4">
        <Button
          onClick={() => navigate('/app/securitization')}
          variant="outline"
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Securitization
        </Button>
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6 text-center">
            <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-100 mb-2">Error Loading Pool</h2>
            <p className="text-slate-400">{error || 'Pool not found'}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { pool, tranches, assets, filings } = poolDetails;
  const totalPoolValue = parseFloat(pool.total_pool_value || '0');
  const totalTrancheValue = tranches.reduce((sum, t) => sum + parseFloat(t.size || '0'), 0);
  const purchasedTranches = tranches.filter(t => t.owner_wallet_address !== null);
  const availableTranches = tranches.filter(t => t.owner_wallet_address === null);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            onClick={() => navigate('/app/securitization')}
            variant="outline"
            size="sm"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-slate-100">{pool.pool_name}</h1>
            <p className="text-slate-400 mt-1">Pool ID: {pool.pool_id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            pool.status === 'active' 
              ? 'bg-emerald-900/20 text-emerald-400 border border-emerald-500/50'
              : pool.status === 'notarized'
              ? 'bg-blue-900/20 text-blue-400 border border-blue-500/50'
              : 'bg-slate-700 text-slate-400 border border-slate-600'
          }`}>
            {pool.status}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Total Pool Value</p>
                <p className="text-2xl font-bold text-slate-100">
                  {pool.currency} {totalPoolValue.toLocaleString()}
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-emerald-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Tranches</p>
                <p className="text-2xl font-bold text-slate-100">{tranches.length}</p>
              </div>
              <BarChart3 className="h-8 w-8 text-blue-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Underlying Assets</p>
                <p className="text-2xl font-bold text-slate-100">{assets.length}</p>
              </div>
              <Building2 className="h-8 w-8 text-purple-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Available</p>
                <p className="text-2xl font-bold text-slate-100">
                  {availableTranches.length} / {tranches.length}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-cyan-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="tranches">Tranches</TabsTrigger>
          <TabsTrigger value="assets">Assets</TabsTrigger>
          <TabsTrigger value="payments">Payments</TabsTrigger>
          <TabsTrigger value="filings">Filings</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="h-5 w-5" />
                  Pool Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-400">Pool Type:</span>
                  <span className="text-slate-100 font-medium">{pool.pool_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Status:</span>
                  <span className="text-slate-100 font-medium capitalize">{pool.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Currency:</span>
                  <span className="text-slate-100 font-medium">{pool.currency}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Created:</span>
                  <span className="text-slate-100 font-medium">
                    {new Date(pool.created_at).toLocaleDateString()}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Summary Statistics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-400">Total Value:</span>
                  <span className="text-slate-100 font-medium">
                    {pool.currency} {totalPoolValue.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Tranche Total:</span>
                  <span className="text-slate-100 font-medium">
                    {pool.currency} {totalTrancheValue.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Purchased:</span>
                  <span className="text-slate-100 font-medium">
                    {purchasedTranches.length} / {tranches.length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Regulatory Filings:</span>
                  <span className="text-slate-100 font-medium">{filings.length}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="tranches" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Tranche Structure</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {tranches.map((tranche) => {
                  const isPurchased = tranche.owner_wallet_address !== null;
                  const size = parseFloat(tranche.size || '0');
                  const principalRemaining = parseFloat(tranche.principal_remaining || '0');
                  const interestAccrued = parseFloat(tranche.interest_accrued || '0');
                  
                  return (
                    <div
                      key={tranche.id}
                      className={`p-4 rounded-lg border ${
                        isPurchased
                          ? 'bg-blue-900/20 border-blue-500/50'
                          : 'bg-slate-900 border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <h3 className="font-semibold text-slate-100">
                            {tranche.tranche_name}
                          </h3>
                          <p className="text-sm text-slate-400">
                            {tranche.tranche_class} • Priority {tranche.payment_priority}
                            {tranche.risk_rating && ` • ${tranche.risk_rating}`}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {isPurchased ? (
                            <span className="px-2 py-1 bg-blue-900/20 text-blue-400 text-xs rounded border border-blue-500/50">
                              Purchased
                            </span>
                          ) : (
                            <span className="px-2 py-1 bg-emerald-900/20 text-emerald-400 text-xs rounded border border-emerald-500/50">
                              Available
                            </span>
                          )}
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-slate-400">Size:</span>
                          <p className="text-slate-100 font-medium">
                            {tranche.currency} {size.toLocaleString()}
                          </p>
                        </div>
                        <div>
                          <span className="text-slate-400">Interest Rate:</span>
                          <p className="text-slate-100 font-medium">{tranche.interest_rate}%</p>
                        </div>
                        <div>
                          <span className="text-slate-400">Principal Remaining:</span>
                          <p className="text-slate-100 font-medium">
                            {tranche.currency} {principalRemaining.toLocaleString()}
                          </p>
                        </div>
                        <div>
                          <span className="text-slate-400">Interest Accrued:</span>
                          <p className="text-slate-100 font-medium">
                            {tranche.currency} {interestAccrued.toLocaleString()}
                          </p>
                        </div>
                      </div>
                      
                      {tranche.token_id && (
                        <div className="mt-3 pt-3 border-t border-slate-700">
                          <div className="flex items-center gap-2 text-sm">
                            <Wallet className="h-4 w-4 text-slate-400" />
                            <span className="text-slate-400">Token ID:</span>
                            <span className="text-slate-100 font-mono">{tranche.token_id}</span>
                          </div>
                          {tranche.owner_wallet_address && (
                            <div className="flex items-center gap-2 text-sm mt-1">
                              <Users className="h-4 w-4 text-slate-400" />
                              <span className="text-slate-400">Owner:</span>
                              <span className="text-slate-100 font-mono text-xs">
                                {tranche.owner_wallet_address.slice(0, 10)}...{tranche.owner_wallet_address.slice(-8)}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {!isPurchased && (
                        <div className="mt-3">
                          <Button
                            onClick={() => navigate(`/app/securitization/pools/${poolId}/tranches/${tranche.tranche_id}/purchase`)}
                            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white"
                          >
                            <CreditCard className="h-4 w-4 mr-2" />
                            Purchase Tranche
                          </Button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="assets" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Underlying Assets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {assets.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No assets in this pool</p>
                ) : (
                  assets.map((asset) => {
                    const value = parseFloat(asset.asset_value || '0');
                    return (
                      <div
                        key={asset.id}
                        className="p-4 bg-slate-900 rounded-lg border border-slate-700"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-semibold text-slate-100">
                              {asset.asset_type === 'deal' ? 'Deal' : 'Loan Asset'}
                            </p>
                            <p className="text-sm text-slate-400">
                              {asset.asset_type === 'deal' 
                                ? `Deal ID: ${asset.deal_id}`
                                : `Loan Asset ID: ${asset.loan_asset_id}`
                              }
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-semibold text-slate-100">
                              {asset.currency} {value.toLocaleString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="payments" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Payment Schedule</CardTitle>
            </CardHeader>
            <CardContent>
              {poolDetails.cdm_payload?.payment_schedule ? (
                <div className="space-y-4">
                  <p className="text-slate-400 text-sm mb-4">
                    Payment schedule information is available in the CDM payload.
                  </p>
                  <pre className="bg-slate-900 p-4 rounded-lg overflow-auto text-xs text-slate-300">
                    {JSON.stringify(poolDetails.cdm_payload.payment_schedule, null, 2)}
                  </pre>
                </div>
              ) : (
                <p className="text-slate-400 text-center py-8">
                  Payment schedule not yet calculated
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="filings" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Regulatory Filings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {filings.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No regulatory filings yet</p>
                ) : (
                  filings.map((filing) => (
                    <div
                      key={filing.id}
                      className="p-4 bg-slate-900 rounded-lg border border-slate-700"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-slate-100">{filing.filing_type}</p>
                          <p className="text-sm text-slate-400">
                            {filing.regulatory_body || 'N/A'}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            filing.status === 'filed'
                              ? 'bg-emerald-900/20 text-emerald-400 border border-emerald-500/50'
                              : filing.status === 'pending'
                              ? 'bg-yellow-900/20 text-yellow-400 border border-yellow-500/50'
                              : 'bg-slate-700 text-slate-400 border border-slate-600'
                          }`}>
                            {filing.status}
                          </span>
                        </div>
                      </div>
                      {filing.filed_at && (
                        <p className="text-xs text-slate-500 mt-2">
                          Filed: {new Date(filing.filed_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
