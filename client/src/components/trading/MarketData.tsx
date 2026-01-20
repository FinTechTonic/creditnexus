/**
 * Market Data Component
 * 
 * Displays real-time prices, order book, trade history, and charts.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';

interface MarketPrice {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  bid: number;
  ask: number;
  timestamp: string;
}

interface OrderBookEntry {
  price: number;
  quantity: number;
  side: 'bid' | 'ask';
}

interface Trade {
  id: string;
  symbol: string;
  price: number;
  quantity: number;
  side: 'buy' | 'sell';
  timestamp: string;
}

interface MarketDataState {
  prices: MarketPrice[];
  orderBook: OrderBookEntry[];
  recentTrades: Trade[];
}

export function MarketData() {
  const [marketData, setMarketData] = useState<MarketDataState>({
    prices: [],
    orderBook: [],
    recentTrades: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');

  const loadMarketData = async () => {
    try {
      const apiUrl = resolveApiUrl('/api/trades/market-data');
      const response = await fetchWithAuth(apiUrl, {
        method: 'GET',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to load market data' }));
        throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}: Failed to load market data`);
      }

      const data: MarketDataState = await response.json();
      setMarketData(data);
      if (data.prices.length > 0 && !selectedSymbol) {
        setSelectedSymbol(data.prices[0].symbol);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load market data');
      // Set mock data for development
      setMarketData({
        prices: [
          {
            symbol: 'DEAL_2024_001',
            price: 100.50,
            change: 2.50,
            change_percent: 2.55,
            volume: 1000000,
            bid: 100.45,
            ask: 100.55,
            timestamp: new Date().toISOString(),
          },
        ],
        orderBook: [],
        recentTrades: [],
      });
    }
  };

  useEffect(() => {
    const initializeMarketData = async () => {
      await loadMarketData();
      setIsLoading(false);
    };

    initializeMarketData();

    // Refresh market data every 5 seconds
    const interval = setInterval(() => {
      setIsRefreshing(true);
      loadMarketData().finally(() => setIsRefreshing(false));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadMarketData();
    setIsRefreshing(false);
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="text-center text-muted-foreground">
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const selectedPrice = marketData.prices.find(p => p.symbol === selectedSymbol);

  return (
    <div className="space-y-6">
      {/* Market Prices */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Market Prices</CardTitle>
              <CardDescription>Real-time prices and market data</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {marketData.prices.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-sm">No market data available</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                {marketData.prices.map((price) => (
                  <Card
                    key={price.symbol}
                    className={`cursor-pointer transition-colors ${
                      selectedSymbol === price.symbol ? 'ring-2 ring-primary' : ''
                    }`}
                    onClick={() => setSelectedSymbol(price.symbol)}
                  >
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-semibold">{price.symbol}</div>
                        {price.change >= 0 ? (
                          <TrendingUp className="h-4 w-4 text-green-500" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                      <div className={`text-2xl font-bold ${
                        price.change >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}>
                        ${price.price.toFixed(2)}
                      </div>
                      <div className={`text-sm mt-1 ${
                        price.change >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}>
                        {price.change >= 0 ? '+' : ''}{price.change.toFixed(2)} ({price.change_percent.toFixed(2)}%)
                      </div>
                      <div className="text-xs text-muted-foreground mt-2">
                        Volume: {price.volume.toLocaleString()}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {selectedPrice && (
                <Card>
                  <CardHeader>
                    <CardTitle>{selectedPrice.symbol} Details</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <div className="text-sm text-muted-foreground">Bid</div>
                        <div className="text-lg font-semibold">${selectedPrice.bid.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Ask</div>
                        <div className="text-lg font-semibold">${selectedPrice.ask.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Spread</div>
                        <div className="text-lg font-semibold">
                          ${(selectedPrice.ask - selectedPrice.bid).toFixed(2)}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Order Book */}
      {selectedSymbol && (
        <Card>
          <CardHeader>
            <CardTitle>Order Book - {selectedSymbol}</CardTitle>
            <CardDescription>Live order book data</CardDescription>
          </CardHeader>
          <CardContent>
            {marketData.orderBook.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <p className="text-sm">No order book data available</p>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <div className="font-semibold mb-2 text-green-500">Bids</div>
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {marketData.orderBook
                      .filter(entry => entry.side === 'bid')
                      .map((entry, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span>${entry.price.toFixed(2)}</span>
                          <span>{entry.quantity.toLocaleString()}</span>
                        </div>
                      ))}
                  </div>
                </div>
                <div>
                  <div className="font-semibold mb-2 text-red-500">Asks</div>
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {marketData.orderBook
                      .filter(entry => entry.side === 'ask')
                      .map((entry, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span>${entry.price.toFixed(2)}</span>
                          <span>{entry.quantity.toLocaleString()}</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Recent Trades */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Trades</CardTitle>
          <CardDescription>Latest executed trades</CardDescription>
        </CardHeader>
        <CardContent>
          {marketData.recentTrades.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-sm">No recent trades</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2 font-medium">Time</th>
                    <th className="text-left p-2 font-medium">Symbol</th>
                    <th className="text-right p-2 font-medium">Price</th>
                    <th className="text-right p-2 font-medium">Quantity</th>
                    <th className="text-center p-2 font-medium">Side</th>
                  </tr>
                </thead>
                <tbody>
                  {marketData.recentTrades.map((trade) => (
                    <tr key={trade.id} className="border-b">
                      <td className="p-2 text-sm">
                        {new Date(trade.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="p-2 font-medium">{trade.symbol}</td>
                      <td className="p-2 text-right">${trade.price.toFixed(2)}</td>
                      <td className="p-2 text-right">{trade.quantity.toFixed(2)}</td>
                      <td className={`p-2 text-center font-medium ${
                        trade.side === 'buy' ? 'text-green-500' : 'text-red-500'
                      }`}>
                        {trade.side.toUpperCase()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
