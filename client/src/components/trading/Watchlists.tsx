/**
 * Watchlists Component
 * 
 * Manage watchlists of stock symbols for monitoring.
 * Backend API: /api/trades/watchlists
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Plus, Trash2, Edit2, Save, X, Loader2, 
  Eye, EyeOff, Star, StarOff 
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';

interface Watchlist {
  id: number;
  name: string;
  symbols: string[];
  created_at: string;
  updated_at: string;
}

export function Watchlists() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [newWatchlistName, setNewWatchlistName] = useState('');
  const [newWatchlistSymbols, setNewWatchlistSymbols] = useState('');
  const [editName, setEditName] = useState('');
  const [editSymbols, setEditSymbols] = useState('');

  const loadWatchlists = async () => {
    try {
      const apiUrl = resolveApiUrl('/api/trades/watchlists');
      const response = await fetchWithAuth(apiUrl, { method: 'GET' });
      
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to load watchlists' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }
      
      const data: Watchlist[] = await response.json();
      setWatchlists(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load watchlists');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadWatchlists();
  }, []);

  const handleCreate = async () => {
    if (!newWatchlistName.trim()) {
      setError('Watchlist name is required');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const symbols = newWatchlistSymbols
        .split(',')
        .map(s => s.trim().toUpperCase())
        .filter(s => s.length > 0);

      const apiUrl = resolveApiUrl('/api/trades/watchlists');
      const response = await fetchWithAuth(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newWatchlistName.trim(),
          symbols,
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to create watchlist' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }

      setNewWatchlistName('');
      setNewWatchlistSymbols('');
      await loadWatchlists();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create watchlist');
    } finally {
      setIsCreating(false);
    }
  };

  const handleUpdate = async (id: number) => {
    setError(null);

    try {
      const symbols = editSymbols
        .split(',')
        .map(s => s.trim().toUpperCase())
        .filter(s => s.length > 0);

      const apiUrl = resolveApiUrl(`/api/trades/watchlists/${id}`);
      const response = await fetchWithAuth(apiUrl, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editName.trim() || undefined,
          symbols: symbols.length > 0 ? symbols : undefined,
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to update watchlist' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }

      setEditingId(null);
      await loadWatchlists();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update watchlist');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this watchlist?')) {
      return;
    }

    setError(null);

    try {
      const apiUrl = resolveApiUrl(`/api/trades/watchlists/${id}`);
      const response = await fetchWithAuth(apiUrl, { method: 'DELETE' });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to delete watchlist' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }

      await loadWatchlists();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete watchlist');
    }
  };

  const startEdit = (watchlist: Watchlist) => {
    setEditingId(watchlist.id);
    setEditName(watchlist.name);
    setEditSymbols(watchlist.symbols.join(', '));
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName('');
    setEditSymbols('');
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

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Create New Watchlist */}
      <Card>
        <CardHeader>
          <CardTitle>Create Watchlist</CardTitle>
          <CardDescription>Monitor a group of symbols together</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="watchlist-name">Watchlist Name</Label>
              <Input
                id="watchlist-name"
                placeholder="e.g., Tech Stocks, Energy Sector"
                value={newWatchlistName}
                onChange={(e) => setNewWatchlistName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="watchlist-symbols">Symbols (comma-separated)</Label>
              <Input
                id="watchlist-symbols"
                placeholder="e.g., AAPL, MSFT, GOOGL"
                value={newWatchlistSymbols}
                onChange={(e) => setNewWatchlistSymbols(e.target.value)}
              />
            </div>
            <Button onClick={handleCreate} disabled={isCreating || !newWatchlistName.trim()}>
              {isCreating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Watchlist
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Watchlists List */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {watchlists.length === 0 ? (
          <Card className="col-span-full">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <EyeOff className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No watchlists yet</p>
              <p className="text-sm text-muted-foreground mt-2">
                Create your first watchlist to start monitoring symbols
              </p>
            </CardContent>
          </Card>
        ) : (
          watchlists.map((watchlist) => (
            <Card key={watchlist.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  {editingId === watchlist.id ? (
                    <Input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="flex-1 mr-2"
                    />
                  ) : (
                    <CardTitle className="text-lg">{watchlist.name}</CardTitle>
                  )}
                  <div className="flex gap-2">
                    {editingId === watchlist.id ? (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleUpdate(watchlist.id)}
                        >
                          <Save className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={cancelEdit}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => startEdit(watchlist)}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDelete(watchlist.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {editingId === watchlist.id ? (
                  <div className="space-y-2">
                    <Label>Symbols (comma-separated)</Label>
                    <Input
                      value={editSymbols}
                      onChange={(e) => setEditSymbols(e.target.value)}
                      placeholder="AAPL, MSFT, GOOGL"
                    />
                  </div>
                ) : (
                  <div className="space-y-2">
                    {watchlist.symbols.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No symbols in this watchlist</p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {watchlist.symbols.map((symbol) => (
                          <Badge key={symbol} variant="secondary">
                            {symbol}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground mt-2">
                      {watchlist.symbols.length} symbol{watchlist.symbols.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
