/**
 * Whitelisting Dashboard: File, IP, Implementation, and Node whitelist profiles.
 * Uses /api/whitelist/profiles with scope filter. Admin-only.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { AlertCircle, FileCheck, Globe, Cpu, Server, Plus, Pencil, Loader2 } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { PERMISSION_USER_VIEW } from '@/utils/permissions';
import { PermissionGate } from '@/components/PermissionGate';

type Scope = 'file' | 'ip' | 'implementation' | 'node';

interface WhitelistProfile {
  id: number;
  name: string;
  scope: string;
  is_active: boolean;
  enabled_categories?: string[];
  file_types?: { allowed_extensions?: string[]; max_file_size_mb?: number };
  subdirectories?: Record<string, { enabled?: boolean; priority?: number }>;
  allowed_ips?: string[];
  allowed_cidrs?: string[];
  implementation_ids?: number[];
  allowed_nodes?: Array<{ id?: string; host?: string; purpose?: string }>;
  organization_id?: number | null;
  created_at?: string;
  updated_at?: string;
}

interface ImplementationOption {
  id: number;
  name: string;
  display_name: string;
  category: string;
}

const SCOPES: { id: Scope; label: string; icon: React.ReactNode }[] = [
  { id: 'file', label: 'File', icon: <FileCheck className="h-4 w-4" /> },
  { id: 'ip', label: 'IP', icon: <Globe className="h-4 w-4" /> },
  { id: 'implementation', label: 'Implementation', icon: <Cpu className="h-4 w-4" /> },
  { id: 'node', label: 'Nodes', icon: <Server className="h-4 w-4" /> },
];

function summary(p: WhitelistProfile, scope: Scope): string {
  switch (scope) {
    case 'file':
      const ec = (p.enabled_categories || []).length;
      const exts = (p.file_types?.allowed_extensions || []).length;
      return `categories: ${ec}, extensions: ${exts}`;
    case 'ip':
      const ips = (p.allowed_ips || []).length;
      const cidrs = (p.allowed_cidrs || []).length;
      return `IPs: ${ips}, CIDRs: ${cidrs}`;
    case 'implementation':
      return `impls: ${(p.implementation_ids || []).length}`;
    case 'node':
      return `nodes: ${(p.allowed_nodes || []).length}`;
    default:
      return '';
  }
}

export function WhitelistingDashboard() {
  const [scope, setScope] = useState<Scope>('file');
  const [profiles, setProfiles] = useState<WhitelistProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [implementations, setImplementations] = useState<ImplementationOption[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<WhitelistProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [formName, setFormName] = useState('');
  const [formActive, setFormActive] = useState(true);
  const [formEnabledCategories, setFormEnabledCategories] = useState('');
  const [formAllowedExtensions, setFormAllowedExtensions] = useState('');
  const [formMaxFileSizeMb, setFormMaxFileSizeMb] = useState(50);
  const [formAllowedIps, setFormAllowedIps] = useState('');
  const [formAllowedCidrs, setFormAllowedCidrs] = useState('');
  const [formImplementationIds, setFormImplementationIds] = useState<number[]>([]);
  const [formAllowedNodes, setFormAllowedNodes] = useState('');

  const loadProfiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithAuth(`/api/whitelist/profiles?scope=${scope}&limit=500`);
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Failed to load: ${res.statusText}`);
      }
      const data = await res.json();
      setProfiles(data.profiles || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load profiles');
      setProfiles([]);
    } finally {
      setLoading(false);
    }
  }, [scope]);

  useEffect(() => {
    loadProfiles();
  }, [loadProfiles]);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetchWithAuth('/api/implementations/available');
        if (res.ok) {
          const d = await res.json();
          setImplementations(d.implementations || []);
        }
      } catch {
        setImplementations([]);
      }
    })();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setFormName('');
    setFormActive(true);
    setFormEnabledCategories('');
    setFormAllowedExtensions('');
    setFormMaxFileSizeMb(50);
    setFormAllowedIps('');
    setFormAllowedCidrs('');
    setFormImplementationIds([]);
    setFormAllowedNodes('');
    setModalOpen(true);
  };

  const openEdit = (p: WhitelistProfile) => {
    setEditing(p);
    setFormName(p.name);
    setFormActive(p.is_active);
    setFormEnabledCategories((p.enabled_categories || []).join(', '));
    setFormAllowedExtensions((p.file_types?.allowed_extensions || []).join(', '));
    setFormMaxFileSizeMb(p.file_types?.max_file_size_mb ?? 50);
    setFormAllowedIps((p.allowed_ips || []).join(', '));
    setFormAllowedCidrs((p.allowed_cidrs || []).join(', '));
    setFormImplementationIds(p.implementation_ids || []);
    setFormAllowedNodes(
      (p.allowed_nodes || [])
        .map((n) => `${n.host || ''}|${n.purpose || 'other'}`)
        .join('\n')
    );
    setModalOpen(true);
  };

  const saveProfile = async () => {
    if (!formName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const url = editing
        ? `/api/whitelist/profiles/${editing.id}`
        : '/api/whitelist/profiles';
      const method = editing ? 'PATCH' : 'POST';
      const body: Record<string, unknown> = {
        name: formName.trim(),
        scope,
        is_active: formActive,
      };
      if (scope === 'file') {
        body.enabled_categories = formEnabledCategories
          .split(/,\s*/)
          .map((s) => s.trim())
          .filter(Boolean);
        const exts = formAllowedExtensions
          .split(/,\s*/)
          .map((s) => (s.startsWith('.') ? s : '.' + s))
          .filter(Boolean);
        body.file_types = { allowed_extensions: exts, max_file_size_mb: formMaxFileSizeMb };
      } else if (scope === 'ip') {
        body.allowed_ips = formAllowedIps.split(/,\s*/).map((s) => s.trim()).filter(Boolean);
        body.allowed_cidrs = formAllowedCidrs.split(/,\s*/).map((s) => s.trim()).filter(Boolean);
      } else if (scope === 'implementation') {
        body.implementation_ids = formImplementationIds;
      } else if (scope === 'node') {
        body.allowed_nodes = formAllowedNodes
          .split('\n')
          .map((line) => {
            const [host, purpose] = line.split('|').map((s) => s.trim());
            return { host: host || '', purpose: purpose || 'other' };
          })
          .filter((n) => n.host);
      }
      const res = await fetchWithAuth(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(typeof d.detail === 'string' ? d.detail : d.detail?.message || 'Save failed');
      }
      setModalOpen(false);
      loadProfiles();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const deactivate = async (p: WhitelistProfile) => {
    if (!confirm(`Deactivate "${p.name}"?`)) return;
    try {
      const res = await fetchWithAuth(`/api/whitelist/profiles/${p.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: false }),
      });
      if (res.ok) loadProfiles();
    } catch {
      setError('Failed to deactivate');
    }
  };

  return (
    <PermissionGate permission={PERMISSION_USER_VIEW}>
      <div className="space-y-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle>Whitelisting Dashboard</CardTitle>
            <p className="text-sm text-slate-400">
              Manage file, IP, implementation, and node whitelist profiles. Admin only.
            </p>
          </CardHeader>
          <CardContent>
            <Tabs value={scope} onValueChange={(v) => setScope(v as Scope)}>
              <TabsList className="grid w-full grid-cols-4 bg-slate-900">
                {SCOPES.map((s) => (
                  <TabsTrigger key={s.id} value={s.id} className="flex items-center gap-2">
                    {s.icon}
                    {s.label}
                  </TabsTrigger>
                ))}
              </TabsList>
              {SCOPES.map((s) => (
                <TabsContent key={s.id} value={s.id} className="mt-4">
                  {error && (
                    <div className="flex items-center gap-2 p-3 mb-4 bg-red-900/50 border border-red-700 rounded-lg">
                      <AlertCircle className="h-4 w-4 text-red-400" />
                      <span className="text-sm text-red-200">{error}</span>
                    </div>
                  )}
                  <div className="flex justify-end mb-2">
                    <Button onClick={openCreate} size="sm" className="gap-2">
                      <Plus className="h-4 w-4" />
                      Create profile
                    </Button>
                  </div>
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Name</TableHead>
                          <TableHead>Active</TableHead>
                          <TableHead>Summary</TableHead>
                          <TableHead className="w-[140px]">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {profiles.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={4} className="text-slate-400 text-center py-8">
                              No {s.label.toLowerCase()} profiles. Create one to get started.
                            </TableCell>
                          </TableRow>
                        ) : (
                          profiles.map((p) => (
                            <TableRow key={p.id}>
                              <TableCell className="font-medium">{p.name}</TableCell>
                              <TableCell>{p.is_active ? 'Yes' : 'No'}</TableCell>
                              <TableCell className="text-slate-400 text-sm">
                                {summary(p, s.id)}
                              </TableCell>
                              <TableCell>
                                <div className="flex gap-2">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => openEdit(p)}
                                    className="gap-1"
                                  >
                                    <Pencil className="h-3 w-3" />
                                    Edit
                                  </Button>
                                  {p.is_active && (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => deactivate(p)}
                                      className="text-amber-400 hover:text-amber-300"
                                    >
                                      Deactivate
                                    </Button>
                                  )}
                                </div>
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  )}
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      </div>

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-lg bg-slate-800 border-slate-700">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit' : 'Create'} {SCOPES.find((s) => s.id === scope)?.label} profile</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>Name</Label>
              <Input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="Profile name"
                className="bg-slate-900 border-slate-600"
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch checked={formActive} onCheckedChange={setFormActive} />
              <Label>Active</Label>
            </div>
            {scope === 'file' && (
              <>
                <div>
                  <Label>Enabled categories (comma-separated)</Label>
                  <Input
                    value={formEnabledCategories}
                    onChange={(e) => setFormEnabledCategories(e.target.value)}
                    placeholder="legal, financial, compliance"
                    className="bg-slate-900 border-slate-600"
                  />
                </div>
                <div>
                  <Label>Allowed extensions (comma-separated)</Label>
                  <Input
                    value={formAllowedExtensions}
                    onChange={(e) => setFormAllowedExtensions(e.target.value)}
                    placeholder=".pdf, .doc, .docx"
                    className="bg-slate-900 border-slate-600"
                  />
                </div>
                <div>
                  <Label>Max file size (MB)</Label>
                  <Input
                    type="number"
                    min={1}
                    value={formMaxFileSizeMb}
                    onChange={(e) => setFormMaxFileSizeMb(parseInt(e.target.value, 10) || 50)}
                    className="bg-slate-900 border-slate-600"
                  />
                </div>
              </>
            )}
            {scope === 'ip' && (
              <>
                <div>
                  <Label>Allowed IPs (comma-separated)</Label>
                  <Input
                    value={formAllowedIps}
                    onChange={(e) => setFormAllowedIps(e.target.value)}
                    placeholder="1.2.3.4, 10.0.0.1"
                    className="bg-slate-900 border-slate-600"
                  />
                </div>
                <div>
                  <Label>Allowed CIDRs (comma-separated)</Label>
                  <Input
                    value={formAllowedCidrs}
                    onChange={(e) => setFormAllowedCidrs(e.target.value)}
                    placeholder="10.0.0.0/8, 192.168.0.0/16"
                    className="bg-slate-900 border-slate-600"
                  />
                </div>
              </>
            )}
            {scope === 'implementation' && (
              <div>
                <Label>Implementations</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {implementations.map((impl) => (
                    <label
                      key={impl.id}
                      className="flex items-center gap-2 px-3 py-1.5 rounded bg-slate-900 border border-slate-600 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={formImplementationIds.includes(impl.id)}
                        onChange={(e) => {
                          if (e.target.checked)
                            setFormImplementationIds((a) => [...a, impl.id]);
                          else
                            setFormImplementationIds((a) => a.filter((x) => x !== impl.id));
                        }}
                      />
                      <span className="text-sm">{impl.display_name || impl.name}</span>
                    </label>
                  ))}
                  {implementations.length === 0 && (
                    <span className="text-slate-400 text-sm">None available</span>
                  )}
                </div>
              </div>
            )}
            {scope === 'node' && (
              <div>
                <Label>Nodes (one per line: host|purpose)</Label>
                <textarea
                  value={formAllowedNodes}
                  onChange={(e) => setFormAllowedNodes(e.target.value)}
                  placeholder={'api.example.com|api\nworker.example.com|worker'}
                  rows={4}
                  className="w-full rounded bg-slate-900 border border-slate-600 p-2 text-sm text-slate-200"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={saveProfile} disabled={saving || !formName.trim()} className="gap-2">
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {editing ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PermissionGate>
  );
}
