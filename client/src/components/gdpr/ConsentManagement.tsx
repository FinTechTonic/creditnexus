import { useEffect, useState } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

type ConsentKey = 'processing' | 'marketing' | 'sharing' | 'analytics';

interface ConsentState {
  processing: boolean;
  marketing: boolean;
  sharing: boolean;
  analytics: boolean;
}

interface ConsentHistoryEntry {
  id: number;
  consent_type: string;
  granted: boolean;
  source: string | null;
  change_reason: string | null;
  recorded_at: string;
}

const DEFAULT_CONSENTS: ConsentState = {
  processing: false,
  marketing: false,
  sharing: false,
  analytics: false,
};

export function ConsentManagement() {
  const [consents, setConsents] = useState<ConsentState>(DEFAULT_CONSENTS);
  const [history, setHistory] = useState<ConsentHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [consentResp, historyResp] = await Promise.all([
        fetchWithAuth('/api/consent'),
        fetchWithAuth('/api/consent/history'),
      ]);
      if (consentResp.ok) {
        const data = await consentResp.json();
        setConsents({ ...DEFAULT_CONSENTS, ...(data.consents || {}) });
      } else {
        const err = await consentResp.json().catch(() => ({ detail: 'Failed to load consents' }));
        setError(err.detail || 'Failed to load consents');
      }
      if (historyResp.ok) {
        const data = await historyResp.json();
        setHistory(Array.isArray(data.history) ? data.history : []);
      }
    } catch (err) {
      setError('Failed to load consent data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toggleConsent = (key: ConsentKey) => {
    setConsents((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const saveConsents = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetchWithAuth('/api/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consents,
          source: 'settings',
          change_reason: 'user_update',
        }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to update consents' }));
        setError(err.detail || 'Failed to update consents');
      } else {
        setSuccess('Consent preferences updated.');
        await load();
      }
    } catch (err) {
      setError('Failed to update consents');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Consent Preferences</CardTitle>
          <CardDescription>
            Manage your consent for data processing, marketing, sharing, and analytics.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-sm text-slate-400">Loading...</div>
          ) : (
            <div className="space-y-4">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={consents.processing}
                  onChange={() => toggleConsent('processing')}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-slate-100">Data Processing (Required)</div>
                  <div className="text-sm text-slate-400">
                    Allows us to process your data to provide core services.
                  </div>
                </div>
              </label>
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={consents.marketing}
                  onChange={() => toggleConsent('marketing')}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-slate-100">Marketing</div>
                  <div className="text-sm text-slate-400">
                    Receive product updates, newsletters, and promotions.
                  </div>
                </div>
              </label>
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={consents.sharing}
                  onChange={() => toggleConsent('sharing')}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-slate-100">Third-Party Sharing</div>
                  <div className="text-sm text-slate-400">
                    Allow data sharing with trusted third parties.
                  </div>
                </div>
              </label>
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={consents.analytics}
                  onChange={() => toggleConsent('analytics')}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-slate-100">Analytics</div>
                  <div className="text-sm text-slate-400">
                    Help us improve the product with usage analytics.
                  </div>
                </div>
              </label>
              {error && <div className="text-sm text-red-400">{error}</div>}
              {success && <div className="text-sm text-emerald-400">{success}</div>}
              <Button onClick={saveConsents} disabled={saving || !consents.processing}>
                {saving ? 'Saving...' : 'Save Preferences'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Consent History</CardTitle>
          <CardDescription>Recent consent changes for audit purposes.</CardDescription>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <div className="text-sm text-slate-400">No history yet.</div>
          ) : (
            <div className="space-y-3">
              {history.map((entry) => (
                <div key={entry.id} className="text-sm border-b border-slate-800 pb-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-100">{entry.consent_type}</span>
                    <span className={entry.granted ? 'text-emerald-400' : 'text-red-400'}>
                      {entry.granted ? 'Granted' : 'Withdrawn'}
                    </span>
                  </div>
                  <div className="text-slate-400">
                    {entry.source || 'unknown'} • {new Date(entry.recorded_at).toLocaleString()}
                  </div>
                  {entry.change_reason && (
                    <div className="text-slate-500">Reason: {entry.change_reason}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
