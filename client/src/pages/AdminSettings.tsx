// #region agent log
/*
fetch('http://127.0.0.1:7242/ingest/b4962ed0-f261-4fa9-86f3-a557335b330a',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client/src/pages/AdminSettings.tsx:start',message:'Creating AdminSettings page',data:{todoId:'phase1-issue005-017'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
*/
// #endregion
import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useAuth } from '@/context/AuthContext';
import { Shield, Database, Users, Settings, Building2, Globe } from 'lucide-react';
import { DemoDataDashboard } from '@/components/DemoDataDashboard';
import { AdminSignupDashboard } from '@/components/AdminSignupDashboard';
import { VerificationFileConfigEditor } from '@/apps/verification-config/VerificationFileConfigEditor';
import { WhitelistingDashboard } from '@/apps/whitelisting-dashboard/WhitelistingDashboard';
import { PolicyEditor } from '@/apps/policy-editor/PolicyEditor';

export function AdminSettings() {
  const { user } = useAuth();
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
