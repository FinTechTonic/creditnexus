/**
 * Price Alerts Component
 * 
 * Manage price alerts for monitoring symbol price movements.
 * Backend API: /api/trades/price-alerts
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { 
  Plus, Trash2, Bell, BellOff, Loader2, 
  TrendingUp, TrendingDown, Activity
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';

interface PriceAlert {
  id: number;
  user_id: number;
  symbol: string;
  alert_type: 'above' | 'below' | 'change_percent';
  target_price?: number;
  change_percent?: number;
  is_active: boolean;
  triggered_at?: string;
  triggered_price?: number;
  notify_email: boolean;
  notify_in_app: boolean;
  created_at: string;
  updated_at: string;
}

export function PriceAlerts() {
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  
  const [newSymbol, setNewSymbol] = useState('');
  const [newAlertType, setNewAlertType] = useState<'above' | 'below' | 'change_percent'>('above');
  const [newTargetPrice, setNewTargetPrice] = useState('');
  const [newChangePercent, setNewChangePercent] = useState('');
  const [newNotifyEmail, setNewNotifyEmail] = useState(false);
  const [newNotifyInApp, setNewNotifyInApp] = useState(true);

  const loadAlerts = async () => {
    try {
      const apiUrl = resolveApiUrl('/api/trades/price-alerts');
      const response = await fetchWithAuth(apiUrl, { method: 'GET' });
      
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to load price alerts' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }
      
      const data: PriceAlert[] = await response.json();
      setAlerts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load price alerts');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
    
    // Refresh alerts every 30 seconds
    const interval = setInterval(loadAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = async () => {
    if (!newSymbol.trim()) {
      setError('Symbol is required');
      return;
    }

    if (newAlertType !== 'change_percent' && !newTargetPrice) {
      setError('Target price is required for above/below alerts');
      return;
    }

    if (newAlertType === 'change_percent' && !newChangePercent) {
      setError('Change percent is required for change alerts');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const apiUrl = resolveApiUrl('/api/trades/price-alerts');
      const payload: Record<string, unknown> = {
        symbol: newSymbol.trim().toUpperCase(),
        alert_type: newAlertType,
        notify_email: newNotifyEmail,
        notify_in_app: newNotifyInApp,
      };

      if (newAlertType !== 'change_percent' && newTargetPrice) {
        payload.target_price = parseFloat(newTargetPrice);
      }

      if (newAlertType === 'change_percent' && newChangePercent) {
        payload.change_percent = parseFloat(newChangePercent);
      }

      const response = await fetchWithAuth(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to create alert' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }

      // Reset form
      setNewSymbol('');
      setNewTargetPrice('');
      setNewChangePercent('');
      setNewNotifyEmail(false);
      setNewNotifyInApp(true);
      
      await loadAlerts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create alert');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this alert?')) {
      return;
    }

    setError(null);

    try {
      const apiUrl = resolveApiUrl(`/api/trades/price-alerts/${id}`);
      const response = await fetchWithAuth(apiUrl, { method: 'DELETE' });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to delete alert' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }

      await loadAlerts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete alert');
    }
  };

  const handleToggle = async (id: number) => {
    setError(null);

    try {
      const apiUrl = resolveApiUrl(`/api/trades/price-alerts/${id}/toggle`);
      const response = await fetchWithAuth(apiUrl, { method: 'PUT' });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to toggle alert' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }

      await loadAlerts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle alert');
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const activeAlerts = alerts.filter(a => a.is_active);
  const triggeredAlerts = alerts.filter(a => a.triggered_at);

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Create New Alert */}
      <Card>
        <CardHeader>
          <CardTitle>Create Price Alert</CardTitle>
          <CardDescription>Get notified when a symbol reaches a target price</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="alert-symbol">Symbol</Label>
                <Input
                  id="alert-symbol"
                  placeholder="e.g., AAPL"
                  value={newSymbol}
                  onChange={(e) => setNewSymbol(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="alert-type">Alert Type</Label>
                <Select
                  id="alert-type"
                  value={newAlertType}
                  onValueChange={(value) => setNewAlertType(value as 'above' | 'below' | 'change_percent')}
                >
                  <option value="above">Price Above</option>
                  <option value="below">Price Below</option>
                  <option value="change_percent">Change %</option>
                </Select>
              </div>
            </div>

            {newAlertType !== 'change_percent' ? (
              <div className="space-y-2">
                <Label htmlFor="target-price">Target Price ($)</Label>
                <Input
                  id="target-price"
                  type="number"
                  step="0.01"
                  placeholder="e.g., 150.00"
                  value={newTargetPrice}
                  onChange={(e) => setNewTargetPrice(e.target.value)}
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="change-percent">Change Percent (%)</Label>
                <Input
                  id="change-percent"
                  type="number"
                  step="0.1"
                  placeholder="e.g., 5.0 for 5%"
                  value={newChangePercent}
                  onChange={(e) => setNewChangePercent(e.target.value)}
                />
              </div>
            )}

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="notify-email"
                  checked={newNotifyEmail}
                  onCheckedChange={setNewNotifyEmail}
                />
                <Label htmlFor="notify-email">Email Notification</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="notify-in-app"
                  checked={newNotifyInApp}
                  onCheckedChange={setNewNotifyInApp}
                />
                <Label htmlFor="notify-in-app">In-App Notification</Label>
              </div>
            </div>

            <Button onClick={handleCreate} disabled={isCreating}>
              {isCreating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Alert
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Active Alerts */}
      {activeAlerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Active Alerts ({activeAlerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {activeAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{alert.symbol}</span>
                      {alert.alert_type === 'above' ? (
                        <TrendingUp className="h-4 w-4 text-green-500" />
                      ) : alert.alert_type === 'below' ? (
                        <TrendingDown className="h-4 w-4 text-red-500" />
                      ) : (
                        <Activity className="h-4 w-4 text-blue-500" />
                      )}
                      <Badge variant="secondary">
                        {alert.alert_type === 'above' && `Above $${alert.target_price?.toFixed(2)}`}
                        {alert.alert_type === 'below' && `Below $${alert.target_price?.toFixed(2)}`}
                        {alert.alert_type === 'change_percent' && `${alert.change_percent}% change`}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {alert.notify_email && 'Email '}
                      {alert.notify_in_app && 'In-App'}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleToggle(alert.id)}
                    >
                      {alert.is_active ? <Bell className="h-4 w-4" /> : <BellOff className="h-4 w-4" />}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(alert.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Triggered Alerts */}
      {triggeredAlerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BellOff className="h-5 w-5" />
              Triggered Alerts ({triggeredAlerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {triggeredAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-center justify-between p-3 border rounded-lg bg-muted/50"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{alert.symbol}</span>
                      <Badge variant="outline">
                        Triggered at ${alert.triggered_price?.toFixed(2)}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {alert.triggered_at && new Date(alert.triggered_at).toLocaleString()}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(alert.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {alerts.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Bell className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No price alerts yet</p>
            <p className="text-sm text-muted-foreground mt-2">
              Create an alert to get notified when a symbol reaches a target price
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
