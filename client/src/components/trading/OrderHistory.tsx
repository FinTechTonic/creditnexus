/**
 * Order History Component
 * 
 * Displays order history with status, execution details, and filtering.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Loader2, Search } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useFDC3 } from '@/context/FDC3Context';
import { resolveApiUrl } from '@/utils/apiBase';

interface Order {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit' | 'stop';
  quantity: number;
  price?: number;
  stop_price?: number;
  status: 'pending' | 'filled' | 'cancelled' | 'rejected' | 'partially_filled';
  filled_quantity?: number;
  average_price?: number;
  created_at: string;
  updated_at: string;
  executed_at?: string;
}

export function OrderHistory() {
  const { context } = useFDC3();
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sideFilter, setSideFilter] = useState<string>('all');

  // Listen for FDC3 context updates (e.g., new order placed or instrument selected)
  useEffect(() => {
    if (
      context?.type === 'fdc3.instrument' ||
      context?.type === 'finos.creditnexus.instrument' ||
      context?.type === 'finos.creditnexus.stockPrediction'
    ) {
      // Instrument or prediction context received - refresh history to show new orders
      loadOrderHistory();
    }
  }, [context]);

  const loadOrderHistory = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const apiUrl = resolveApiUrl('/api/trades/orders/history');
      const response = await fetchWithAuth(apiUrl, {
        method: 'GET',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to load order history' }));
        throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}: Failed to load order history`);
      }

      const raw: unknown[] = await response.json();
      // Map trading API (order_id, order_type, average_fill_price) to UI shape (id, type, average_price)
      const data: Order[] = raw.map((o: any) => ({
        ...o,
        id: String(o?.order_id ?? o?.id ?? ''),
        type: o?.order_type ?? o?.type ?? 'market',
        average_price: o?.average_fill_price ?? o?.average_price,
      }));
      setOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load order history');
      setOrders([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadOrderHistory();
  }, []);

  const filteredOrders = orders.filter(order => {
    const matchesSearch = order.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         order.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || order.status === statusFilter;
    const matchesSide = sideFilter === 'all' || order.side === sideFilter;
    return matchesSearch && matchesStatus && matchesSide;
  });

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      filled: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
      rejected: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      partially_filled: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    };
    return colors[status] || colors.pending;
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

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Order History</CardTitle>
          <CardDescription>View and filter your order history</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by symbol or order ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={statusFilter}
              onValueChange={setStatusFilter}
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="filled">Filled</option>
              <option value="partially_filled">Partially Filled</option>
              <option value="cancelled">Cancelled</option>
              <option value="rejected">Rejected</option>
            </Select>
            <Select
              value={sideFilter}
              onValueChange={setSideFilter}
            >
              <option value="all">All Sides</option>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Orders Table */}
      <Card>
        <CardContent className="pt-6">
          {filteredOrders.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-sm">No orders found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2 font-medium">Order ID</th>
                    <th className="text-left p-2 font-medium">Symbol</th>
                    <th className="text-center p-2 font-medium">Side</th>
                    <th className="text-center p-2 font-medium">Type</th>
                    <th className="text-right p-2 font-medium">Quantity</th>
                    <th className="text-right p-2 font-medium">Price</th>
                    <th className="text-center p-2 font-medium">Status</th>
                    <th className="text-right p-2 font-medium">Filled</th>
                    <th className="text-right p-2 font-medium">Avg Price</th>
                    <th className="text-left p-2 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map((order) => (
                    <tr key={order.id} className="border-b">
                      <td className="p-2 text-sm font-mono">{order.id}</td>
                      <td className="p-2 font-medium">{order.symbol}</td>
                      <td className={`p-2 text-center font-medium ${
                        order.side === 'buy' ? 'text-green-500' : 'text-red-500'
                      }`}>
                        {order.side.toUpperCase()}
                      </td>
                      <td className="p-2 text-center capitalize">{order.type}</td>
                      <td className="p-2 text-right">{order.quantity.toFixed(2)}</td>
                      <td className="p-2 text-right">
                        {order.price ? `$${order.price.toFixed(2)}` : '—'}
                      </td>
                      <td className="p-2 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadge(order.status)}`}>
                          {order.status.replace('_', ' ').toUpperCase()}
                        </span>
                      </td>
                      <td className="p-2 text-right">
                        {order.filled_quantity !== undefined
                          ? `${order.filled_quantity.toFixed(2)} / ${order.quantity.toFixed(2)}`
                          : '—'}
                      </td>
                      <td className="p-2 text-right">
                        {order.average_price ? `$${order.average_price.toFixed(2)}` : '—'}
                      </td>
                      <td className="p-2 text-sm text-muted-foreground">
                        {new Date(order.created_at).toLocaleDateString()}
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
