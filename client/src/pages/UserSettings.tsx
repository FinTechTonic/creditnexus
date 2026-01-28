import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/context/AuthContext';
import { User, Key, Bell, Shield, Mic, TrendingUp, Building2, DollarSign, Link2 } from 'lucide-react';
import { LinkAccounts } from '@/components/LinkAccounts';

interface UserPreferences {
  audio_input_mode: boolean;
  investment_mode: boolean;
  loan_mode: boolean;
  bank_mode: boolean;
  trading_mode: boolean;
  email_notifications: boolean;
  push_notifications: boolean;
}

interface APIKey {
  id: number;
  name: string;
  key?: string; // Optional - not returned from API for security
  created_at: string;
}

export function UserSettings() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [profile, setProfile] = useState({
    display_name: user?.display_name || '',
    email: user?.email || '',
    profile_image: user?.profile_image || '',
  });
  
  const [preferences, setPreferences] = useState<UserPreferences>({
    audio_input_mode: false,
    investment_mode: false,
    loan_mode: false,
    bank_mode: false,
    trading_mode: false,
    email_notifications: true,
    push_notifications: false,
  });
  
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [newApiKey, setNewApiKey] = useState({ name: '', key: '' });

  // Load user preferences and profile on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        // Load preferences
        const prefsResponse = await fetch('/api/user-settings/preferences');
        if (prefsResponse.ok) {
          const prefsData = await prefsResponse.json();
          setPreferences(prefsData);
        }
        
        // Load profile
        const profileResponse = await fetch('/api/user-settings/profile');
        if (profileResponse.ok) {
          const profileData = await profileResponse.json();
          setProfile({
            display_name: profileData.display_name || user?.display_name || '',
            email: profileData.email || user?.email || '',
            profile_image: profileData.profile_image || user?.profile_image || '',
          });
        }
        
        // Load API keys
        const keysResponse = await fetch('/api/user-settings/api-keys');
        if (keysResponse.ok) {
          const keysData = await keysResponse.json();
          setApiKeys(keysData.map((k: any) => ({
            id: k.id,
            name: k.name,
            created_at: k.created_at,
          })));
        }
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        setLoading(false);
      }
    };
    
    if (user) {
      loadData();
    }
  }, [user]);

  const handleSaveProfile = async () => {
    try {
      setSaving(true);
      const response = await fetch('/api/user-settings/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      });
      if (response.ok) {
        // Show success message
        alert('Profile updated successfully');
      }
    } catch (error) {
      console.error('Failed to save profile:', error);
      alert('Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const handleSavePreferences = async () => {
    try {
      setSaving(true);
      const response = await fetch('/api/user-settings/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      });
      if (response.ok) {
        alert('Preferences saved successfully');
      }
    } catch (error) {
      console.error('Failed to save preferences:', error);
      alert('Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleAddApiKey = async () => {
    if (!newApiKey.name || !newApiKey.key) {
      alert('Please fill in both name and key');
      return;
    }
    try {
      setSaving(true);
      const response = await fetch('/api/user-settings/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newApiKey),
      });
      if (response.ok) {
        const data = await response.json();
        const key: APIKey = {
          id: data.id,
          name: data.name,
          key: '', // Don't store the actual key in state
          created_at: data.created_at,
        };
        setApiKeys([...apiKeys, key]);
        setNewApiKey({ name: '', key: '' });
        alert('API key added successfully');
      } else {
        alert('Failed to add API key');
      }
    } catch (error) {
      console.error('Failed to add API key:', error);
      alert('Failed to add API key');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteApiKey = async (keyId: number) => {
    if (!confirm('Are you sure you want to delete this API key?')) {
      return;
    }
    try {
      setSaving(true);
      const response = await fetch(`/api/user-settings/api-keys/${keyId}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setApiKeys(apiKeys.filter(k => k.id !== keyId));
        alert('API key deleted successfully');
      } else {
        alert('Failed to delete API key');
      }
    } catch (error) {
      console.error('Failed to delete API key:', error);
      alert('Failed to delete API key');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">User Settings</h1>
      
      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="preferences">Preferences</TabsTrigger>
          <TabsTrigger value="link-accounts">
            <Link2 className="h-4 w-4 mr-2" />
            Link Accounts
          </TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
        </TabsList>
        
        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>Update your personal information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="display_name">Display Name</Label>
                <Input
                  id="display_name"
                  value={profile.display_name}
                  onChange={(e) => setProfile({ ...profile, display_name: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={profile.email}
                  disabled
                  className="bg-slate-800"
                />
                <p className="text-xs text-slate-400 mt-1">Email cannot be changed</p>
              </div>
              <div>
                <Label htmlFor="profile_image">Profile Image URL</Label>
                <Input
                  id="profile_image"
                  value={profile.profile_image}
                  onChange={(e) => setProfile({ ...profile, profile_image: e.target.value })}
                  placeholder="https://..."
                />
              </div>
              <Button onClick={handleSaveProfile} disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="preferences">
          <Card>
            <CardHeader>
              <CardTitle>Quick Access Preferences</CardTitle>
              <CardDescription>Enable/disable modes for quick access in dashboard</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mic className="h-5 w-5 text-slate-400" />
                  <div>
                    <Label htmlFor="audio_input_mode">Audio Input Mode</Label>
                    <p className="text-xs text-slate-400">Enable voice input for document processing</p>
                  </div>
                </div>
                <Switch
                  id="audio_input_mode"
                  checked={preferences.audio_input_mode}
                  onCheckedChange={(checked) => setPreferences({ ...preferences, audio_input_mode: checked })}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <TrendingUp className="h-5 w-5 text-slate-400" />
                  <div>
                    <Label htmlFor="investment_mode">Investment Mode</Label>
                    <p className="text-xs text-slate-400">Show investment tracking and portfolio analytics</p>
                  </div>
                </div>
                <Switch
                  id="investment_mode"
                  checked={preferences.investment_mode}
                  onCheckedChange={(checked) => setPreferences({ ...preferences, investment_mode: checked })}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Building2 className="h-5 w-5 text-slate-400" />
                  <div>
                    <Label htmlFor="loan_mode">Loan Mode</Label>
                    <p className="text-xs text-slate-400">Show loan applications and management</p>
                  </div>
                </div>
                <Switch
                  id="loan_mode"
                  checked={preferences.loan_mode}
                  onCheckedChange={(checked) => setPreferences({ ...preferences, loan_mode: checked })}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <DollarSign className="h-5 w-5 text-slate-400" />
                  <div>
                    <Label htmlFor="bank_mode">Bank Mode</Label>
                    <p className="text-xs text-slate-400">Show bank account connections and balances</p>
                  </div>
                </div>
                <Switch
                  id="bank_mode"
                  checked={preferences.bank_mode}
                  onCheckedChange={(checked) => setPreferences({ ...preferences, bank_mode: checked })}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <TrendingUp className="h-5 w-5 text-slate-400" />
                  <div>
                    <Label htmlFor="trading_mode">Trading Mode</Label>
                    <p className="text-xs text-slate-400">Show trading dashboard and order management</p>
                  </div>
                </div>
                <Switch
                  id="trading_mode"
                  checked={preferences.trading_mode}
                  onCheckedChange={(checked) => setPreferences({ ...preferences, trading_mode: checked })}
                />
              </div>
              
              <Button onClick={handleSavePreferences} disabled={saving}>
                {saving ? 'Saving...' : 'Save Preferences'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="link-accounts">
          <LinkAccounts />
        </TabsContent>
        
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>Manage how you receive notifications</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Bell className="h-5 w-5 text-slate-400" />
                  <div>
                    <Label htmlFor="email_notifications">Email Notifications</Label>
                    <p className="text-xs text-slate-400">Receive notifications via email</p>
                  </div>
                </div>
                <Switch
                  id="email_notifications"
                  checked={preferences.email_notifications}
                  onCheckedChange={(checked) => setPreferences({ ...preferences, email_notifications: checked })}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Bell className="h-5 w-5 text-slate-400" />
                  <div>
                    <Label htmlFor="push_notifications">Push Notifications</Label>
                    <p className="text-xs text-slate-400">Receive browser push notifications</p>
                  </div>
                </div>
                <Switch
                  id="push_notifications"
                  checked={preferences.push_notifications}
                  onCheckedChange={(checked) => setPreferences({ ...preferences, push_notifications: checked })}
                />
              </div>
              
              <Button onClick={handleSavePreferences} disabled={saving}>
                {saving ? 'Saving...' : 'Save Preferences'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="api-keys">
          <Card>
            <CardHeader>
              <CardTitle>API Keys & Account Linking</CardTitle>
              <CardDescription>Manage API keys for external account linking (SSO placeholders)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Add New API Key</Label>
                <div className="flex gap-2">
                  <Input 
                    placeholder="Key name (e.g., Plaid API Key)" 
                    value={newApiKey.name}
                    onChange={(e) => setNewApiKey({ ...newApiKey, name: e.target.value })}
                  />
                  <Input 
                    type="password" 
                    placeholder="API Key" 
                    value={newApiKey.key}
                    onChange={(e) => setNewApiKey({ ...newApiKey, key: e.target.value })}
                  />
                  <Button onClick={handleAddApiKey}>Add</Button>
                </div>
              </div>
              
              <div className="space-y-2">
                <h3 className="text-sm font-semibold">Existing Keys</h3>
                {apiKeys.length === 0 ? (
                  <p className="text-sm text-slate-400">No API keys added yet</p>
                ) : (
                  apiKeys.map((key) => (
                    <div key={key.id} className="flex items-center justify-between p-3 bg-slate-800 rounded">
                      <div>
                        <p className="text-sm font-medium">{key.name}</p>
                        <p className="text-xs text-slate-400">Created: {new Date(key.created_at).toLocaleDateString()}</p>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => handleDeleteApiKey(key.id)} disabled={saving}>
                        Delete
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
