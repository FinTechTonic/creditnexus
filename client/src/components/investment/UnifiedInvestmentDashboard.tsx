import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { fetchWithAuth } from '@/context/AuthContext';
import { DollarSign, TrendingUp, BarChart2, AlertTriangle, ArrowUp, ArrowDown, Building2, CreditCard, Layers, Clock } from 'lucide-react';
import { OrderForm } from '@/components/trading/OrderForm';
import { StockPredictionTab } from '@/components/trading/StockPredictionTab';
import { BacktestTab } from '@/components/trading/BacktestTab';
import { PortfolioView } from '@/components/trading/PortfolioView';
import { MarketData } from '@/components/trading/MarketData';
import { ErrorBoundary } from '@/components/ErrorBoundary';

interface PortfolioMetrics {
  total_value: number;
  total_equity: number;
  unrealized_pl: number;
  realized_pl: number;
  buying_power: number;
  currency: string;
}

interface AssetAllocation {
  equity: number;
  bonds: number;
  real_estate: number;
  commodities: number;
  cash: number;
  other: number;
}

interface RiskMetrics {
  sharpe_ratio?: number;
  beta?: number;
  var_95?: number;
  max_drawdown?: number;
}

interface TechnicalIndicators {
  rsi?: number;
  macd?: number;
  bollinger_bands?: { upper: number; middle: number; lower: number };
  moving_averages?: { sma_50?: number; sma_200?: number };
}

interface TradingMetrics {
  open_positions: number;
  pending_orders: number;
  today_pnl: number;
  total_trades: number;
}

interface BankingMetrics {
  total_balance: number;
  connected_accounts: number;
  pending_transactions: number;
}

export function UnifiedInvestmentDashboard() {
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics | null>(null);
  const [assetAllocation, setAssetAllocation] = useState<AssetAllocation | null>(null);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [technicalIndicators, setTechnicalIndicators] = useState<TechnicalIndicators | null>(null);
  const [tradingMetrics, setTradingMetrics] = useState<TradingMetrics | null>(null);
  const [bankingMetrics, setBankingMetrics] = useState<BankingMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'trading' | 'banking' | 'risk'>('overview');
  const [tradingSubTab, setTradingSubTab] = useState<'overview' | 'orders' | 'predictions' | 'backtest' | 'market' | 'portfolio'>('overview');
  
  useEffect(() => {
    loadAllMetrics();
  }, []);
  
  const loadAllMetrics = async () => {
    setLoading(true);
    try {
      // Load portfolio overview
      const portfolioRes = await fetchWithAuth('/api/portfolio/overview');
      if (portfolioRes.ok) {
        const portfolio = await portfolioRes.json();
        setPortfolioMetrics({
          total_value: portfolio.total_equity || 0,
          total_equity: portfolio.total_equity || 0,
          unrealized_pl: portfolio.unrealized_pl || 0,
          realized_pl: portfolio.realized_pl || 0,
          buying_power: portfolio.buying_power || 0,
          currency: portfolio.currency || 'USD'
        });
      }
      
      // Load risk analysis
      const riskRes = await fetchWithAuth('/api/portfolio/risk-analysis');
      if (riskRes.ok) {
        const risk = await riskRes.json();
        setAssetAllocation(risk.asset_allocation || {});
        setRiskMetrics(risk.risk_metrics || {});
      }
      
      // Load trading metrics
      const tradingRes = await fetchWithAuth('/api/trades/portfolio');
      if (tradingRes.ok) {
        const trading = await tradingRes.json();
        setTradingMetrics({
          open_positions: trading.positions?.length || 0,
          pending_orders: trading.pending_orders || 0,
          today_pnl: trading.today_pnl || 0,
          total_trades: trading.total_trades || 0
        });
      }
      
      // Load banking metrics (handle 503 gracefully if Plaid is disabled)
      try {
        const bankingRes = await fetchWithAuth('/api/banking/balances');
        if (bankingRes.ok) {
          const banking = await bankingRes.json();
          const totalBalance = banking.accounts?.reduce((sum: number, acc: any) => sum + (acc.balance || 0), 0) || 0;
          setBankingMetrics({
            total_balance: totalBalance,
            connected_accounts: banking.accounts?.length || 0,
            pending_transactions: 0
          });
        } else if (bankingRes.status === 503) {
          // Plaid is disabled - set empty metrics
          setBankingMetrics({
            total_balance: 0,
            connected_accounts: 0,
            pending_transactions: 0
          });
        }
      } catch (error) {
        // Handle any other errors gracefully
        setBankingMetrics({
          total_balance: 0,
          connected_accounts: 0,
          pending_transactions: 0
        });
      }
      
      // Load technical indicators (new endpoint to be created)
      const techRes = await fetchWithAuth('/api/portfolio/technical-indicators');
      if (techRes.ok) {
        setTechnicalIndicators(await techRes.json());
      }
    } catch (error) {
      console.error('Failed to load metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderOverviewTab = () => (
    <div className="space-y-6">
      {/* Key Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Portfolio Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {portfolioMetrics ? `$${portfolioMetrics.total_value.toLocaleString()}` : '—'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Equity: {portfolioMetrics ? `$${portfolioMetrics.total_equity.toLocaleString()}` : '—'}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unrealized P&L</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              portfolioMetrics && portfolioMetrics.unrealized_pl >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {portfolioMetrics ? (
                <>
                  {portfolioMetrics.unrealized_pl >= 0 ? <ArrowUp className="inline h-5 w-5" /> : <ArrowDown className="inline h-5 w-5" />}
                  ${Math.abs(portfolioMetrics.unrealized_pl).toLocaleString()}
                </>
              ) : '—'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Realized: {portfolioMetrics ? `$${portfolioMetrics.realized_pl.toLocaleString()}` : '—'}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Buying Power</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {portfolioMetrics ? `$${portfolioMetrics.buying_power.toLocaleString()}` : '—'}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Risk Score</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {riskMetrics?.sharpe_ratio ? riskMetrics.sharpe_ratio.toFixed(2) : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Sharpe Ratio</p>
          </CardContent>
        </Card>
      </div>
      
      {/* Asset Allocation */}
      {assetAllocation && (
        <Card>
          <CardHeader>
            <CardTitle>Asset Allocation</CardTitle>
            <CardDescription>Portfolio distribution across asset classes</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(assetAllocation)
                .filter(([_, percentage]) => percentage > 0)
                .sort(([_, a], [__, b]) => b - a)
                .map(([asset, percentage]) => (
                  <div key={asset} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="capitalize font-medium">{asset.replace('_', ' ')}</span>
                      <span className="font-semibold">{percentage.toFixed(1)}%</span>
                    </div>
                    <Progress value={percentage} className="h-2" />
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );

  const renderTradingTab = () => {
    return (
      <div className="space-y-6">
        {/* Trading Sub-Tabs */}
        <Tabs value={tradingSubTab} onValueChange={(v) => setTradingSubTab(v as typeof tradingSubTab)}>
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="orders">Orders</TabsTrigger>
            <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
            <TabsTrigger value="market">Market</TabsTrigger>
            <TabsTrigger value="predictions">Predictions</TabsTrigger>
            <TabsTrigger value="backtest">Backtest</TabsTrigger>
          </TabsList>
          
          <TabsContent value="overview" className="mt-6 space-y-6">
            {/* Trading Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {tradingMetrics?.open_positions || 0}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {tradingMetrics?.pending_orders || 0}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Today's P&L</CardTitle>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold ${
                    tradingMetrics && tradingMetrics.today_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {tradingMetrics ? `$${tradingMetrics.today_pnl.toLocaleString()}` : '—'}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
                  <BarChart2 className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {tradingMetrics?.total_trades || 0}
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Technical Indicators */}
            {technicalIndicators && (
              <Card>
                <CardHeader>
                  <CardTitle>Technical Indicators</CardTitle>
                  <CardDescription>Market analysis indicators</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {typeof technicalIndicators.rsi === 'number' && !Number.isNaN(technicalIndicators.rsi) && (
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">RSI (14)</p>
                        <div className="flex items-center gap-2">
                          <div className="text-lg font-semibold">{technicalIndicators.rsi.toFixed(2)}</div>
                          <div className={`text-xs px-2 py-1 rounded ${
                            technicalIndicators.rsi > 70 ? 'bg-red-900/20 text-red-400' :
                            technicalIndicators.rsi < 30 ? 'bg-green-900/20 text-green-400' :
                            'bg-slate-800 text-slate-400'
                          }`}>
                            {technicalIndicators.rsi > 70 ? 'Overbought' :
                             technicalIndicators.rsi < 30 ? 'Oversold' : 'Neutral'}
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {typeof technicalIndicators.macd === 'number' && !Number.isNaN(technicalIndicators.macd) && (
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">MACD</p>
                        <div className="text-lg font-semibold">{technicalIndicators.macd.toFixed(2)}</div>
                      </div>
                    )}
                    
                    {technicalIndicators.bollinger_bands &&
                     typeof technicalIndicators.bollinger_bands.upper === 'number' &&
                     typeof technicalIndicators.bollinger_bands.middle === 'number' &&
                     typeof technicalIndicators.bollinger_bands.lower === 'number' &&
                     !Number.isNaN(technicalIndicators.bollinger_bands.upper) &&
                     !Number.isNaN(technicalIndicators.bollinger_bands.middle) &&
                     !Number.isNaN(technicalIndicators.bollinger_bands.lower) && (
                      <div className="space-y-1 col-span-2">
                        <p className="text-xs text-muted-foreground mb-2">Bollinger Bands</p>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span>Upper:</span>
                            <span className="font-medium">{technicalIndicators.bollinger_bands.upper.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Middle:</span>
                            <span className="font-medium">{technicalIndicators.bollinger_bands.middle.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Lower:</span>
                            <span className="font-medium">{technicalIndicators.bollinger_bands.lower.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {technicalIndicators.moving_averages && (
                      <>
                        {typeof technicalIndicators.moving_averages.sma_50 === 'number' &&
                         !Number.isNaN(technicalIndicators.moving_averages.sma_50) && (
                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground">SMA (50)</p>
                            <div className="text-lg font-semibold">{technicalIndicators.moving_averages.sma_50.toFixed(2)}</div>
                          </div>
                        )}
                        {typeof technicalIndicators.moving_averages.sma_200 === 'number' &&
                         !Number.isNaN(technicalIndicators.moving_averages.sma_200) && (
                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground">SMA (200)</p>
                            <div className="text-lg font-semibold">{technicalIndicators.moving_averages.sma_200.toFixed(2)}</div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
          
          <TabsContent value="orders" className="mt-6">
            <ErrorBoundary>
              <OrderForm />
            </ErrorBoundary>
          </TabsContent>
          
          <TabsContent value="portfolio" className="mt-6">
            <ErrorBoundary>
              <PortfolioView />
            </ErrorBoundary>
          </TabsContent>
          
          <TabsContent value="market" className="mt-6">
            <ErrorBoundary>
              <MarketData />
            </ErrorBoundary>
          </TabsContent>
          
          <TabsContent value="predictions" className="mt-6">
            <ErrorBoundary>
              <StockPredictionTab />
            </ErrorBoundary>
          </TabsContent>
          
          <TabsContent value="backtest" className="mt-6">
            <ErrorBoundary>
              <BacktestTab />
            </ErrorBoundary>
          </TabsContent>
        </Tabs>
      </div>
    );
  };

  const renderBankingTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Balance</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {bankingMetrics ? `$${bankingMetrics.total_balance.toLocaleString()}` : '—'}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Connected Accounts</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {bankingMetrics?.connected_accounts || 0}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Transactions</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {bankingMetrics?.pending_transactions || 0}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const renderRiskTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Sharpe Ratio</CardTitle>
            <CardDescription>Risk-adjusted return measure</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {riskMetrics?.sharpe_ratio ? riskMetrics.sharpe_ratio.toFixed(2) : 'N/A'}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Beta</CardTitle>
            <CardDescription>Market correlation measure</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {riskMetrics?.beta ? riskMetrics.beta.toFixed(2) : 'N/A'}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>VaR (95%)</CardTitle>
            <CardDescription>Value at Risk at 95% confidence</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-400">
              {riskMetrics?.var_95 ? `$${Math.abs(riskMetrics.var_95).toLocaleString()}` : 'N/A'}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Max Drawdown</CardTitle>
            <CardDescription>Maximum peak-to-trough decline</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-400">
              {riskMetrics?.max_drawdown ? `${(riskMetrics.max_drawdown * 100).toFixed(2)}%` : 'N/A'}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
        <TabsList>
          <TabsTrigger value="overview">
            <Layers className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="trading">
            <TrendingUp className="h-4 w-4 mr-2" />
            Trading
          </TabsTrigger>
          <TabsTrigger value="banking">
            <Building2 className="h-4 w-4 mr-2" />
            Banking
          </TabsTrigger>
          <TabsTrigger value="risk">
            <AlertTriangle className="h-4 w-4 mr-2" />
            Risk
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="mt-6">
          {renderOverviewTab()}
        </TabsContent>
        
        <TabsContent value="trading" className="mt-6">
          {renderTradingTab()}
        </TabsContent>
        
        <TabsContent value="banking" className="mt-6">
          {renderBankingTab()}
        </TabsContent>
        
        <TabsContent value="risk" className="mt-6">
          {renderRiskTab()}
        </TabsContent>
      </Tabs>
    </div>
  );
}
