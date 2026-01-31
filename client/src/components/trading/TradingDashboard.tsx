/**
 * Trading Dashboard Component
 * 
 * Main trading dashboard with order placement, portfolio view, and market data.
 * Integrated with the unified dashboard system.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { OrderForm } from './OrderForm';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';
import { Link } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { PortfolioView } from './PortfolioView';
import { MarketData } from './MarketData';
import { OrderHistory } from './OrderHistory';
import { StockPredictionTab } from './StockPredictionTab';
import { BacktestTab } from './BacktestTab';
import { StructuredProductsTab } from './StructuredProductsTab';
import { Watchlists } from './Watchlists';
import { PriceAlerts } from './PriceAlerts';
import { PerformanceAnalytics } from './PerformanceAnalytics';
import { Newsfeed } from '@/components/dashboard-tabs/Newsfeed';
import { TrendingUp, Wallet, BarChart3, History, LineChart, BarChart2, Layers, Eye, Bell, Share2 } from 'lucide-react';
import { PermissionGate } from '@/components/PermissionGate';
import { PERMISSION_TRADE_EXECUTE, PERMISSION_TRADE_VIEW } from '@/utils/permissions';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export function TradingDashboard() {
  // Persist activeTab in sessionStorage to survive re-renders
  const getInitialTab = () => {
    try {
      const saved = sessionStorage.getItem('tradingDashboardActiveTab');
      return saved && ['orders', 'portfolio', 'market', 'newsfeed', 'watchlists', 'alerts', 'predictions', 'backtest', 'history', 'structured'].includes(saved)
        ? saved
        : 'orders';
    } catch {
      return 'orders';
    }
  };
  
  const [activeTab, setActiveTab] = useState(getInitialTab);
  const isInitialMount = useRef(true);
  const [brokerageStatus, setBrokerageStatus] = useState<{ has_account: boolean; status?: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchWithAuth(resolveApiUrl('/api/brokerage/account/status'))
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (!cancelled && d) setBrokerageStatus(d); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const brokerageGate = brokerageStatus?.has_account && brokerageStatus?.status !== 'ACTIVE';

  // Save tab to sessionStorage whenever it changes
  useEffect(() => {
    if (!isInitialMount.current) {
      try {
        sessionStorage.setItem('tradingDashboardActiveTab', activeTab);
      } catch (e) {
        console.debug('Failed to save activeTab to sessionStorage:', e);
      }
    } else {
      isInitialMount.current = false;
    }
  }, [activeTab]);

  // Prevent tab from resetting if there's an error or re-render
  const handleTabChange = useCallback((value: string) => {
    try {
      if (value && value !== activeTab) {
        setActiveTab(value);
      }
    } catch (e) {
      console.error('Error changing tab:', e);
    }
  }, [activeTab]);

  return (
    <PermissionGate
      permissions={[PERMISSION_TRADE_VIEW, PERMISSION_TRADE_EXECUTE]}
      requireAll={false}
      fallback={
        <Card className="shadow-lg border-0">
          <CardHeader className="text-center py-12">
            <CardTitle className="text-muted-foreground">Access Denied</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              You don't have permission to access the trading dashboard
            </p>
          </CardHeader>
        </Card>
      }
    >
      <div className="space-y-6 p-6">
        {brokerageGate && (
          <Alert variant="destructive" className="border-amber-700 bg-amber-900/20">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Your trading account is not yet active ({brokerageStatus?.status ?? 'pending'}). Complete onboarding in{' '}
              <Link to="/settings" className="underline font-medium">Settings → Trading account</Link> to place orders.
            </AlertDescription>
          </Alert>
        )}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Trading Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Place orders, monitor positions, and track market data
            </p>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid w-full grid-cols-2 sm:grid-cols-3 lg:grid-cols-10">
            <TabsTrigger value="orders" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              <span className="hidden sm:inline">Orders</span>
            </TabsTrigger>
            <TabsTrigger value="portfolio" className="flex items-center gap-2">
              <Wallet className="h-4 w-4" />
              <span className="hidden sm:inline">Portfolio</span>
            </TabsTrigger>
            <TabsTrigger value="market" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Market</span>
            </TabsTrigger>
            <TabsTrigger value="newsfeed" className="flex items-center gap-2">
              <Share2 className="h-4 w-4" />
              <span className="hidden sm:inline">Newsfeed</span>
            </TabsTrigger>
            <TabsTrigger value="watchlists" className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              <span className="hidden sm:inline">Watchlists</span>
            </TabsTrigger>
            <TabsTrigger value="alerts" className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              <span className="hidden sm:inline">Alerts</span>
            </TabsTrigger>
            <TabsTrigger value="predictions" className="flex items-center gap-2">
              <LineChart className="h-4 w-4" />
              <span className="hidden sm:inline">Predictions</span>
            </TabsTrigger>
            <TabsTrigger value="backtest" className="flex items-center gap-2">
              <BarChart2 className="h-4 w-4" />
              <span className="hidden sm:inline">Backtest</span>
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center gap-2">
              <History className="h-4 w-4" />
              <span className="hidden sm:inline">History</span>
            </TabsTrigger>
            <TabsTrigger value="structured" className="flex items-center gap-2">
              <Layers className="h-4 w-4" />
              <span className="hidden sm:inline">Structured</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="orders" className="space-y-4 mt-6">
            <OrderForm />
          </TabsContent>

          <TabsContent value="portfolio" className="space-y-4 mt-6">
            <div className="space-y-6">
              <PortfolioView />
              <PerformanceAnalytics />
            </div>
          </TabsContent>

          <TabsContent value="market" className="space-y-4 mt-6">
            <MarketData
              onRunPrediction={() => handleTabChange('predictions')}
              onRunBacktest={() => handleTabChange('backtest')}
            />
          </TabsContent>

          <TabsContent value="newsfeed" className="space-y-4 mt-6">
            <Newsfeed />
          </TabsContent>

          <TabsContent value="watchlists" className="space-y-4 mt-6">
            <Watchlists />
          </TabsContent>

          <TabsContent value="alerts" className="space-y-4 mt-6">
            <PriceAlerts />
          </TabsContent>

          <TabsContent value="predictions" className="space-y-4 mt-6">
            <ErrorBoundary>
              <StockPredictionTab />
            </ErrorBoundary>
          </TabsContent>

          <TabsContent value="backtest" className="space-y-4 mt-6">
            <ErrorBoundary>
              <BacktestTab />
            </ErrorBoundary>
          </TabsContent>

          <TabsContent value="history" className="space-y-4 mt-6">
            <OrderHistory />
          </TabsContent>
          <TabsContent value="structured" className="space-y-4 mt-6">
            <StructuredProductsTab />
          </TabsContent>
        </Tabs>
      </div>
    </PermissionGate>
  );
}
