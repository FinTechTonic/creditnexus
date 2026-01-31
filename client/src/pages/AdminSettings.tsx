import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';
import { Shield, Database, Users, Settings, Building2, Globe, ExternalLink, UserCircle, Share2, Plus, Trash2 } from 'lucide-react';
import { DemoDataDashboard } from '@/components/DemoDataDashboard';
import { AdminSignupDashboard } from '@/components/AdminSignupDashboard';
import { VerificationFileConfigEditor } from '@/apps/verification-config/VerificationFileConfigEditor';
import { WhitelistingDashboard } from '@/apps/whitelisting-dashboard/WhitelistingDashboard';
import { PolicyEditor } from '@/apps/policy-editor/PolicyEditor';

interface WhitelistEntry {
  id: number;
  organization_id: number;
  whitelisted_organization_id: number;
  created_at: string | null;
}

interface OrgOption {
  id: number;
  name: string;
}

function SocialFeedWhitelistCard({ orgId }: { orgId: number }) {
  const [list, setList] = useState<WhitelistEntry[]>([]);
  const [orgs, setOrgs] = useState<OrgOption[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<number | ''>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [listRes, orgsRes] = await Promise.all([
        fetchWithAuth(resolveApiUrl(`/api/organizations/${orgId}/social-feed-whitelist`)),
        fetchWithAuth(resolveApiUrl('/api/organizations?limit=500')),
      ]);
      if (listRes.ok) {
        const data = await listRes.json();
        setList(Array.isArray(data) ? data : []);
      }
      if (orgsRes.ok) {
        const data = await orgsRes.json();
        const arr = Array.isArray(data) ? data : (data?.organizations ?? data?.items ?? []);
        setOrgs(arr.filter((o: OrgOption) => o.id !== orgId));
      }
    } catch (e) {
      console.error('Failed to load social feed whitelist', e);
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    load();
  }, [load]);

  const add = async () => {
    if (selectedOrgId === '') return;
    setSaving(true);
    try {
      const res = await fetchWithAuth(resolveApiUrl(`/api/organizations/${orgId}/social-feed-whitelist`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ whitelisted_organization_id: selectedOrgId }),
      });
      if (res.ok) {
        setSelectedOrgId('');
        await load();
      }
    } finally {
      setSaving(false);
    }
  };

  const remove = async (whitelistedOrgId: number) => {
    setSaving(true);
    try {
      await fetchWithAuth(
        resolveApiUrl(`/api/organizations/${orgId}/social-feed-whitelist/${whitelistedOrgId}`),
        { method: 'DELETE' }
      );
      await load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Share2 className="h-4 w-4" />
          Social feed whitelist
        </CardTitle>
        <CardDescription>Whitelist other organisations so their posts appear in your social feed</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-slate-400">Loading…</p>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={selectedOrgId}
                onChange={(e) => setSelectedOrgId(e.target.value === '' ? '' : Number(e.target.value))}
                className="bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200"
              >
                <option value="">Select organization</option>
                {orgs.map((o) => (
                  <option key={o.id} value={o.id}>{o.name} (ID: {o.id})</option>
                ))}
              </select>
              <Button size="sm" onClick={add} disabled={saving || selectedOrgId === ''}>
                <Plus className="h-4 w-4 mr-1" />
                Add
              </Button>
            </div>
            <ul className="space-y-2">
              {list.length === 0 ? (
                <li className="text-slate-400 text-sm">No organisations whitelisted yet.</li>
              ) : (
                list.map((entry) => (
                  <li key={entry.id} className="flex items-center justify-between py-2 border-b border-slate-700">
                    <span className="text-slate-300">Org ID: {entry.whitelisted_organization_id}</span>
                    <Button variant="ghost" size="sm" onClick={() => remove(entry.whitelisted_organization_id)} disabled={saving}>
                      <Trash2 className="h-4 w-4 text-red-400" />
                    </Button>
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AdminSettings() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [isInstanceAdmin, setIsInstanceAdmin] = useState(false);
  const [isOrgAdmin, setIsOrgAdmin] = useState(false);
  
  useEffect(() => {
    // Check if user is instance admin
    // Note: is_instance_admin field may not exist yet, so we check for admin role
    // Once the field is added, this will be: user?.role === 'admin' && user?.is_instance_admin === true
    setIsInstanceAdmin(user?.role === 'admin' && (user as any)?.is_instance_admin === true);
    // Check if user is organization admin
    setIsOrgAdmin(user?.role === 'admin' || (user as any)?.organization_role === 'admin');
  }, [user]);

  // If user is not an admin, show access denied
  if (!user || (user.role !== 'admin' && !(user as any)?.organization_role)) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="text-center py-12">
          <Shield className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
          <p className="text-slate-400">You do not have permission to access admin settings.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Admin Settings</h1>
          <p className="text-slate-400 mt-1">
            {isInstanceAdmin ? 'Instance Admin' : isOrgAdmin ? 'Organization Admin' : 'Admin'}
          </p>
        </div>
      </div>

      <Card className="mb-6 border-slate-700 bg-slate-800/30">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <ExternalLink className="h-4 w-4" />
            Quick links
          </CardTitle>
          <CardDescription>Jump to related admin and user areas</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button variant="outline" size="sm" className="border-slate-600" asChild>
            <Link to="/settings">
              <UserCircle className="h-4 w-4 mr-2" />
              User Settings
            </Link>
          </Button>
          {isInstanceAdmin && (
            <>
              <Button variant="outline" size="sm" className="border-slate-600" asChild>
                <Link to="/dashboard/admin-signups">
                  <Users className="h-4 w-4 mr-2" />
                  User Signups
                </Link>
              </Button>
              <Button variant="outline" size="sm" className="border-slate-600" asChild>
                <Link to="/app/demo-data">
                  <Database className="h-4 w-4 mr-2" />
                  Demo Data
                </Link>
              </Button>
              <Button variant="outline" size="sm" className="border-slate-600" asChild>
                <Link to="/app/policy-editor">
                  <Shield className="h-4 w-4 mr-2" />
                  Policy Editor
                </Link>
              </Button>
              <Button variant="outline" size="sm" className="border-slate-600" asChild>
                <Link to="/app/verification-config">
                  <Settings className="h-4 w-4 mr-2" />
                  Verification Config
                </Link>
              </Button>
              <Button variant="outline" size="sm" className="border-slate-600" asChild>
                <Link to="/app/whitelisting-dashboard">
                  <Shield className="h-4 w-4 mr-2" />
                  Whitelisting
                </Link>
              </Button>
            </>
          )}
        </CardContent>
      </Card>
      
      <Tabs defaultValue={isInstanceAdmin ? "instance" : "organization"} className="space-y-6">
        <TabsList>
          {isInstanceAdmin && (
            <TabsTrigger value="instance">
              <Globe className="h-4 w-4 mr-2" />
              Instance Settings
            </TabsTrigger>
          )}
          {(isOrgAdmin || isInstanceAdmin) && (
            <TabsTrigger value="organization">
              <Building2 className="h-4 w-4 mr-2" />
              Organization Settings
            </TabsTrigger>
          )}
        </TabsList>
        
        {/* Instance Admin Settings */}
        {isInstanceAdmin && (
          <TabsContent value="instance">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    Demo Data
                  </CardTitle>
                  <CardDescription>Seed and manage demo data for testing</CardDescription>
                </CardHeader>
                <CardContent>
                  <DemoDataDashboard />
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    User Signups
                  </CardTitle>
                  <CardDescription>Review and approve user signups</CardDescription>
                </CardHeader>
                <CardContent>
                  <AdminSignupDashboard />
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Settings className="h-5 w-5" />
                    Verification Config
                  </CardTitle>
                  <CardDescription>Configure verification file settings</CardDescription>
                </CardHeader>
                <CardContent>
                  <VerificationFileConfigEditor />
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5" />
                    Whitelisting
                  </CardTitle>
                  <CardDescription>Manage IP and file whitelists</CardDescription>
                </CardHeader>
                <CardContent>
                  <WhitelistingDashboard />
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5" />
                    Policy Editor
                  </CardTitle>
                  <CardDescription>Edit policy rules and compliance</CardDescription>
                </CardHeader>
                <CardContent>
                  <PolicyEditor />
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        )}
        
        {/* Organization Admin Settings */}
        {(isOrgAdmin || isInstanceAdmin) && (
          <TabsContent value="organization">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Organization Configuration</CardTitle>
                  <CardDescription>Manage organization settings and policies</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <p className="text-slate-400">Organization settings will be implemented here</p>
                    {user?.organization && (
                      <div className="p-4 bg-slate-800 rounded-lg">
                        <p className="text-sm font-medium mb-2">Current Organization</p>
                        <p className="text-slate-300">{user.organization.name || 'N/A'}</p>
                        {user.organization_id && (
                          <p className="text-xs text-slate-400 mt-1">ID: {user.organization_id}</p>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Social feed whitelist: org admin can whitelist other orgs for social feeds */}
              {user?.organization_id && (
                <SocialFeedWhitelistCard orgId={user.organization_id} />
              )}
              
              {/* Instance admin can see all organization admin settings */}
              {isInstanceAdmin && (
                <Card>
                  <CardHeader>
                    <CardTitle>All Organizations</CardTitle>
                    <CardDescription>Instance admin: Manage all organizations</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-slate-400">Organization management interface will be implemented here</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
