/**
 * Bank products marketplace (Week 14).
 * Display user's bank-held products (from Plaid), marketplace listings, sell form, and configurable flat fee.
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { DollarSign, Store, Package } from 'lucide-react';

interface BankProduct {
  id: string;
  symbol?: string;
  name: string;
  quantity?: number;
  market_value?: number;
  current_price?: number;
  product_type?: string;
}

interface Listing {
  id: number;
  user_id: number;
  name: string;
  product_type?: string;
  asking_price: number;
  flat_fee: number;
  status: string;
  created_at?: string;
}

export function BankProductsMarketplace() {
  const [products, setProducts] = useState<BankProduct[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [listingsLoading, setListingsLoading] = useState(true);
  const [sellName, setSellName] = useState('');
  const [sellPrice, setSellPrice] = useState('');
  const [sellLoading, setSellLoading] = useState(false);
  const [sellError, setSellError] = useState<string | null>(null);

  const loadProducts = useCallback(async () => {
    try {
      const r = await fetchWithAuth('/api/bank-products');
      if (r.ok) {
        const data = await r.json();
        setProducts(data.products ?? []);
      } else {
        setProducts([]);
      }
    } catch {
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadListings = useCallback(async () => {
    setListingsLoading(true);
    try {
      const r = await fetchWithAuth('/api/bank-products/marketplace?limit=50');
      if (r.ok) {
        const data = await r.json();
        setListings(data.listings ?? []);
      } else {
        setListings([]);
      }
    } catch {
      setListings([]);
    } finally {
      setListingsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);
  useEffect(() => {
    loadListings();
  }, [loadListings]);

  const handleSell = async () => {
    const name = sellName.trim();
    const price = parseFloat(sellPrice);
    if (!name || !price || price <= 0) return;
    setSellLoading(true);
    setSellError(null);
    try {
      const r = await fetchWithAuth('/api/bank-products/sell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, asking_price: price.toFixed(2) }),
      });
      if (r.ok) {
        setSellName('');
        setSellPrice('');
        loadListings();
      } else {
        const err = await r.json().catch(() => ({}));
        setSellError(err.detail || 'Failed to create listing');
      }
    } catch (e) {
      setSellError('Failed to create listing');
    } finally {
      setSellLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-100 flex items-center gap-2">
          <Store className="h-6 w-6" />
          Bank Products Marketplace
        </h2>
        <p className="text-slate-400 text-sm mt-1">
          View your bank-held investments and list products for sale (configurable flat fee applies).
        </p>
      </div>

      <Card className="bg-slate-900/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <Package className="h-5 w-5" />
            Sell a product
          </CardTitle>
          <CardDescription className="text-slate-400">
            Create a marketplace listing. A flat fee may apply per listing.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label className="text-slate-300">Product name</Label>
              <Input
                value={sellName}
                onChange={(e) => setSellName(e.target.value)}
                placeholder="e.g. Equity XYZ"
                className="mt-1 bg-slate-800 border-slate-600 text-slate-100"
              />
            </div>
            <div>
              <Label className="text-slate-300">Asking price (USD)</Label>
              <Input
                type="number"
                min="0.01"
                step="0.01"
                value={sellPrice}
                onChange={(e) => setSellPrice(e.target.value)}
                placeholder="0.00"
                className="mt-1 bg-slate-800 border-slate-600 text-slate-100"
              />
            </div>
          </div>
          {sellError && <p className="text-sm text-red-400">{sellError}</p>}
          <Button
            onClick={handleSell}
            disabled={!sellName.trim() || !sellPrice || parseFloat(sellPrice) <= 0 || sellLoading}
          >
            {sellLoading ? 'Creating…' : 'List for sale'}
          </Button>
        </CardContent>
      </Card>

      <Card className="bg-slate-900/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Products for sale</CardTitle>
          <CardDescription className="text-slate-400">Marketplace listings</CardDescription>
        </CardHeader>
        <CardContent>
          {listingsLoading ? (
            <p className="text-slate-400">Loading listings…</p>
          ) : listings.length === 0 ? (
            <p className="text-slate-400">No products listed yet.</p>
          ) : (
            <ul className="space-y-3">
              {listings.map((l) => (
                <li
                  key={l.id}
                  className="flex items-center justify-between py-2 border-b border-slate-700 last:border-0"
                >
                  <div>
                    <span className="font-medium text-slate-100">{l.name}</span>
                    {l.product_type && (
                      <span className="ml-2 text-xs text-slate-500">{l.product_type}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-slate-300">
                      <DollarSign className="inline h-4 w-4 mr-1" />
                      {l.asking_price.toFixed(2)}
                    </span>
                    {l.flat_fee > 0 && (
                      <span className="text-xs text-slate-500">Fee: ${l.flat_fee.toFixed(2)}</span>
                    )}
                    <span className="text-xs text-slate-500">{l.status}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="bg-slate-900/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Your bank-held products</CardTitle>
          <CardDescription className="text-slate-400">From connected Plaid accounts (investments)</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-slate-400">Loading…</p>
          ) : products.length === 0 ? (
            <p className="text-slate-400">Connect a bank (Plaid) to see investment products here.</p>
          ) : (
            <ul className="space-y-3">
              {products.map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between py-2 border-b border-slate-700 last:border-0"
                >
                  <div>
                    <span className="font-medium text-slate-100">{p.name || p.symbol}</span>
                    {p.product_type && (
                      <span className="ml-2 text-xs text-slate-500">{p.product_type}</span>
                    )}
                  </div>
                  <div className="text-slate-300">
                    {p.market_value != null && (
                      <>
                        <DollarSign className="inline h-4 w-4 mr-1" />
                        {p.market_value.toFixed(2)}
                      </>
                    )}
                    {p.quantity != null && (
                      <span className="ml-2 text-xs text-slate-500">qty {p.quantity}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
