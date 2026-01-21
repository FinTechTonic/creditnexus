/**
 * Trading Dashboard Component
 * 
 * Main trading dashboard with order placement, portfolio view, and market data.
 * Integrated with the unified dashboard system.
 */

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { OrderForm } from './OrderForm';
import { PortfolioView } from './PortfolioView';
import { MarketData } from './MarketData';
import { OrderHistory } from './OrderHistory';
import { StockPredictionTab } from './StockPredictionTab';
import { BacktestTab } from './BacktestTab';
import { StructuredProductsTab } from './StructuredProductsTab';
import { TrendingUp, Wallet, BarChart3, History, LineChart, BarChart2, Layers } from 'lucide-react';
import { PermissionGate } from '@/components/PermissionGate';
import { PERMISSION_TRADE_EXECUTE, PERMISSION_TRADE_VIEW } from '@/utils/permissions';

export function TradingDashboard() {
  const [activeTab, setActiveTab] = useState('orders');

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Trading Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Place orders, monitor positions, and track market data
            </p>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 sm:grid-cols-3 lg:grid-cols-7">
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
            <PortfolioView />
          </TabsContent>

          <TabsContent value="market" className="space-y-4 mt-6">
            <MarketData />
          </TabsContent>

          <TabsContent value="predictions" className="space-y-4 mt-6">
            <StockPredictionTab />
          </TabsContent>

          <TabsContent value="backtest" className="space-y-4 mt-6">
            <BacktestTab />
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
