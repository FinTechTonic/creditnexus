import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Cookie, X, Settings, CheckCircle2 } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface CookieBannerProps {
  onConsentChange?: (consents: Record<string, boolean>) => void;
}

const COOKIE_CATEGORIES = [
  {
    id: 'essential',
    title: 'Essential Cookies',
    description: 'Required for the website to function properly. These cannot be disabled.',
    required: true,
    legal_basis: 'contract'
  },
  {
    id: 'analytics',
    title: 'Analytics Cookies',
    description: 'Help us understand how visitors interact with our website by collecting and reporting information anonymously.',
    required: false,
    legal_basis: 'consent'
  },
  {
    id: 'marketing',
    title: 'Marketing Cookies',
    description: 'Used to track visitors across websites to display relevant advertisements.',
    required: false,
    legal_basis: 'consent'
  },
  {
    id: 'functional',
    title: 'Functional Cookies',
    description: 'Enable enhanced functionality and personalization, such as remembering your preferences.',
    required: false,
    legal_basis: 'consent'
  }
];

export function CookieBanner({ onConsentChange }: CookieBannerProps) {
  const [showBanner, setShowBanner] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [consents, setConsents] = useState<Record<string, boolean>>({
    essential: true, // Always required
    analytics: false,
    marketing: false,
    functional: false
  });

  useEffect(() => {
    // Check if user has already provided consent
    const cookieConsent = localStorage.getItem('cookie_consent');
    if (!cookieConsent) {
      setShowBanner(true);
    } else {
      // Load saved consents
      try {
        const saved = JSON.parse(cookieConsent);
        setConsents(saved);
      } catch (e) {
        // Invalid saved data, show banner again
        setShowBanner(true);
      }
    }
  }, []);

  const handleAcceptAll = async () => {
    const allConsents = {
      essential: true,
      analytics: true,
      marketing: true,
      functional: true
    };
    await saveConsents(allConsents);
  };

  const handleRejectAll = async () => {
    const minimalConsents = {
      essential: true, // Required
      analytics: false,
      marketing: false,
      functional: false
    };
    await saveConsents(minimalConsents);
  };

  const handleSavePreferences = async () => {
    await saveConsents(consents);
    setShowSettings(false);
  };

  const saveConsents = async (newConsents: Record<string, boolean>) => {
    // Save to localStorage
    localStorage.setItem('cookie_consent', JSON.stringify(newConsents));
    localStorage.setItem('cookie_consent_date', new Date().toISOString());
    
    setConsents(newConsents);
    setShowBanner(false);
    
    // Record consents via API if user is authenticated
    try {
      const token = localStorage.getItem('token');
      if (token) {
        for (const [consentType, given] of Object.entries(newConsents)) {
          if (consentType !== 'essential') { // Essential doesn't need API call
            const category = COOKIE_CATEGORIES.find(c => c.id === consentType);
            if (category) {
              await fetchWithAuth('/api/gdpr/consents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  consent_type: `cookie_${consentType}`,
                  consent_purpose: category.description,
                  legal_basis: category.legal_basis,
                  consent_given: given,
                  consent_source: 'cookie_banner'
                })
              });
            }
          }
        }
      }
    } catch (e) {
      console.error('Failed to record cookie consents:', e);
      // Non-blocking - consents are saved locally
    }
    
    if (onConsentChange) {
      onConsentChange(newConsents);
    }
  };

  const toggleConsent = (consentId: string) => {
    if (consentId === 'essential') return; // Can't toggle essential
    
    setConsents(prev => ({
      ...prev,
      [consentId]: !prev[consentId]
    }));
  };

  if (!showBanner && !showSettings) {
    return null;
  }

  if (showSettings) {
    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-2xl bg-slate-900 border-slate-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-slate-100">Cookie Preferences</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowSettings(false)}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
            
            <p className="text-slate-400 mb-6">
              Manage your cookie preferences. You can enable or disable different types of cookies below.
            </p>
            
            <div className="space-y-4 mb-6">
              {COOKIE_CATEGORIES.map((category) => (
                <div
                  key={category.id}
                  className="flex items-start gap-4 p-4 border border-slate-700 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-slate-100">{category.title}</h3>
                      {category.required && (
                        <span className="text-xs text-slate-500">(Required)</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-400 mb-2">{category.description}</p>
                    <p className="text-xs text-slate-500">
                      Legal basis: {category.legal_basis}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {consents[category.id] ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                    ) : (
                      <div className="h-5 w-5 rounded-full border-2 border-slate-500" />
                    )}
                    <input
                      type="checkbox"
                      checked={consents[category.id]}
                      onChange={() => toggleConsent(category.id)}
                      disabled={category.required}
                      className="h-5 w-5 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                    />
                  </div>
                </div>
              ))}
            </div>
            
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowSettings(false)}
              >
                Cancel
              </Button>
              <Button onClick={handleSavePreferences}>
                Save Preferences
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4">
      <Card className="max-w-4xl mx-auto bg-slate-900 border-slate-700 shadow-2xl">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <Cookie className="h-6 w-6 text-emerald-400 flex-shrink-0 mt-1" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-slate-100 mb-2">
                We use cookies
              </h3>
              <p className="text-sm text-slate-400 mb-4">
                We use cookies to enhance your browsing experience, analyze site traffic, and personalize content. 
                By clicking "Accept All", you consent to our use of cookies. You can manage your preferences at any time.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button
                  onClick={handleRejectAll}
                  variant="outline"
                  size="sm"
                >
                  Reject All
                </Button>
                <Button
                  onClick={() => setShowSettings(true)}
                  variant="outline"
                  size="sm"
                >
                  <Settings className="h-4 w-4 mr-2" />
                  Customize
                </Button>
                <Button
                  onClick={handleAcceptAll}
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  Accept All
                </Button>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleRejectAll}
              className="flex-shrink-0"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
