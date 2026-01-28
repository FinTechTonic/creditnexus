import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { FileText, Shield, Save, Loader2 } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface DocumentClassificationFormProps {
  documentId: number;
  initialClassification?: string;
  initialStatus?: string;
  onUpdate?: () => void;
}

export function DocumentClassificationForm({ 
  documentId, 
  initialClassification, 
  initialStatus,
  onUpdate 
}: DocumentClassificationFormProps) {
  const [classification, setClassification] = useState(initialClassification || 'internal');
  const [status, setStatus] = useState(initialStatus || 'draft');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetchWithAuth(`/api/documents/${documentId}/classification`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ classification, status }),
      });
      if (response.ok) {
        if (onUpdate) onUpdate();
        alert('Classification updated');
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
          <Shield className="h-4 w-4 text-blue-500" />
          Document Classification
        </CardTitle>
        <CardDescription>Set security and lifecycle status</CardDescription>
      </Header>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Classification</Label>
          <select 
            className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm"
            value={classification}
            onChange={(e) => setClassification(e.target.value)}
          >
            <option value="public">Public</option>
            <option value="internal">Internal</option>
            <option value="confidential">Confidential</option>
            <option value="restricted">Restricted</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label>Status</Label>
          <select 
            className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="expired">Expired</option>
          </select>
        </div>
        <Button size="sm" onClick={handleSave} disabled={saving} className="w-full">
          {saving ? <Loader2 className="h-3 w-3 animate-spin mr-2" /> : <Save className="h-3 w-3 mr-2" />}
          Update Classification
        </Button>
      </CardContent>
    </Card>
  );
}
