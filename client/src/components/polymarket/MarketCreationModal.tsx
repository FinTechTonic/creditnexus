/**
 * Modal to create a prediction market for a deal.
 * Uses /api/polymarket/markets POST.
 */

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { fetchWithAuth } from '@/context/AuthContext';

interface Deal { id: number; deal_id: string; borrower_name?: string; status?: string }

interface MarketCreationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}

export function MarketCreationModal({ open, onOpenChange, onCreated }: MarketCreationModalProps) {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loadingDeals, setLoadingDeals] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [dealId, setDealId] = useState<string>('');
  const [question, setQuestion] = useState('');
  const [outcomeType, setOutcomeType] = useState<'binary' | 'categorical'>('binary');
  const [conditionType, setConditionType] = useState('NDVI_COMPLIANCE');
  const [threshold, setThreshold] = useState('0.5');
  const [anchorToBlockchain, setAnchorToBlockchain] = useState(true);
  const [publishToPolymarket, setPublishToPolymarket] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDealId('');
    setLoadingDeals(true);
    setError(null);
    fetchWithAuth('/api/deals?limit=100')
      .then((r) => r.ok ? r.json() : Promise.reject(new Error('Failed to load deals')))
      .then((d) => {
        const list = Array.isArray(d.deals) ? d.deals : [];
        setDeals(list);
        if (list.length > 0) setDealId(String(list[0].id));
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load deals'))
      .finally(() => setLoadingDeals(false));
  }, [open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const num = parseFloat(threshold);
    const resolution_condition: Record<string, unknown> = { type: conditionType };
    if (!Number.isNaN(num)) resolution_condition.threshold = num;

    try {
      const res = await fetchWithAuth('/api/polymarket/markets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deal_id: parseInt(dealId, 10),
          question: question.trim() || 'Will the resolution condition be met?',
          outcome_type: outcomeType,
          resolution_condition,
          market_event_type: conditionType,
          anchor_to_blockchain: anchorToBlockchain,
          visibility: 'public',
          publish_to_polymarket: publishToPolymarket,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.message || 'Failed to create market');
      onCreated();
      onOpenChange(false);
      setQuestion('');
      setDealId(deals[0] ? String(deals[0].id) : '');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create market');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create prediction market</DialogTitle>
          <DialogDescription>
            Create an SFP-backed prediction market for a deal. Optionally anchor the Merkle root on-chain.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <p className="text-sm text-destructive" role="alert">{error}</p>
          )}
          <div>
            <Label htmlFor="deal">Deal</Label>
            <Select id="deal" value={dealId} onValueChange={setDealId} required>
              <SelectTrigger>
                <SelectValue placeholder={loadingDeals ? 'Loading...' : 'Select deal'} />
              </SelectTrigger>
              <SelectContent>
                {deals.map((d) => (
                  <SelectItem key={d.id} value={String(d.id)}>
                    #{d.id} {d.deal_id} {d.borrower_name ? `– ${d.borrower_name}` : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="question">Question</Label>
            <Input
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Will NDVI remain above 0.5?"
            />
          </div>
          <div>
            <Label htmlFor="outcome">Outcome type</Label>
            <Select id="outcome" value={outcomeType} onValueChange={(v) => setOutcomeType(v as 'binary' | 'categorical')}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="binary">Binary</SelectItem>
                <SelectItem value="categorical">Categorical</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label htmlFor="cond">Condition type</Label>
              <Input
                id="cond"
                value={conditionType}
                onChange={(e) => setConditionType(e.target.value)}
                placeholder="NDVI_COMPLIANCE"
              />
            </div>
            <div>
              <Label htmlFor="thr">Threshold</Label>
              <Input
                id="thr"
                type="number"
                step="0.01"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                placeholder="0.5"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="anchor"
              checked={anchorToBlockchain}
              onChange={(e) => setAnchorToBlockchain(e.target.checked)}
            />
            <Label htmlFor="anchor">Anchor SFP to blockchain</Label>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="publish"
              checked={publishToPolymarket}
              onChange={(e) => setPublishToPolymarket(e.target.checked)}
            />
            <Label htmlFor="publish">Also export to external Polymarket (optional, for discovery only)</Label>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting || !dealId}>
              {submitting ? 'Creating…' : 'Create market'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
