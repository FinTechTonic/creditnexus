import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Calendar, Trash2, Clock, Save, Loader2 } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface RetentionPolicyManagerProps {
  documentId: number;
  initialPolicy?: string;
  initialExpiresAt?: string;
  onUpdate?: () => void;
}

export function RetentionPolicyManager({ 
  documentId, 
  initialPolicy, 
  initialExpiresAt,
  onUpdate 
}: RetentionPolicyManagerProps) {
  const [policy, setPolicy] = useState(initialPolicy || 'standard');
  const [expiresAt, setExpiresAt] = useState(initialExpiresAt ? initialExpiresAt.split('T')[0] : '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetchWithAuth(`/api/documents/${documentId}/retention`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ retention_policy: policy, retention_expires_at: expiresAt }),
      });
      if (response.ok) {
        if (onUpdate) onUpdate();
        alert('Retention policy updated');
      }
    } catch (e) {
      console.error('Update failed', e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Clock className="h-4 w-4 text-orange-500" />
          Data Retention
        </CardTitle>
        <CardDescription>Manage lifecycle and deletion</CardDescription>
      </Header>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Policy</Label>
          <select 
            className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm"
            value={policy}
            onChange={(e) => setPolicy(e.target.value)}
          >
            <option value="standard">Standard (7 Years)</option>
            <option value="extended">Extended (10 Years)</option>
            <option value="permanent">Permanent</option>
            <option value="custom">Custom Date</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label>Expiration Date</Label>
          <input 
            type="date"
            className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm text-white"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
          />
        </div>
        <Button size="sm" onClick={handleSave} disabled={saving} className="w-full">
          {saving ? <Loader2 className="h-3 w-3 animate-spin mr-2" /> : <Save className="h-3 w-3 mr-2" />}
          Update Retention
        </Button>
      </CardContent>
    </Card>
  );
}
