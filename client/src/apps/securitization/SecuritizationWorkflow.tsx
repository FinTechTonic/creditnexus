import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Building2, 
  Wallet, 
  CheckCircle, 
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  ArrowRight,
  Shield,
  FileText,
  DollarSign
} from 'lucide-react';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';
import { useWallet } from '@/context/WalletContext';
// import { useX402Payment } from '@/hooks/useX402Payment';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface AvailableAsset {
  asset_id: string;
  asset_type: 'deal' | 'loan_asset';
  deal_id?: string;
  loan_id?: string;
  name: string;
  value: string;
  currency: string;
  status: string;
}

interface SelectedAsset extends AvailableAsset {
  allocation_percentage?: number;
  allocation_amount?: number;
}

interface TrancheDefinition {
  tranche_name: string;
  tranche_class: string;
  size: {
    amount: number;
    currency: string;
  };
  interest_rate: number;
  risk_rating?: string;
  payment_priority: number;
}

interface PoolConfiguration {
  pool_name: string;
  pool_type: string;
  originator_id: number | null;
  trustee_id: number | null;
  underlying_assets: SelectedAsset[];
  tranches: TrancheDefinition[];
}

export function SecuritizationWorkflow() {
  const { user } = useAuth();
  const { isConnected, account } = useWallet();
  // const { processPayment, isProcessing: paymentProcessing } = useX402Payment();
  
  const [activeStep, setActiveStep] = useState<'assets' | 'configure' | 'review' | 'notarize'>('assets');
  const [availableAssets, setAvailableAssets] = useState<AvailableAsset[]>([]);
  const [selectedAssets, setSelectedAssets] = useState<SelectedAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [poolConfig, setPoolConfig] = useState<PoolConfiguration>({
    pool_name: '',
    pool_type: 'ABS',
    originator_id: null,
    trustee_id: null,
    underlying_assets: [],
    tranches: []
  });
  const [creating, setCreating] = useState(false);
  const [createdPoolId, setCreatedPoolId] = useState<string | null>(null);

  useEffect(() => {
    fetchAvailableAssets();
  }, []);

  const fetchAvailableAssets = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth('/api/securitization/available-assets?limit=100');
      if (!response.ok) {
        throw new Error('Failed to fetch available assets');
      }
      const data = await response.json();
      setAvailableAssets(data.assets || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assets');
    } finally {
      setLoading(false);
    }
  };

  const handleAssetToggle = (asset: AvailableAsset) => {
    setSelectedAssets(prev => {
      const exists = prev.find(a => 
        (asset.asset_type === 'deal' && a.deal_id === asset.deal_id) ||
        (asset.asset_type === 'loan_asset' && a.loan_id === asset.loan_id)
      );
      
      if (exists) {
        return prev.filter(a => 
          !((asset.asset_type === 'deal' && a.deal_id === asset.deal_id) ||
            (asset.asset_type === 'loan_asset' && a.loan_id === asset.loan_id))
        );
      } else {
        const amount = parseFloat(asset.value) || 0;
        return [...prev, { 
          ...asset, 
          allocation_percentage: 100, 
          allocation_amount: amount 
        }];
      }
    });
  };

  const handleAllocationChange = (assetId: string, percentage: number) => {
    setSelectedAssets(prev => prev.map(asset => {
      const match = (asset.asset_type === 'deal' && asset.deal_id === assetId) ||
                    (asset.asset_type === 'loan_asset' && asset.loan_id === assetId);
      if (match) {
        const baseAmount = parseFloat(asset.value) || 0;
        const allocationAmount = (baseAmount * percentage) / 100;
        return { ...asset, allocation_percentage: percentage, allocation_amount: allocationAmount };
      }
      return asset;
    }));
  };

  const handleAddTranche = () => {
    setPoolConfig(prev => ({
      ...prev,
      tranches: [
        ...prev.tranches,
        {
          tranche_name: `Tranche ${prev.tranches.length + 1}`,
          tranche_class: 'Senior',
          size: { amount: 0, currency: 'USD' },
          interest_rate: 5.0,
          risk_rating: 'AAA',
          payment_priority: prev.tranches.length + 1
        }
      ]
    }));
  };

  const handleTrancheChange = (index: number, field: string, value: any) => {
    setPoolConfig(prev => ({
      ...prev,
      tranches: prev.tranches.map((t, i) => 
        i === index ? { ...t, [field]: value } : t
      )
    }));
  };

  const handleRemoveTranche = (index: number) => {
    setPoolConfig(prev => ({
      ...prev,
      tranches: prev.tranches.filter((_, i) => i !== index)
    }));
  };

  const calculateTotalPoolValue = () => {
    return selectedAssets.reduce((sum, asset) => {
      const baseAmount = parseFloat(asset.value) || 0;
      return sum + (asset.allocation_amount || baseAmount);
    }, 0);
  };

  const calculateTrancheTotal = () => {
    return poolConfig.tranches.reduce((sum, t) => sum + t.size.amount, 0);
  };

  const handleCreatePool = async () => {
    if (!poolConfig.pool_name || !poolConfig.originator_id || !poolConfig.trustee_id) {
      setError('Please fill in all required fields');
      return;
    }

    if (selectedAssets.length === 0) {
      setError('Please select at least one asset');
      return;
    }

    if (poolConfig.tranches.length === 0) {
      setError('Please add at least one tranche');
      return;
    }

    const totalPoolValue = calculateTotalPoolValue();
    const trancheTotal = calculateTrancheTotal();
    
    if (Math.abs(totalPoolValue - trancheTotal) > 0.01) {
      setError(`Tranche total (${trancheTotal}) must equal pool value (${totalPoolValue})`);
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const underlying_assets = selectedAssets.map(asset => ({
        asset_type: asset.asset_type,
        asset_id: asset.asset_id,
        deal_id: asset.deal_id,
        loan_asset_id: asset.loan_id,
        value: asset.allocation_amount || parseFloat(asset.value || '0'),
        currency: asset.currency
      }));

      const tranches = poolConfig.tranches.map(t => ({
        tranche_name: t.tranche_name,
        tranche_class: t.tranche_class,
        size: t.size,
        interest_rate: t.interest_rate,
        risk_rating: t.risk_rating,
        payment_priority: t.payment_priority
      }));

      const response = await fetchWithAuth('/api/securitization/pools', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pool_name: poolConfig.pool_name,
          pool_type: poolConfig.pool_type,
          originator_user_id: poolConfig.originator_id,
          trustee_user_id: poolConfig.trustee_id,
          underlying_asset_ids: underlying_assets,
          tranche_data: tranches
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create pool');
      }

      const data = await response.json();
      setCreatedPoolId(data.pool_id);
      setActiveStep('notarize');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create pool');
    } finally {
      setCreating(false);
    }
  };

  const totalPoolValue = calculateTotalPoolValue();
  const trancheTotal = calculateTrancheTotal();

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Securitization Workflow</h1>
          <p className="text-slate-400 mt-1">Bundle deals and loans into structured finance products</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-4 flex items-center gap-2 text-red-400">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      <Tabs value={activeStep} onValueChange={(v) => setActiveStep(v as any)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="assets">Step 1: Select Assets</TabsTrigger>
          <TabsTrigger value="configure">Step 2: Configure Pool</TabsTrigger>
          <TabsTrigger value="review">Step 3: Review</TabsTrigger>
          <TabsTrigger value="notarize">Step 4: Notarize</TabsTrigger>
        </TabsList>

        <TabsContent value="assets" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Available Assets
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-emerald-400" />
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-sm text-slate-400 mb-4">
                    Selected: {selectedAssets.length} assets | Total: ${totalPoolValue.toLocaleString()}
                  </div>
                  
                  <div className="space-y-2">
                    {availableAssets.map((asset) => {
                      const isSelected = selectedAssets.some(a =>
                        (asset.asset_type === 'deal' && a.deal_id === asset.deal_id) ||
                        (asset.asset_type === 'loan_asset' && a.loan_id === asset.loan_id)
                      );
                      
                      return (
                        <div
                          key={`${asset.type}_${asset.deal_id || asset.loan_asset_id}`}
                          className={`p-4 rounded-lg border ${
                            isSelected
                              ? 'bg-emerald-900/20 border-emerald-500/50'
                              : 'bg-slate-900 border-slate-700'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 flex-1">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => handleAssetToggle(asset)}
                                className="w-4 h-4 rounded border-slate-600"
                              />
                              <div className="flex-1">
                                <div className="font-semibold text-slate-100">
                                  {asset.name}
                                </div>
                                <div className="text-sm text-slate-400">
                                  {asset.asset_type === 'deal' ? `Deal: ${asset.deal_id}` : `Loan: ${asset.loan_id}`} | 
                                  {asset.currency} {parseFloat(asset.value || '0').toLocaleString()} | 
                                  Status: {asset.status}
                                </div>
                              </div>
                            </div>
                          </div>
                          
                          {isSelected && (
                            <div className="mt-3 pt-3 border-t border-slate-700">
                              <Label className="text-sm text-slate-400">Allocation Percentage</Label>
                              <Input
                                type="number"
                                min="0"
                                max="100"
                                value={
                                  selectedAssets.find(a =>
                                    (asset.type === 'deal' && a.deal_id === asset.deal_id) ||
                                    (asset.type === 'loan_asset' && a.loan_asset_id === asset.loan_asset_id)
                                  )?.allocation_percentage || 100
                                }
                                onChange={(e) => {
                                  const percentage = parseFloat(e.target.value) || 0;
                                  const assetId = asset.asset_type === 'deal' ? asset.deal_id! : asset.loan_id!;
                                  handleAllocationChange(assetId, percentage);
                                }}
                                className="mt-1 bg-slate-900 border-slate-700"
                              />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {selectedAssets.length > 0 && (
                    <div className="flex justify-end pt-4">
                      <Button
                        onClick={() => setActiveStep('configure')}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white"
                      >
                        Continue to Configuration
                        <ArrowRight className="h-4 w-4 ml-2" />
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="configure" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Pool Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Pool Name</Label>
                  <Input
                    value={poolConfig.pool_name}
                    onChange={(e) => setPoolConfig(prev => ({ ...prev, pool_name: e.target.value }))}
                    placeholder="Q1 2024 ABS Pool"
                    className="bg-slate-900 border-slate-700"
                  />
                </div>
                <div>
                  <Label>Pool Type</Label>
                  <select
                    value={poolConfig.pool_type}
                    onChange={(e) => setPoolConfig(prev => ({ ...prev, pool_type: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100"
                  >
                    <option value="ABS">ABS (Asset-Backed Security)</option>
                    <option value="CLO">CLO (Collateralized Loan Obligation)</option>
                    <option value="MBS">MBS (Mortgage-Backed Security)</option>
                  </select>
                </div>
                <div>
                  <Label>Originator ID</Label>
                  <Input
                    type="number"
                    value={poolConfig.originator_id || ''}
                    onChange={(e) => setPoolConfig(prev => ({ ...prev, originator_id: parseInt(e.target.value) || null }))}
                    placeholder="User ID"
                    className="bg-slate-900 border-slate-700"
                  />
                </div>
                <div>
                  <Label>Trustee ID</Label>
                  <Input
                    type="number"
                    value={poolConfig.trustee_id || ''}
                    onChange={(e) => setPoolConfig(prev => ({ ...prev, trustee_id: parseInt(e.target.value) || null }))}
                    placeholder="User ID"
                    className="bg-slate-900 border-slate-700"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-slate-700">
                <div className="flex items-center justify-between mb-4">
                  <Label className="text-lg font-semibold">Tranche Structure</Label>
                  <Button
                    onClick={handleAddTranche}
                    variant="outline"
                    size="sm"
                    className="border-emerald-500/50 text-emerald-400"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Tranche
                  </Button>
                </div>

                <div className="space-y-4">
                  {poolConfig.tranches.map((tranche, index) => (
                    <div key={index} className="p-4 bg-slate-900 rounded-lg border border-slate-700">
                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div>
                          <Label>Tranche Name</Label>
                          <Input
                            value={tranche.tranche_name}
                            onChange={(e) => handleTrancheChange(index, 'tranche_name', e.target.value)}
                            className="bg-slate-800 border-slate-700"
                          />
                        </div>
                        <div>
                          <Label>Tranche Class</Label>
                          <select
                            value={tranche.tranche_class}
                            onChange={(e) => handleTrancheChange(index, 'tranche_class', e.target.value)}
                            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-100"
                          >
                            <option value="Senior">Senior</option>
                            <option value="Mezzanine">Mezzanine</option>
                            <option value="Equity">Equity</option>
                          </select>
                        </div>
                        <div>
                          <Label>Size (Amount)</Label>
                          <Input
                            type="number"
                            value={tranche.size.amount}
                            onChange={(e) => handleTrancheChange(index, 'size', {
                              ...tranche.size,
                              amount: parseFloat(e.target.value) || 0
                            })}
                            className="bg-slate-800 border-slate-700"
                          />
                        </div>
                        <div>
                          <Label>Interest Rate (%)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={tranche.interest_rate}
                            onChange={(e) => handleTrancheChange(index, 'interest_rate', parseFloat(e.target.value) || 0)}
                            className="bg-slate-800 border-slate-700"
                          />
                        </div>
                        <div>
                          <Label>Risk Rating</Label>
                          <Input
                            value={tranche.risk_rating || ''}
                            onChange={(e) => handleTrancheChange(index, 'risk_rating', e.target.value)}
                            placeholder="AAA, AA, A, BBB, etc."
                            className="bg-slate-800 border-slate-700"
                          />
                        </div>
                        <div>
                          <Label>Payment Priority</Label>
                          <Input
                            type="number"
                            value={tranche.payment_priority}
                            onChange={(e) => handleTrancheChange(index, 'payment_priority', parseInt(e.target.value) || 1)}
                            className="bg-slate-800 border-slate-700"
                          />
                        </div>
                      </div>
                      <Button
                        onClick={() => handleRemoveTranche(index)}
                        variant="ghost"
                        size="sm"
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Remove
                      </Button>
                    </div>
                  ))}
                </div>

                {poolConfig.tranches.length > 0 && (
                  <div className="mt-4 p-4 bg-blue-900/20 border border-blue-500/50 rounded-lg">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Pool Value:</span>
                      <span className="text-blue-400 font-semibold">${totalPoolValue.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-sm mt-2">
                      <span className="text-slate-400">Tranche Total:</span>
                      <span className={`font-semibold ${Math.abs(totalPoolValue - trancheTotal) < 0.01 ? 'text-emerald-400' : 'text-red-400'}`}>
                        ${trancheTotal.toLocaleString()}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-between pt-4">
                <Button
                  onClick={() => setActiveStep('assets')}
                  variant="outline"
                >
                  Back
                </Button>
                <Button
                  onClick={() => setActiveStep('review')}
                  disabled={poolConfig.tranches.length === 0}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  Review Pool
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="review" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Review & Create Pool</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold text-slate-100 mb-2">Pool Details</h3>
                  <div className="bg-slate-900 p-4 rounded-lg space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Pool Name:</span>
                      <span className="text-slate-100">{poolConfig.pool_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Pool Type:</span>
                      <span className="text-slate-100">{poolConfig.pool_type}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Total Value:</span>
                      <span className="text-slate-100">${totalPoolValue.toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-slate-100 mb-2">Selected Assets ({selectedAssets.length})</h3>
                  <div className="bg-slate-900 p-4 rounded-lg space-y-2 text-sm max-h-40 overflow-y-auto">
                    {selectedAssets.map((asset, idx) => {
                      const baseAmount = parseFloat(asset.value || '0');
                      const allocationAmount = asset.allocation_amount || baseAmount;
                      return (
                        <div key={idx} className="flex justify-between">
                          <span className="text-slate-400">{asset.name}</span>
                          <span className="text-slate-100">
                            ${allocationAmount.toLocaleString()}
                            {asset.allocation_percentage && asset.allocation_percentage < 100 && 
                              ` (${asset.allocation_percentage}%)`
                            }
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-slate-100 mb-2">Tranches ({poolConfig.tranches.length})</h3>
                  <div className="bg-slate-900 p-4 rounded-lg space-y-2 text-sm">
                    {poolConfig.tranches.map((tranche, idx) => (
                      <div key={idx} className="flex justify-between">
                        <span className="text-slate-400">{tranche.tranche_name} ({tranche.tranche_class})</span>
                        <span className="text-slate-100">
                          ${tranche.size.amount.toLocaleString()} @ {tranche.interest_rate}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-between pt-4">
                <Button
                  onClick={() => setActiveStep('configure')}
                  variant="outline"
                >
                  Back
                </Button>
                <Button
                  onClick={handleCreatePool}
                  disabled={creating || Math.abs(totalPoolValue - trancheTotal) > 0.01}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  {creating ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Creating Pool...
                    </>
                  ) : (
                    <>
                      <FileText className="h-4 w-4 mr-2" />
                      Create Pool
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notarize" className="space-y-4">
          {createdPoolId ? (
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-emerald-400" />
                  Pool Created Successfully
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="bg-emerald-900/20 border border-emerald-500/50 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-2">Pool ID</div>
                    <div className="text-lg font-semibold text-emerald-400">{createdPoolId}</div>
                  </div>
                  
                  <p className="text-slate-400 text-sm">
                    Your securitization pool has been created. You can now proceed with notarization.
                  </p>
                  
                  <Button
                    onClick={() => window.location.href = `/dashboard/securitization/${createdPoolId}`}
                    className="w-full bg-blue-600 hover:bg-blue-500 text-white"
                  >
                    <Shield className="h-4 w-4 mr-2" />
                    View Pool Details & Notarize
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-6 text-center text-slate-400">
                Please complete the previous steps to create a pool.
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
