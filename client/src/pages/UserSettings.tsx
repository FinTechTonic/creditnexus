import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useAuth, fetchWithAuth } from '@/context/AuthContext';
import { usePayment } from '@/context/PaymentContext';
import { User, Key, Bell, Shield, Mic, TrendingUp, Building2, DollarSign, Link2, Briefcase, Settings, Coins } from 'lucide-react';
import { LinkAccounts } from '@/components/LinkAccounts';
import { BrokerageOnboarding } from '@/components/BrokerageOnboarding';
import { BringYourOwnKeys } from '@/components/BringYourOwnKeys';

interface UserPreferences {
  audio_input_mode: boolean;
  investment_mode: boolean;
  loan_mode: boolean;
  bank_mode: boolean;
  trading_mode: boolean;
  email_notifications: boolean;
  push_notifications: boolean;
  kyc_brokerage_notifications: boolean;
  brokerage_plaid_kyc_preferred: boolean;
}

interface APIKey {
  id: number;
  name: string;
  key?: string; // Optional - not returned from API for security
  created_at: string;
}

interface KYCInfo {
  legal_name: string;
  date_of_birth: string;
  address_line1: string;
  address_line2: string;
  address_city: string;
  address_state: string;
  address_postal_code: string;
  address_country: string;
  phone: string;
  tax_id: string;
  tax_id_type: string;
}

const SETTINGS_TAB_VALUES = ['profile', 'preferences', 'kyc-identity', 'link-accounts', 'bring-your-own-keys', 'trading-account', 'notifications', 'api-keys'] as const;

export function UserSettings() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabFromUrl = searchParams.get('tab');
  const initialTab = tabFromUrl && SETTINGS_TAB_VALUES.includes(tabFromUrl as typeof SETTINGS_TAB_VALUES[number])
    ? tabFromUrl
    : 'profile';
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
    kyc_brokerage_notifications: true,
    brokerage_plaid_kyc_preferred: false,
  });
  
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [newApiKey, setNewApiKey] = useState({ name: '', key: '' });
  const [kycStatus, setKycStatus] = useState<{ status: string; verification?: Record<string, unknown>; evaluation?: Record<string, unknown> } | null>(null);
  const [kycInfo, setKycInfo] = useState<KYCInfo>({
    legal_name: '',
    date_of_birth: '',
    address_line1: '',
    address_line2: '',
    address_city: '',
    address_state: '',
    address_postal_code: '',
    address_country: '',
    phone: '',
    tax_id: '',
    tax_id_type: 'USA_SSN',
  });
  const [activeSettingsTab, setActiveSettingsTab] = useState(initialTab);
  const [byokAccess, setByokAccess] = useState<{ allowed: boolean; reason: string } | null>(null);
  const [tradingUnlocked, setTradingUnlocked] = useState<boolean | null>(null);
  const { fetchWithPaymentHandling } = usePayment();
  const [creditsAmount, setCreditsAmount] = useState('');
  const [creditsTopUpLoading, setCreditsTopUpLoading] = useState(false);
  const [creditsTopUpError, setCreditsTopUpError] = useState<string | null>(null);

  // Sync tab from URL when landing on /settings?tab=kyc-identity
  useEffect(() => {
    const t = searchParams.get('tab');
    if (t && SETTINGS_TAB_VALUES.includes(t as (typeof SETTINGS_TAB_VALUES)[number])) {
      setActiveSettingsTab(t);
    }
  }, [searchParams]);

  // Fetch BYOK access when user switches to Bring Your Own Keys tab
  useEffect(() => {
    if (activeSettingsTab !== 'bring-your-own-keys' || !user) {
      setByokAccess(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchWithAuth('/api/user-settings/byok/access');
        const data = res.ok ? await res.json() : { allowed: false, reason: 'paywall' };
        if (!cancelled) setByokAccess({ allowed: data.allowed === true, reason: data.reason || '' });
      } catch {
        if (!cancelled) setByokAccess({ allowed: false, reason: 'paywall' });
      }
    })();
    return () => { cancelled = true; };
  }, [activeSettingsTab, user]);

  // Fetch trading-unlocked when user switches to Trading account tab (gate: require Alpaca BYOK)
  useEffect(() => {
    if (activeSettingsTab !== 'trading-account' || !user) {
      setTradingUnlocked(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchWithAuth('/api/user-settings/byok/trading-unlocked');
        const data = res.ok ? await res.json() : { unlocked: false };
        if (!cancelled) setTradingUnlocked(data.unlocked === true);
      } catch {
        if (!cancelled) setTradingUnlocked(false);
      }
    })();
    return () => { cancelled = true; };
  }, [activeSettingsTab, user]);

  const handleTabChange = (value: string) => {
    setActiveSettingsTab(value);
    if (value && value !== 'profile') {
      setSearchParams({ tab: value }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
  };

  // Load user preferences and profile on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        // Load preferences
        const prefsResponse = await fetchWithAuth('/api/user-settings/preferences');
        if (prefsResponse.ok) {
          const prefsData = await prefsResponse.json();
          setPreferences({
            kyc_brokerage_notifications: true,
            brokerage_plaid_kyc_preferred: false,
            ...prefsData,
          });
        }
        
        // Load profile
        const profileResponse = await fetchWithAuth('/api/user-settings/profile');
        if (profileResponse.ok) {
          const profileData = await profileResponse.json();
          setProfile({
            display_name: profileData.display_name || user?.display_name || '',
            email: profileData.email || user?.email || '',
            profile_image: profileData.profile_image || user?.profile_image || '',
          });
        }
        
        // Load API keys
        const keysResponse = await fetchWithAuth('/api/user-settings/api-keys');
        if (keysResponse.ok) {
          const keysData = await keysResponse.json();
          setApiKeys(keysData.map((k: any) => ({
            id: k.id,
            name: k.name,
            created_at: k.created_at,
          })));
        }

        // Load KYC status
        const kycResponse = await fetchWithAuth('/api/kyc/status');
        if (kycResponse.ok) {
          const kycData = await kycResponse.json();
          setKycStatus(kycData);
        } else {
          setKycStatus(null);
        }

        // Load KYC info (legal name, DOB, address, phone)
        const kycInfoResponse = await fetchWithAuth('/api/user-settings/kyc-info');
        if (kycInfoResponse.ok) {
          const kycInfoData = await kycInfoResponse.json();
          setKycInfo({
            legal_name: kycInfoData.legal_name ?? '',
            date_of_birth: kycInfoData.date_of_birth ?? '',
            address_line1: kycInfoData.address_line1 ?? '',
            address_line2: kycInfoData.address_line2 ?? '',
            address_city: kycInfoData.address_city ?? '',
            address_state: kycInfoData.address_state ?? '',
            address_postal_code: kycInfoData.address_postal_code ?? '',
            address_country: kycInfoData.address_country ?? '',
            phone: kycInfoData.phone ?? '',
            tax_id: kycInfoData.tax_id ?? '',
            tax_id_type: kycInfoData.tax_id_type ?? 'USA_SSN',
          });
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
      const response = await fetchWithAuth('/api/user-settings/profile', {
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
      const response = await fetchWithAuth('/api/user-settings/preferences', {
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
      const response = await fetchWithAuth('/api/user-settings/api-keys', {
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
      const response = await fetchWithAuth(`/api/user-settings/api-keys/${keyId}`, {
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

  const handleSaveKycInfo = async () => {
    try {
      setSaving(true);
      const response = await fetchWithAuth('/api/user-settings/kyc-info', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(kycInfo),
      });
      if (response.ok) {
        alert('KYC information saved successfully');
      } else {
        alert('Failed to save KYC information');
      }
    } catch (error) {
      console.error('Failed to save KYC information:', error);
      alert('Failed to save KYC information');
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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">User Settings</h1>
        {user?.role === 'admin' && (
          <Link
            to="/admin-settings"
            className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-emerald-400 transition-colors"
          >
            <Settings className="h-4 w-4" />
            Admin Settings
          </Link>
        )}
      </div>
      
      <Tabs value={activeSettingsTab} onValueChange={handleTabChange} className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="preferences">Preferences</TabsTrigger>
          <TabsTrigger value="kyc-identity">
            <Shield className="h-4 w-4 mr-2" />
            KYC & Identity
          </TabsTrigger>
          <TabsTrigger value="link-accounts">
            <Link2 className="h-4 w-4 mr-2" />
            Link Accounts
          </TabsTrigger>
          <TabsTrigger value="bring-your-own-keys">
            <Key className="h-4 w-4 mr-2" />
            Bring Your Own Keys
          </TabsTrigger>
          <TabsTrigger value="trading-account">
            <Briefcase className="h-4 w-4 mr-2" />
            Trading account
          </TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
        </TabsList>
        
        <TabsContent value="profile">
          <div className="space-y-6">
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

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-slate-400" />
                  KYC information
                </CardTitle>
                <CardDescription>
                  Name, date of birth, address, and phone used for identity verification (e.g. brokerage application). Also available in the{' '}
                  <button type="button" onClick={() => handleTabChange('kyc-identity')} className="text-emerald-400 hover:underline">
                    KYC & Identity
                  </button>
                  {' '}tab.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="profile_kyc_legal_name">Legal name</Label>
                    <Input
                      id="profile_kyc_legal_name"
                      value={kycInfo.legal_name}
                      onChange={(e) => setKycInfo({ ...kycInfo, legal_name: e.target.value })}
                      placeholder="Full legal name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile_kyc_date_of_birth">Date of birth</Label>
                    <Input
                      id="profile_kyc_date_of_birth"
                      type="date"
                      value={kycInfo.date_of_birth}
                      onChange={(e) => setKycInfo({ ...kycInfo, date_of_birth: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="profile_kyc_address_line1">Address line 1</Label>
                  <Input
                    id="profile_kyc_address_line1"
                    value={kycInfo.address_line1}
                    onChange={(e) => setKycInfo({ ...kycInfo, address_line1: e.target.value })}
                    placeholder="Street address"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="profile_kyc_address_line2">Address line 2 (optional)</Label>
                  <Input
                    id="profile_kyc_address_line2"
                    value={kycInfo.address_line2}
                    onChange={(e) => setKycInfo({ ...kycInfo, address_line2: e.target.value })}
                    placeholder="Apt, suite, etc."
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="profile_kyc_city">City</Label>
                    <Input
                      id="profile_kyc_city"
                      value={kycInfo.address_city}
                      onChange={(e) => setKycInfo({ ...kycInfo, address_city: e.target.value })}
                      placeholder="City"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile_kyc_state">State / Province</Label>
                    <Input
                      id="profile_kyc_state"
                      value={kycInfo.address_state}
                      onChange={(e) => setKycInfo({ ...kycInfo, address_state: e.target.value })}
                      placeholder="State or province"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile_kyc_postal_code">Postal code</Label>
                    <Input
                      id="profile_kyc_postal_code"
                      value={kycInfo.address_postal_code}
                      onChange={(e) => setKycInfo({ ...kycInfo, address_postal_code: e.target.value })}
                      placeholder="ZIP / Postal code"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="profile_kyc_country">Country</Label>
                  <Input
                    id="profile_kyc_country"
                    value={kycInfo.address_country}
                    onChange={(e) => setKycInfo({ ...kycInfo, address_country: e.target.value })}
                    placeholder="Country"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="profile_kyc_phone">Phone</Label>
                  <Input
                    id="profile_kyc_phone"
                    type="tel"
                    value={kycInfo.phone}
                    onChange={(e) => setKycInfo({ ...kycInfo, phone: e.target.value })}
                    placeholder="Phone number (e.g. E.164)"
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="profile_kyc_tax_id">Tax ID (SSN / TIN)</Label>
                    <Input
                      id="profile_kyc_tax_id"
                      type="password"
                      autoComplete="off"
                      value={kycInfo.tax_id}
                      onChange={(e) => setKycInfo({ ...kycInfo, tax_id: e.target.value })}
                      placeholder="e.g. XXX-XX-XXXX (USA)"
                    />
                    <p className="text-xs text-slate-400">Required for brokerage application. Stored securely.</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile_kyc_tax_id_type">Tax ID type</Label>
                    <select
                      id="profile_kyc_tax_id_type"
                      value={kycInfo.tax_id_type}
                      onChange={(e) => setKycInfo({ ...kycInfo, tax_id_type: e.target.value })}
                      className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="USA_SSN">USA SSN</option>
                      <option value="USA_TIN">USA TIN</option>
                    </select>
                  </div>
                </div>
                <Button onClick={handleSaveKycInfo} disabled={saving}>
                  {saving ? 'Saving...' : 'Save KYC information'}
                </Button>
              </CardContent>
            </Card>
          </div>
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

              <div className="border-t border-slate-700 pt-4 mt-4">
                <p className="text-sm font-medium text-slate-300 mb-3">KYC & Brokerage</p>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Shield className="h-5 w-5 text-slate-400" />
                      <div>
                        <Label htmlFor="kyc_brokerage_notifications">KYC & Brokerage status notifications</Label>
                        <p className="text-xs text-slate-400">Notify when KYC or brokerage account status changes</p>
                      </div>
                    </div>
                    <Switch
                      id="kyc_brokerage_notifications"
                      checked={preferences.kyc_brokerage_notifications}
                      onCheckedChange={(checked) => setPreferences({ ...preferences, kyc_brokerage_notifications: checked })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Link2 className="h-5 w-5 text-slate-400" />
                      <div>
                        <Label htmlFor="brokerage_plaid_kyc_preferred">Prefer Plaid for brokerage KYC</Label>
                        <p className="text-xs text-slate-400">When applying for a trading account, prefer using Plaid identity when available</p>
                      </div>
                    </div>
                    <Switch
                      id="brokerage_plaid_kyc_preferred"
                      checked={preferences.brokerage_plaid_kyc_preferred}
                      onCheckedChange={(checked) => setPreferences({ ...preferences, brokerage_plaid_kyc_preferred: checked })}
                    />
                  </div>
                </div>
              </div>
              
              <Button onClick={handleSavePreferences} disabled={saving}>
                {saving ? 'Saving...' : 'Save Preferences'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="kyc-identity">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Information used for KYC</CardTitle>
                <CardDescription>
                  Edit the information used for identity verification. This prefill is used when you apply for a trading account on the{' '}
                  <button type="button" onClick={() => handleTabChange('trading-account')} className="text-emerald-400 hover:underline">
                    Trading account
                  </button>
                  {' '}tab.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="kyc_legal_name">Legal name</Label>
                    <Input
                      id="kyc_legal_name"
                      value={kycInfo.legal_name}
                      onChange={(e) => setKycInfo({ ...kycInfo, legal_name: e.target.value })}
                      placeholder="Full legal name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="kyc_date_of_birth">Date of birth</Label>
                    <Input
                      id="kyc_date_of_birth"
                      type="date"
                      value={kycInfo.date_of_birth}
                      onChange={(e) => setKycInfo({ ...kycInfo, date_of_birth: e.target.value })}
                      placeholder="YYYY-MM-DD"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="kyc_address_line1">Address line 1</Label>
                  <Input
                    id="kyc_address_line1"
                    value={kycInfo.address_line1}
                    onChange={(e) => setKycInfo({ ...kycInfo, address_line1: e.target.value })}
                    placeholder="Street address"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="kyc_address_line2">Address line 2 (optional)</Label>
                  <Input
                    id="kyc_address_line2"
                    value={kycInfo.address_line2}
                    onChange={(e) => setKycInfo({ ...kycInfo, address_line2: e.target.value })}
                    placeholder="Apt, suite, etc."
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="kyc_address_city">City</Label>
                    <Input
                      id="kyc_address_city"
                      value={kycInfo.address_city}
                      onChange={(e) => setKycInfo({ ...kycInfo, address_city: e.target.value })}
                      placeholder="City"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="kyc_address_state">State / Province</Label>
                    <Input
                      id="kyc_address_state"
                      value={kycInfo.address_state}
                      onChange={(e) => setKycInfo({ ...kycInfo, address_state: e.target.value })}
                      placeholder="State or province"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="kyc_address_postal_code">Postal code</Label>
                    <Input
                      id="kyc_address_postal_code"
                      value={kycInfo.address_postal_code}
                      onChange={(e) => setKycInfo({ ...kycInfo, address_postal_code: e.target.value })}
                      placeholder="ZIP / Postal code"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="kyc_address_country">Country</Label>
                  <Input
                    id="kyc_address_country"
                    value={kycInfo.address_country}
                    onChange={(e) => setKycInfo({ ...kycInfo, address_country: e.target.value })}
                    placeholder="Country"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="kyc_phone">Phone</Label>
                  <Input
                    id="kyc_phone"
                    type="tel"
                    value={kycInfo.phone}
                    onChange={(e) => setKycInfo({ ...kycInfo, phone: e.target.value })}
                    placeholder="Phone number (e.g. E.164)"
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="kyc_tax_id">Tax ID (SSN / TIN)</Label>
                    <Input
                      id="kyc_tax_id"
                      type="password"
                      autoComplete="off"
                      value={kycInfo.tax_id}
                      onChange={(e) => setKycInfo({ ...kycInfo, tax_id: e.target.value })}
                      placeholder="e.g. XXX-XX-XXXX (USA)"
                    />
                    <p className="text-xs text-slate-400">Required for brokerage application. Stored securely.</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="kyc_tax_id_type">Tax ID type</Label>
                    <select
                      id="kyc_tax_id_type"
                      value={kycInfo.tax_id_type}
                      onChange={(e) => setKycInfo({ ...kycInfo, tax_id_type: e.target.value })}
                      className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="USA_SSN">USA SSN</option>
                      <option value="USA_TIN">USA TIN</option>
                    </select>
                  </div>
                </div>
                <Button onClick={handleSaveKycInfo} disabled={saving}>
                  {saving ? 'Saving...' : 'Save KYC information'}
                </Button>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>KYC & Identity status</CardTitle>
                <CardDescription>Your identity verification status for KYC and brokerage</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {kycStatus === null ? (
                  <p className="text-sm text-slate-400">Loading KYC status...</p>
                ) : kycStatus.status === 'not_initiated' ? (
                  <>
                    <p className="text-sm text-slate-300">KYC has not been started.</p>
                    <p className="text-xs text-slate-400">You can start identity verification when you open a trading account.</p>
                    <Button variant="outline" onClick={() => setActiveSettingsTab('trading-account')}>
                      <Briefcase className="h-4 w-4 mr-2" />
                      Open Trading account
                    </Button>
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">Status</span>
                      <span className="text-sm font-medium capitalize">{kycStatus.status}</span>
                    </div>
                    {kycStatus.verification && typeof kycStatus.verification === 'object' && 'kyc_level' in kycStatus.verification && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-400">Level</span>
                        <span className="text-sm">{String((kycStatus.verification as Record<string, unknown>).kyc_level)}</span>
                      </div>
                    )}
                    <Button variant="outline" onClick={() => setActiveSettingsTab('trading-account')}>
                      <Briefcase className="h-4 w-4 mr-2" />
                      Trading account
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        <TabsContent value="link-accounts">
          <div className="space-y-6">
            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Coins className="h-5 w-5 text-slate-400" />
                  Add credits
                </CardTitle>
                <CardDescription>
                  Top up rolling credits to use billable features. Pay with MetaMask, facilitator, or RevenueCat.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex gap-2 flex-wrap items-center">
                  <Input
                    type="text"
                    inputMode="decimal"
                    placeholder="Amount (USD)"
                    value={creditsAmount}
                    onChange={(e) => setCreditsAmount(e.target.value)}
                    className="max-w-[140px]"
                  />
                  <Button
                    size="sm"
                    disabled={creditsTopUpLoading || !creditsAmount || Number(creditsAmount) <= 0}
                    onClick={async () => {
                      setCreditsTopUpError(null);
                      setCreditsTopUpLoading(true);
                      try {
                        const r = await fetchWithPaymentHandling('/api/credits/top-up', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ amount: creditsAmount }),
                        });
                        if (r.ok) {
                          setCreditsAmount('');
                        } else if (r.status !== 402) {
                          const d = await r.json().catch(() => ({}));
                          setCreditsTopUpError(d.detail?.message ?? d.detail ?? 'Top-up failed');
                        }
                      } catch {
                        setCreditsTopUpError('Top-up failed');
                      } finally {
                        setCreditsTopUpLoading(false);
                      }
                    }}
                  >
                    {creditsTopUpLoading ? '…' : 'Top up'}
                  </Button>
                </div>
                {creditsTopUpError && <p className="text-sm text-red-400">{creditsTopUpError}</p>}
              </CardContent>
            </Card>
            <LinkAccounts />
          </div>
        </TabsContent>

        <TabsContent value="bring-your-own-keys">
          {byokAccess === null ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-slate-400">Loading…</p>
              </CardContent>
            </Card>
          ) : !byokAccess.allowed ? (
            <Card>
              <CardHeader>
                <CardTitle>Bring Your Own Keys</CardTitle>
                <CardDescription>
                  Upgrade or complete payment to configure your own API keys for trading and market data (Alpaca, Polygon, Polymarket). Bank and brokerage linking stays in Link Accounts.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-amber-500 text-sm mb-4">BYOK access is paywalled. Subscribe or add credits to unlock.</p>
                <Button asChild>
                  <Link to="/settings?tab=profile">Go to profile</Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <BringYourOwnKeys />
          )}
        </TabsContent>
        
        <TabsContent value="trading-account">
          {tradingUnlocked === null ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-slate-400">Loading…</p>
              </CardContent>
            </Card>
          ) : !tradingUnlocked ? (
            <Card>
              <CardHeader>
                <CardTitle>Trading account</CardTitle>
                <CardDescription>
                  Add an Alpaca key in Bring Your Own Keys to unlock trading. If you don’t have BYOK access yet, upgrade or complete payment to unlock Bring Your Own Keys first.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button onClick={() => handleTabChange('bring-your-own-keys')}>
                  <Key className="h-4 w-4 mr-2" />
                  Open Bring Your Own Keys
                </Button>
              </CardContent>
            </Card>
          ) : (
            <BrokerageOnboarding />
          )}
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
