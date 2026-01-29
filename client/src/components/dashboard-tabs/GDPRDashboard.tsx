import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Download, Trash2, Shield, AlertCircle, CheckCircle2, History } from 'lucide-react';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';

interface ConsentRecord {
  id: number;
  consent_type: string;
  consent_purpose: string;
  legal_basis: string;
  consent_given: boolean;
  consent_withdrawn: boolean;
  consent_given_at: string | null;
  created_at: string;
}

export function GDPRDashboard() {
  const { user } = useAuth();
  const [consents, setConsents] = useState<ConsentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExportLoading] = useState(false);
  const [requestType, setRequestType] = useState('rectification');
  const [requestDesc, setRequestDesc] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadConsents();
  }, []);

  const loadConsents = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth('/api/gdpr/consents');
      if (res.ok) {
        const data = await res.json();
        setConsents(data.consents || []);
      }
    } catch (e) {
      console.error("Failed to load consents", e);
    } finally {
      setLoading(false);
    }
  };

  const handleExportData = async () => {
    setExportLoading(true);
    try {
      const res = await fetchWithAuth('/api/gdpr/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: user?.email, format: 'json' })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `data_export_${new Date().toISOString()}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    } catch (e) {
      console.error("Export failed", e);
    } finally {
      setExportLoading(false);
    }
  };

  const handleSubmitRequest = async () => {
    if (!requestDesc.trim()) return;
    setSubmitting(true);
    try {
      const res = await fetchWithAuth('/api/gdpr/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_type: requestType,
          description: requestDesc
        })
      });
      if (res.ok) {
        alert("Request submitted successfully.");
        setRequestDesc('');
      }
    } catch (e) {
      console.error("Request failed", e);
    } finally {
      setSubmitting(false);
    }
  };

  const updateConsent = async (type: string, purpose: string, basis: string, given: boolean) => {
    try {
      const res = await fetchWithAuth('/api/gdpr/consents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consent_type: type,
          consent_purpose: purpose,
          legal_basis: basis,
          consent_given: given
        })
      });
      if (res.ok) loadConsents();
    } catch (e) {
      console.error("Consent update failed", e);
    }
  };

  const isConsentGiven = (type: string) => {
    const record = consents.find(c => c.consent_type === type && !c.consent_withdrawn);
    return record ? record.consent_given : false;
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Privacy & Data Protection</h2>
        <p className="text-slate-400 mt-1">Manage your GDPR rights and data preferences</p>
      </div>

      <Tabs defaultValue="consent">
        <TabsList>
          <TabsTrigger value="consent">Consents</TabsTrigger>
          <TabsTrigger value="requests">Rights Requests</TabsTrigger>
          <TabsTrigger value="data">Data Management</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="consent" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Data Processing Consents</CardTitle>
              <CardDescription>Control how we use your information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {[
                { id: 'marketing', label: 'Marketing Communications', purpose: 'Sending newsletters and product updates', basis: 'consent' },
                { id: 'analytics', label: 'Usage Analytics', purpose: 'Improving application performance and UX', basis: 'consent' },
                { id: 'third_party', label: 'Third-Party Data Sharing', purpose: 'Sharing non-essential data with partners', basis: 'consent' }
              ].map(c => (
                <div key={c.id} className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">{c.label}</Label>
                    <p className="text-sm text-slate-400">{c.purpose}</p>
                  </div>
                  <Switch 
                    checked={isConsentGiven(c.id)} 
                    onCheckedChange={(val) => updateConsent(c.id, c.purpose, c.basis, val)}
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="requests" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Exercise Your Rights</CardTitle>
              <CardDescription>Submit requests for rectification, restriction, or objection</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Request Type</Label>
                <select 
                  className="w-full bg-slate-900 border border-slate-700 rounded-md p-2"
                  value={requestType}
                  onChange={(e) => setRequestType(e.target.value)}
                >
                  <option value="rectification">Rectification (Correct data)</option>
                  <option value="restriction">Restriction of Processing</option>
                  <option value="objection">Objection to Processing</option>
                  <option value="portability">Data Portability</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Details</Label>
                <Textarea 
                  placeholder="Describe your request in detail..."
                  value={requestDesc}
                  onChange={(e) => setRequestDesc(e.target.value)}
                />
              </div>
              <Button onClick={handleSubmitRequest} disabled={submitting || !requestDesc.trim()}>
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Submit Request
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="data" className="space-y-4 mt-6">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Download className="h-4 w-4" />Export Data</CardTitle>
                <CardDescription>Download a machine-readable copy of your personal data</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" onClick={handleExportData} disabled={exporting}>
                  {exporting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Generate Export (JSON)
                </Button>
              </CardContent>
            </Card>

            <Card className="border-red-900/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-500"><Trash2 className="h-4 w-4" />Delete Account</CardTitle>
                <CardDescription>Permanently delete or anonymize your information (Right to Erasure)</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="destructive">Request Deletion</Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="history" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Compliance Audit Trail</CardTitle>
              <CardDescription>History of your privacy actions and requests</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? <div className="flex justify-center"><Loader2 className="h-6 w-6 animate-spin" /></div> : (
                <div className="space-y-4">
                  {consents.length === 0 ? <p className="text-sm text-slate-400">No history found.</p> : 
                    consents.map(c => (
                      <div key={c.id} className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <div>
                          <p className="text-sm font-medium">{c.consent_type} - {c.consent_given ? 'Granted' : 'Withdrawn'}</p>
                          <p className="text-xs text-slate-500">{new Date(c.created_at).toLocaleString()}</p>
                        </div>
                        {c.consent_given && !c.consent_withdrawn ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <History className="h-4 w-4 text-slate-500" />}
                      </div>
                    ))
                  }
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
