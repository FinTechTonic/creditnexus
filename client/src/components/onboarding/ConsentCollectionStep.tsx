import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { CheckCircle2, XCircle, FileText, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ConsentCollectionStepProps {
  onConsentChange: (consents: Record<string, boolean>) => void;
}

const REQUIRED_CONSENTS = [
  {
    id: 'essential',
    title: 'Essential Services',
    description: 'Required for account functionality and service delivery. This includes authentication, transaction processing, and compliance with legal obligations.',
    required: true,
    legal_basis: 'contract'
  },
  {
    id: 'analytics',
    title: 'Analytics & Performance',
    description: 'Help us improve our services through usage analytics and performance monitoring. This data is anonymized and aggregated.',
    required: false,
    legal_basis: 'consent'
  },
  {
    id: 'marketing',
    title: 'Marketing Communications',
    description: 'Receive updates about new features, services, and relevant financial products. You can unsubscribe at any time.',
    required: false,
    legal_basis: 'consent'
  },
  {
    id: 'third_party',
    title: 'Third-Party Services',
    description: 'Share non-essential data with trusted third-party service providers for enhanced functionality (e.g., payment processors, analytics tools).',
    required: false,
    legal_basis: 'consent'
  }
];

export function ConsentCollectionStep({ onConsentChange }: ConsentCollectionStepProps) {
  const navigate = useNavigate();
  const [consents, setConsents] = useState<Record<string, boolean>>({
    essential: true,  // Required
    analytics: false,
    marketing: false,
    third_party: false
  });
  
  const handleConsentChange = (consentId: string, value: boolean) => {
    if (consentId === 'essential') return; // Can't change essential
    
    setConsents(prev => ({
      ...prev,
      [consentId]: value
    }));
  };
  
  const handleSubmit = () => {
    onConsentChange(consents);
  };
  
  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <h3 className="text-xl font-semibold text-slate-100 mb-2">
          Privacy & Consent
        </h3>
        <p className="text-slate-400 mb-4">
          Please review our privacy policy and provide your consent for data processing
        </p>
        <Button
          variant="link"
          onClick={() => navigate('/privacy-policy')}
          className="text-emerald-400 hover:text-emerald-300"
        >
          <FileText className="h-4 w-4 mr-2" />
          View Privacy Policy
          <ExternalLink className="h-3 w-3 ml-2" />
        </Button>
      </div>
      
      <div className="space-y-4">
        {REQUIRED_CONSENTS.map((consent) => (
          <Card key={consent.id} className="bg-slate-900 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-start gap-4">
                <Checkbox
                  checked={consents[consent.id]}
                  onCheckedChange={(checked) => 
                    handleConsentChange(consent.id, checked as boolean)
                  }
                  disabled={consent.required}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-slate-100">{consent.title}</span>
                    {consent.required && (
                      <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded">
                        Required
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-400 mb-2">{consent.description}</p>
                  <p className="text-xs text-slate-500">
                    Legal basis: <span className="text-slate-400">{consent.legal_basis}</span>
                  </p>
                </div>
                <div className="flex-shrink-0">
                  {consents[consent.id] ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <XCircle className="h-5 w-5 text-slate-500" />
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      
      <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
        <p className="text-sm text-slate-400">
          <strong className="text-slate-300">Your Rights:</strong> You can withdraw your consent at any time 
          by visiting the GDPR Dashboard in your account settings. Withdrawing consent will not affect the 
          lawfulness of processing based on consent before its withdrawal.
        </p>
      </div>
      
      <Button
        onClick={handleSubmit}
        className="w-full bg-emerald-600 hover:bg-emerald-700"
        disabled={!consents.essential}  // Essential must be checked
      >
        Continue
      </Button>
    </div>
  );
}
