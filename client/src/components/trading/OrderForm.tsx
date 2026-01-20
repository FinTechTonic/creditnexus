/**
 * Order Form Component
 * 
 * Form component for placing buy/sell orders with order type selection.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TrendingUp, TrendingDown, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';

type OrderSide = 'buy' | 'sell';
type OrderType = 'market' | 'limit' | 'stop';

interface OrderFormData {
  side: OrderSide;
  type: OrderType;
  symbol: string;
  quantity: string;
  price?: string;
  stopPrice?: string;
}

interface OrderResponse {
  order_id: string;
  status: 'pending' | 'filled' | 'cancelled' | 'rejected';
  message?: string;
}

export function OrderForm() {
  const [orderSide, setOrderSide] = useState<OrderSide>('buy');
  const [orderData, setOrderData] = useState<OrderFormData>({
    side: 'buy',
    type: 'market',
    symbol: '',
    quantity: '',
    price: '',
    stopPrice: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [orderResponse, setOrderResponse] = useState<OrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSideChange = (side: OrderSide) => {
    setOrderSide(side);
    setOrderData(prev => ({ ...prev, side }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setOrderResponse(null);
    setIsSubmitting(true);

    try {
      // Validate form data
      if (!orderData.symbol.trim()) {
        throw new Error('Symbol is required');
      }
      if (!orderData.quantity || parseFloat(orderData.quantity) <= 0) {
        throw new Error('Quantity must be greater than 0');
      }
      if (orderData.type === 'limit' && (!orderData.price || parseFloat(orderData.price) <= 0)) {
        throw new Error('Limit price is required for limit orders');
      }
      if (orderData.type === 'stop' && (!orderData.stopPrice || parseFloat(orderData.stopPrice) <= 0)) {
        throw new Error('Stop price is required for stop orders');
      }

      const payload: Record<string, unknown> = {
        side: orderData.side,
        type: orderData.type,
        symbol: orderData.symbol.trim().toUpperCase(),
        quantity: parseFloat(orderData.quantity),
      };

      if (orderData.type === 'limit' && orderData.price) {
        payload.price = parseFloat(orderData.price);
      }
      if (orderData.type === 'stop' && orderData.stopPrice) {
        payload.stop_price = parseFloat(orderData.stopPrice);
      }

      const apiUrl = resolveApiUrl('/api/trades/orders');
      const response = await fetchWithAuth(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to place order' }));
        throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}: Failed to place order`);
      }

      const result: OrderResponse = await response.json();
      setOrderResponse(result);

      // Reset form on success
      if (result.status === 'filled' || result.status === 'pending') {
        setOrderData({
          side: orderSide,
          type: 'market',
          symbol: '',
          quantity: '',
          price: '',
          stopPrice: '',
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to place order');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Place Order</CardTitle>
          <CardDescription>
            Enter order details and submit to execute a trade
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={orderSide} onValueChange={(v) => handleSideChange(v as OrderSide)} className="mb-6">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="buy" className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Buy
              </TabsTrigger>
              <TabsTrigger value="sell" className="flex items-center gap-2">
                <TrendingDown className="h-4 w-4" />
                Sell
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Input
                id="symbol"
                placeholder="e.g., DEAL_2024_001"
                value={orderData.symbol}
                onChange={(e) => setOrderData(prev => ({ ...prev, symbol: e.target.value }))}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="orderType">Order Type</Label>
              <Select
                id="orderType"
                value={orderData.type}
                onValueChange={(value) => setOrderData(prev => ({ ...prev, type: value as OrderType }))}
              >
                <option value="market">Market</option>
                <option value="limit">Limit</option>
                <option value="stop">Stop</option>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="quantity">Quantity</Label>
              <Input
                id="quantity"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={orderData.quantity}
                onChange={(e) => setOrderData(prev => ({ ...prev, quantity: e.target.value }))}
                required
              />
            </div>

            {orderData.type === 'limit' && (
              <div className="space-y-2">
                <Label htmlFor="price">Limit Price</Label>
                <Input
                  id="price"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={orderData.price}
                  onChange={(e) => setOrderData(prev => ({ ...prev, price: e.target.value }))}
                  required
                />
              </div>
            )}

            {orderData.type === 'stop' && (
              <div className="space-y-2">
                <Label htmlFor="stopPrice">Stop Price</Label>
                <Input
                  id="stopPrice"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={orderData.stopPrice}
                  onChange={(e) => setOrderData(prev => ({ ...prev, stopPrice: e.target.value }))}
                  required
                />
              </div>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {orderResponse && (
              <Alert variant={orderResponse.status === 'rejected' ? 'destructive' : 'default'}>
                {orderResponse.status !== 'rejected' ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <AlertTriangle className="h-4 w-4" />
                )}
                <AlertDescription>
                  <div className="font-semibold">
                    Order {orderResponse.status === 'rejected' ? 'Rejected' : 'Placed'}
                  </div>
                  <div className="text-sm mt-1">
                    Order ID: {orderResponse.order_id}
                    {orderResponse.message && ` - ${orderResponse.message}`}
                  </div>
                </AlertDescription>
              </Alert>
            )}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Placing Order...
                </>
              ) : (
                `${orderSide === 'buy' ? 'Buy' : 'Sell'} ${orderData.type === 'market' ? 'Market' : orderData.type === 'limit' ? 'Limit' : 'Stop'} Order`
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Order Preview</CardTitle>
          <CardDescription>
            Review your order before submission
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-muted-foreground">Side</div>
              <div className="font-semibold capitalize">{orderSide}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Type</div>
              <div className="font-semibold capitalize">{orderData.type}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Symbol</div>
              <div className="font-semibold">{orderData.symbol || '—'}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Quantity</div>
              <div className="font-semibold">{orderData.quantity || '—'}</div>
            </div>
            {orderData.type === 'limit' && orderData.price && (
              <div>
                <div className="text-muted-foreground">Limit Price</div>
                <div className="font-semibold">{orderData.price}</div>
              </div>
            )}
            {orderData.type === 'stop' && orderData.stopPrice && (
              <div>
                <div className="text-muted-foreground">Stop Price</div>
                <div className="font-semibold">{orderData.stopPrice}</div>
              </div>
            )}
          </div>

          {(orderData.type === 'limit' || orderData.type === 'stop') && 
           (orderData.price || orderData.stopPrice) && 
           orderData.quantity && (
            <div className="pt-4 border-t">
              <div className="text-muted-foreground text-sm mb-1">Estimated Value</div>
              <div className="text-2xl font-bold">
                ${((parseFloat(orderData.price || orderData.stopPrice || '0')) * parseFloat(orderData.quantity || '0')).toFixed(2)}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
