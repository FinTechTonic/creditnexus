// #region agent log
/*
fetch('http://127.0.0.1:7242/ingest/b4962ed0-f261-4fa9-86f3-a557335b330a',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client/src/components/QuickAccessSettings.tsx:start',message:'Creating QuickAccessSettings component',data:{todoId:'phase1-issue005-022'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
*/
// #endregion
import { useState, useEffect } from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Mic, TrendingUp, Building2, DollarSign } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

interface UserPreferences {
  audio_input_mode: boolean;
  investment_mode: boolean;
  loan_mode: boolean;
  bank_mode: boolean;
  trading_mode: boolean;
}

export function QuickAccessSettings() {
  const { user } = useAuth();
  const [preferences, setPreferences] = useState<UserPreferences>({
    audio_input_mode: false,
    investment_mode: false,
    loan_mode: false,
    bank_mode: false,
    trading_mode: false,
  });
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Load preferences from API
    const loadPreferences = async () => {
      try {
        const response = await fetch('/api/user-settings/preferences');
        if (response.ok) {
          const data = await response.json();
          setPreferences({
            audio_input_mode: data.audio_input_mode || false,
            investment_mode: data.investment_mode || false,
            loan_mode: data.loan_mode || false,
            bank_mode: data.bank_mode || false,
            trading_mode: data.trading_mode || false,
          });
        }
      } catch (error) {
        console.error('Failed to load preferences:', error);
      } finally {
        setLoading(false);
      }
    };
    
    if (user) {
      loadPreferences();
    }
  }, [user]);
  
  const updatePreference = async (key: keyof UserPreferences, value: boolean) => {
    const newPrefs = { ...preferences, [key]: value };
    setPreferences(newPrefs);
    
    try {
      await fetch('/api/user-settings/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPrefs)
      });
    } catch (error) {
      console.error('Failed to update preference:', error);
      // Revert on error
      setPreferences(preferences);
    }
  };

  if (loading) {
    return null;
  }

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="text-sm">Quick Access</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Mic className="h-4 w-4 text-slate-400" />
            <Label htmlFor="audio-input" className="text-sm">Audio Input</Label>
          </div>
          <Switch
            id="audio-input"
            checked={preferences.audio_input_mode}
            onCheckedChange={(checked) => updatePreference('audio_input_mode', checked)}
          />
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-slate-400" />
            <Label htmlFor="investment-mode" className="text-sm">Investment Mode</Label>
          </div>
          <Switch
            id="investment-mode"
            checked={preferences.investment_mode}
            onCheckedChange={(checked) => updatePreference('investment_mode', checked)}
          />
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-slate-400" />
            <Label htmlFor="loan-mode" className="text-sm">Loan Mode</Label>
          </div>
          <Switch
            id="loan-mode"
            checked={preferences.loan_mode}
            onCheckedChange={(checked) => updatePreference('loan_mode', checked)}
          />
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-slate-400" />
            <Label htmlFor="bank-mode" className="text-sm">Bank Mode</Label>
          </div>
          <Switch
            id="bank-mode"
            checked={preferences.bank_mode}
            onCheckedChange={(checked) => updatePreference('bank_mode', checked)}
          />
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-slate-400" />
            <Label htmlFor="trading-mode" className="text-sm">Trading Mode</Label>
          </div>
          <Switch
            id="trading-mode"
            checked={preferences.trading_mode}
            onCheckedChange={(checked) => updatePreference('trading_mode', checked)}
          />
        </div>
      </CardContent>
    </Card>
  );
}
