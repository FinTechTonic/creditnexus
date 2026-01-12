import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useFDC3 } from '@/context/FDC3Context';
import { fetchWithAuth } from '@/context/AuthContext';
import type { CreditAgreementData, ESGKPITarget } from '@/context/FDC3Context';
import { Leaf, TrendingDown, TrendingUp, AlertTriangle, CheckCircle2, Target, Droplets, Zap, Recycle, Search, Loader2, ChevronDown, MapPin, Building2, Wind } from 'lucide-react';
import { LocationTypeBadge } from '@/components/green-finance/LocationTypeBadge';
import { AirQualityIndicator } from '@/components/green-finance/AirQualityIndicator';
import { SustainabilityScoreCard } from '@/components/green-finance/SustainabilityScoreCard';

const MOCK_ESG_DATA: ESGKPITarget[] = [
  {
    kpi_type: 'CO2 Emissions',
    target_value: 50000,
    current_value: 42000,
    unit: 'tons CO2/year',
    margin_adjustment_bps: -25,
  },
  {
    kpi_type: 'Renewable Energy Percentage',
    target_value: 60,
    current_value: 72,
    unit: '%',
    margin_adjustment_bps: -15,
  },
  {
    kpi_type: 'Water Usage',
    target_value: 1000000,
    current_value: 1100000,
    unit: 'gallons/year',
    margin_adjustment_bps: 0,
  },
];

function getKPIIcon(kpiType: string) {
  if (kpiType.toLowerCase().includes('co2') || kpiType.toLowerCase().includes('emission')) {
    return <Leaf className="h-5 w-5" />;
  }
  if (kpiType.toLowerCase().includes('renewable') || kpiType.toLowerCase().includes('energy')) {
    return <Zap className="h-5 w-5" />;
  }
  if (kpiType.toLowerCase().includes('water')) {
    return <Droplets className="h-5 w-5" />;
  }
  if (kpiType.toLowerCase().includes('waste') || kpiType.toLowerCase().includes('recycl')) {
    return <Recycle className="h-5 w-5" />;
  }
  return <Target className="h-5 w-5" />;
}

function isTargetMet(kpi: ESGKPITarget): boolean {
  if (kpi.current_value === undefined) return false;
  
  if (kpi.kpi_type.toLowerCase().includes('emission') || 
      kpi.kpi_type.toLowerCase().includes('water') ||
      kpi.kpi_type.toLowerCase().includes('waste') ||
      kpi.kpi_type.toLowerCase().includes('incident')) {
    return kpi.current_value <= kpi.target_value;
  }
  return kpi.current_value >= kpi.target_value;
}

export function GreenLens() {
  const { context, clearContext } = useFDC3();
  const [loanData, setLoanData] = useState<CreditAgreementData | null>(null);
  const [esgTargets, setEsgTargets] = useState<ESGKPITarget[]>([]);
  const [showLoanSelector, setShowLoanSelector] = useState(false);
  const [availableLoans, setAvailableLoans] = useState<any[]>([]);
  const [loadingLoans, setLoadingLoans] = useState(false);
  const [loanSearchQuery, setLoanSearchQuery] = useState('');
  const [selectedLoanAsset, setSelectedLoanAsset] = useState<any>(null);

  useEffect(() => {
    if (context?.loan) {
      setLoanData(context.loan);
      
      if (context.loan.esg_kpi_targets && context.loan.esg_kpi_targets.length > 0) {
        setEsgTargets(context.loan.esg_kpi_targets);
      } else if (context.loan.sustainability_linked) {
        setEsgTargets(MOCK_ESG_DATA);
      } else {
        setEsgTargets(MOCK_ESG_DATA);
      }
    }
  }, [context]);

  const handleClear = () => {
    setLoanData(null);
    setEsgTargets([]);
    clearContext();
  };

  const borrower = loanData?.parties?.find(p => p.role.toLowerCase().includes('borrower'));
  
  const totalMarginAdjustment = esgTargets.reduce((sum, kpi) => {
    if (isTargetMet(kpi)) {
      return sum + kpi.margin_adjustment_bps;
    }
    return sum;
  }, 0);

  const targetsMetCount = esgTargets.filter(isTargetMet).length;
  const isSustainabilityLinked = loanData?.sustainability_linked || esgTargets.length > 0;


  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Leaf className="h-6 w-6 text-emerald-400" />
            GreenLens
          </h2>
          <p className="text-muted-foreground">ESG Performance & Margin Ratchet</p>
        </div>
        {loanData && (
          <button onClick={handleClear} className="text-sm text-muted-foreground hover:text-white">
            Clear Data
          </button>
        )}
      </div>

      {!loanData ? (
        <Card className="border-slate-700 bg-slate-800/50">
          <CardContent className="p-12">
            <div className="w-20 h-20 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-6">
              <Leaf className="h-10 w-10 text-emerald-500/50" />
            </div>
            <h3 className="text-xl font-semibold mb-2 text-center">Select a Loan for ESG Analysis</h3>
            <p className="text-muted-foreground max-w-md mx-auto mb-6 text-center">
              Select a loan asset from your portfolio or use the Docu-Digitizer to extract loan data and broadcast it here.
            </p>
            <div className="max-w-md mx-auto">
              <Button
                onClick={async () => {
                  setShowLoanSelector(!showLoanSelector);
                  if (!showLoanSelector && availableLoans.length === 0) {
                    setLoadingLoans(true);
                    try {
                      const response = await fetchWithAuth('/api/loan-assets?limit=20');
                      if (response.ok) {
                        const data = await response.json();
                        setAvailableLoans(data.loan_assets || []);
                      }
                    } catch (err) {
                      console.error('Failed to load loans:', err);
                    } finally {
                      setLoadingLoans(false);
                    }
                  }
                }}
                className="w-full"
              >
                <Search className="h-4 w-4 mr-2" />
                {showLoanSelector ? 'Hide Loans' : 'Select Loan Asset'}
              </Button>
              
              {showLoanSelector && (
                <div className="mt-4 space-y-2 max-h-96 overflow-y-auto">
                  <div className="relative mb-2">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search loans..."
                      value={loanSearchQuery}
                      onChange={(e) => setLoanSearchQuery(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100"
                    />
                  </div>
                  {loadingLoans ? (
                    <div className="text-center py-8 text-slate-400">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                      Loading loans...
                    </div>
                  ) : (
                    availableLoans
                      .filter((loan: any) => 
                        !loanSearchQuery || 
                        loan.loan_id?.toLowerCase().includes(loanSearchQuery.toLowerCase()) ||
                        loan.title?.toLowerCase().includes(loanSearchQuery.toLowerCase())
                      )
                      .map((loan: any) => (
                        <Card
                          key={loan.id}
                          className="border-slate-700 bg-slate-900/50 hover:border-emerald-500/50 cursor-pointer transition-colors"
                          onClick={async () => {
                            try {
                              // Try to get CDM data from the loan's associated deal
                              // Loan assets have loan_id which matches deal.deal_id
                              const dealsResponse = await fetchWithAuth(`/api/deals?search=${loan.loan_id}&limit=1`);
                              if (dealsResponse.ok) {
                                const dealsData = await dealsResponse.json();
                                const deal = dealsData.deals?.[0];
                                if (deal) {
                                  const dealResponse = await fetchWithAuth(`/api/deals/${deal.id}`);
                                  if (dealResponse.ok) {
                                    const dealData = await dealResponse.json();
                                    const documents = dealData.documents || [];
                                    for (const doc of documents) {
                                      const docResponse = await fetchWithAuth(`/api/documents/${doc.id}?include_cdm_data=true`);
                                      if (docResponse.ok) {
                                        const docData = await docResponse.json();
                                        if (docData.cdm_data) {
                                          setLoanData(docData.cdm_data as CreditAgreementData);
                                          if (docData.cdm_data.esg_kpi_targets && docData.cdm_data.esg_kpi_targets.length > 0) {
                                            setEsgTargets(docData.cdm_data.esg_kpi_targets);
                                          } else if (docData.cdm_data.sustainability_linked) {
                                            setEsgTargets(MOCK_ESG_DATA);
                                          } else {
                                            setEsgTargets(MOCK_ESG_DATA);
                                          }
                                          setShowLoanSelector(false);
                                          return;
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                              // If no deal found, create minimal loan data from loan asset
                              setLoanData({
                                deal_id: loan.loan_id,
                                agreement_date: loan.created_at?.split('T')[0] || new Date().toISOString().split('T')[0],
                                parties: [],
                                facilities: [],
                                sustainability_linked: loan.risk_status !== 'BREACH',
                              } as CreditAgreementData);
                              setEsgTargets(MOCK_ESG_DATA);
                              setShowLoanSelector(false);
                            } catch (err) {
                              console.error('Failed to load loan:', err);
                            }
                          }}
                        >
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium text-slate-100">{loan.loan_id}</p>
                                {loan.title && (
                                  <p className="text-sm text-slate-400">{loan.title}</p>
                                )}
                                {loan.risk_status && (
                                  <span className={`text-xs px-2 py-0.5 rounded mt-1 inline-block ${
                                    loan.risk_status === 'COMPLIANT' ? 'bg-emerald-500/20 text-emerald-400' :
                                    loan.risk_status === 'WARNING' ? 'bg-yellow-500/20 text-yellow-400' :
                                    'bg-red-500/20 text-red-400'
                                  }`}>
                                    {loan.risk_status}
                                  </span>
                                )}
                              </div>
                              <ChevronDown className="h-4 w-4 text-slate-400" />
                            </div>
                          </CardContent>
                        </Card>
                      ))
                  )}
                  {availableLoans.length === 0 && !loadingLoans && (
                    <div className="text-center py-8 text-slate-400">
                      No loan assets found. Create loan assets first or use Docu-Digitizer to extract loan data.
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="border-slate-700 bg-slate-800/50">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground mb-1">Borrower</div>
                <div className="font-medium truncate">{borrower?.name || 'N/A'}</div>
              </CardContent>
            </Card>
            
            <Card className="border-slate-700 bg-slate-800/50">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground mb-1">Sustainability Linked</div>
                <div className="font-medium flex items-center gap-2">
                  {isSustainabilityLinked ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      <span className="text-emerald-400">Yes</span>
                    </>
                  ) : (
                    <span>No</span>
                  )}
                </div>
              </CardContent>
            </Card>
            
            <Card className="border-slate-700 bg-slate-800/50">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground mb-1">ESG Targets Met</div>
                <div className="font-medium">
                  <span className="text-emerald-400">{targetsMetCount}</span>
                  <span className="text-muted-foreground"> / {esgTargets.length}</span>
                </div>
              </CardContent>
            </Card>
            
            <Card className={`border-2 ${totalMarginAdjustment < 0 ? 'border-emerald-500/50 bg-emerald-500/10' : 'border-slate-700 bg-slate-800/50'}`}>
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground mb-1">Total Margin Adjustment</div>
                <div className={`font-bold text-lg flex items-center gap-1 ${totalMarginAdjustment < 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                  {totalMarginAdjustment < 0 ? (
                    <TrendingDown className="h-4 w-4" />
                  ) : totalMarginAdjustment > 0 ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : null}
                  {totalMarginAdjustment > 0 ? '+' : ''}{totalMarginAdjustment} bps
                </div>
              </CardContent>
            </Card>
          </div>

          {totalMarginAdjustment < 0 && (
            <Card className="border-emerald-500/30 bg-gradient-to-r from-emerald-500/10 to-transparent">
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center">
                    <Leaf className="h-8 w-8 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-emerald-400">Margin Discount Applied</h3>
                    <p className="text-muted-foreground">
                      Based on ESG performance, this loan qualifies for a{' '}
                      <span className="text-emerald-400 font-medium">{Math.abs(totalMarginAdjustment)} bps</span> margin reduction.
                    </p>
                  </div>
                  <div className="ml-auto text-right">
                    <div className="text-3xl font-bold text-emerald-400">{totalMarginAdjustment} bps</div>
                    <div className="text-sm text-muted-foreground">Annual Savings</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader>
                <CardTitle>ESG Performance vs Targets</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {esgTargets.map((kpi, idx) => {
                    const met = isTargetMet(kpi);
                    const maxValue = Math.max(kpi.target_value, kpi.current_value || 0);
                    const normalizedTarget = (kpi.target_value / maxValue) * 100;
                    const normalizedCurrent = ((kpi.current_value || 0) / maxValue) * 100;
                    
                    return (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-300">{kpi.kpi_type.split(' ').slice(0, 2).join(' ')}</span>
                          <span className={met ? 'text-emerald-400' : 'text-yellow-400'}>
                            {met ? 'Met' : 'In Progress'}
                          </span>
                        </div>
                        <div className="relative h-8 bg-slate-900 rounded overflow-hidden">
                          <div 
                            className="absolute h-full bg-blue-600/40 rounded-r"
                            style={{ width: `${normalizedTarget}%` }}
                          />
                          <div 
                            className={`absolute h-full rounded-r ${met ? 'bg-emerald-500' : 'bg-yellow-500'}`}
                            style={{ width: `${normalizedCurrent}%`, opacity: 0.8 }}
                          />
                          <div className="absolute inset-0 flex items-center px-2 justify-between text-xs font-mono">
                            <span className="text-white/80">Current: {(kpi.current_value || 0).toLocaleString()}</span>
                            <span className="text-blue-300">Target: {kpi.target_value.toLocaleString()}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  <div className="flex gap-4 mt-4 text-xs text-slate-400">
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-blue-600/40 rounded" />
                      <span>Target</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-emerald-500 rounded" />
                      <span>Met</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-yellow-500 rounded" />
                      <span>In Progress</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader>
                <CardTitle>KPI Details</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {esgTargets.map((kpi, idx) => {
                    const met = isTargetMet(kpi);
                    const percentage = kpi.current_value 
                      ? Math.round((kpi.current_value / kpi.target_value) * 100) 
                      : 0;
                    
                    return (
                      <div key={idx} className="p-4 bg-slate-900/50 rounded-lg border border-slate-700">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <div className={`p-2 rounded-lg ${met ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                              {getKPIIcon(kpi.kpi_type)}
                            </div>
                            <div>
                              <div className="font-medium">{kpi.kpi_type}</div>
                              <div className="text-xs text-muted-foreground">{kpi.unit}</div>
                            </div>
                          </div>
                          {met ? (
                            <span className="flex items-center gap-1 text-emerald-400 text-sm">
                              <CheckCircle2 className="h-4 w-4" />
                              Target Met
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-yellow-400 text-sm">
                              <AlertTriangle className="h-4 w-4" />
                              Below Target
                            </span>
                          )}
                        </div>
                        
                        <div className="grid grid-cols-3 gap-4 text-sm">
                          <div>
                            <div className="text-muted-foreground">Current</div>
                            <div className="font-mono">{kpi.current_value?.toLocaleString() || 'N/A'}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Target</div>
                            <div className="font-mono">{kpi.target_value.toLocaleString()}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Margin Impact</div>
                            <div className={`font-mono ${met && kpi.margin_adjustment_bps < 0 ? 'text-emerald-400' : ''}`}>
                              {met ? `${kpi.margin_adjustment_bps > 0 ? '+' : ''}${kpi.margin_adjustment_bps} bps` : '—'}
                            </div>
                          </div>
                        </div>

                        <div className="mt-3">
                          <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                            <div 
                              className={`h-full transition-all ${met ? 'bg-emerald-500' : 'bg-yellow-500'}`}
                              style={{ width: `${Math.min(percentage, 100)}%` }}
                            />
                          </div>
                          <div className="text-xs text-muted-foreground mt-1 text-right">{percentage}% of target</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Geospatial ESG Metrics */}
        {(selectedLoanAsset && (selectedLoanAsset.location_type || selectedLoanAsset.air_quality_index || selectedLoanAsset.composite_sustainability_score)) && (
          <Card className="border-slate-700 bg-slate-800/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-blue-400" />
                Geospatial ESG Metrics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {selectedLoanAsset.location_type && (
                  <div className="space-y-2">
                    <div className="text-xs text-muted-foreground">Location Type</div>
                    <LocationTypeBadge 
                      locationType={selectedLoanAsset.location_type}
                      confidence={selectedLoanAsset.green_finance_metrics?.location_confidence}
                    />
                  </div>
                )}
                {selectedLoanAsset.air_quality_index && (
                  <div className="space-y-2">
                    <div className="text-xs text-muted-foreground">Air Quality</div>
                    <AirQualityIndicator 
                      aqi={selectedLoanAsset.air_quality_index}
                      pm25={selectedLoanAsset.green_finance_metrics?.air_quality?.pm25}
                      compact
                    />
                  </div>
                )}
                {selectedLoanAsset.composite_sustainability_score !== undefined && (
                  <div className="space-y-2">
                    <div className="text-xs text-muted-foreground">Sustainability Score</div>
                    <SustainabilityScoreCard 
                      compositeScore={selectedLoanAsset.composite_sustainability_score}
                      components={selectedLoanAsset.green_finance_metrics?.sustainability_components}
                      compact
                    />
                  </div>
                )}
              </div>

              {/* Add geospatial KPIs to ESG targets */}
              {selectedLoanAsset.composite_sustainability_score !== undefined && (
                <div className="pt-4 border-t border-slate-700">
                  <div className="text-xs text-muted-foreground mb-2">Geospatial ESG KPIs</div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-slate-300 flex items-center gap-2">
                        <Leaf className="h-4 w-4" />
                        Location Sustainability Score
                      </span>
                      <span className={selectedLoanAsset.composite_sustainability_score >= 0.7 ? 'text-emerald-400' : 'text-yellow-400'}>
                        {(selectedLoanAsset.composite_sustainability_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    {selectedLoanAsset.air_quality_index && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-300 flex items-center gap-2">
                          <Wind className="h-4 w-4" />
                          Air Quality Index
                        </span>
                        <span className={selectedLoanAsset.air_quality_index <= 100 ? 'text-emerald-400' : 'text-orange-400'}>
                          {Math.round(selectedLoanAsset.air_quality_index)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
        </>
      )}
    </div>
  );
}
