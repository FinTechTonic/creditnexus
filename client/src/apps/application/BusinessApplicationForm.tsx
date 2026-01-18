import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  FileText, 
  ArrowRight, 
  ArrowLeft, 
  CheckCircle, 
  Loader2,
  Upload,
  X,
  AlertCircle,
  TrendingUp,
  TrendingDown
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface FormData {
  // Business Information
  companyName: string;
  lei: string;
  registrationNumber: string;
  industry: string;
  address: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
  
  // Business Type
  businessType: 'sell_debt' | 'buy_loan' | '';
  
  // Debt Selling Fields
  bondIssuer: string;
  bondMaturity: string;
  couponRate: string;
  faceValue: string;
  outstandingAmount: string;
  creditRating: string;
  collateralInfo: string;
  
  // Loan Buying Fields
  loanAmountNeeded: string;
  loanPurpose: string;
  loanTerm: string;
  interestRatePreference: string;
  collateralAvailable: string;
  
  // Financial Statements
  financialStatements: File[];
  
  // Legal Documents
  legalDocuments: File[];
}

type FormStep = 'business' | 'type' | 'details' | 'documents' | 'review';

const steps: { id: FormStep; title: string; description: string }[] = [
  { id: 'business', title: 'Business Information', description: 'Company details' },
  { id: 'type', title: 'Business Type', description: 'Select service type' },
  { id: 'details', title: 'Transaction Details', description: 'Transaction-specific information' },
  { id: 'documents', title: 'Documents', description: 'Upload required documents' },
  { id: 'review', title: 'Review', description: 'Review and submit' },
];

interface BusinessApplicationFormProps {
  defaultApplicationType?: 'debt_selling' | 'loan_buying';
  onComplete?: (applicationId: number) => void;
}

export function BusinessApplicationForm({ 
  defaultApplicationType,
  onComplete 
}: BusinessApplicationFormProps = {}) {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<FormStep>(
    defaultApplicationType ? 'business' : 'business'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>({
    companyName: '',
    lei: '',
    registrationNumber: '',
    industry: '',
    address: '',
    city: '',
    state: '',
    zipCode: '',
    country: '',
    businessType: defaultApplicationType === 'debt_selling' ? 'sell_debt' : defaultApplicationType === 'loan_buying' ? 'buy_loan' : '',
    bondIssuer: '',
    bondMaturity: '',
    couponRate: '',
    faceValue: '',
    outstandingAmount: '',
    creditRating: '',
    collateralInfo: '',
    loanAmountNeeded: '',
    loanPurpose: '',
    loanTerm: '',
    interestRatePreference: '',
    collateralAvailable: '',
    financialStatements: [],
    legalDocuments: [],
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const currentStepIndex = steps.findIndex(s => s.id === currentStep);

  const validateStep = (step: FormStep): boolean => {
    const errors: Record<string, string> = {};

    if (step === 'business') {
      if (!formData.companyName.trim()) errors.companyName = 'Company name is required';
      if (!formData.lei.trim()) errors.lei = 'LEI is required';
      if (!formData.registrationNumber.trim()) errors.registrationNumber = 'Registration number is required';
      if (!formData.industry.trim()) errors.industry = 'Industry is required';
      if (!formData.address.trim()) errors.address = 'Address is required';
      if (!formData.city.trim()) errors.city = 'City is required';
      if (!formData.state.trim()) errors.state = 'State is required';
      if (!formData.zipCode.trim()) errors.zipCode = 'ZIP code is required';
      if (!formData.country.trim()) errors.country = 'Country is required';
    } else if (step === 'type') {
      if (!formData.businessType) errors.businessType = 'Please select a business type';
    } else if (step === 'details') {
      if (formData.businessType === 'sell_debt') {
        if (!formData.bondIssuer.trim()) errors.bondIssuer = 'Bond issuer is required';
        if (!formData.bondMaturity.trim()) errors.bondMaturity = 'Bond maturity is required';
        if (!formData.couponRate.trim()) errors.couponRate = 'Coupon rate is required';
        if (!formData.faceValue.trim()) errors.faceValue = 'Face value is required';
        if (!formData.outstandingAmount.trim()) errors.outstandingAmount = 'Outstanding amount is required';
      } else if (formData.businessType === 'buy_loan') {
        if (!formData.loanAmountNeeded.trim()) errors.loanAmountNeeded = 'Loan amount is required';
        if (!formData.loanPurpose.trim()) errors.loanPurpose = 'Loan purpose is required';
        if (!formData.loanTerm.trim()) errors.loanTerm = 'Loan term is required';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleNext = () => {
    if (!validateStep(currentStep)) {
      return;
    }

    const nextIndex = currentStepIndex + 1;
    if (nextIndex < steps.length) {
      setCurrentStep(steps[nextIndex].id);
    }
  };

  const handleBack = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(steps[prevIndex].id);
    }
  };

  const handleFileUpload = (type: 'financial' | 'legal', e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const validFiles = files.filter(file => {
      const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
      const maxSize = 10 * 1024 * 1024; // 10MB
      return validTypes.includes(file.type) && file.size <= maxSize;
    });

    if (type === 'financial') {
      setFormData(prev => ({
        ...prev,
        financialStatements: [...prev.financialStatements, ...validFiles],
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        legalDocuments: [...prev.legalDocuments, ...validFiles],
      }));
    }
  };

  const removeFile = (type: 'financial' | 'legal', index: number) => {
    if (type === 'financial') {
      setFormData(prev => ({
        ...prev,
        financialStatements: prev.financialStatements.filter((_, i) => i !== index),
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        legalDocuments: prev.legalDocuments.filter((_, i) => i !== index),
      }));
    }
  };

  const handleSubmit = async () => {
    if (!validateStep('review')) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const businessData: Record<string, unknown> = {
        company: {
          name: formData.companyName,
          lei: formData.lei,
          registrationNumber: formData.registrationNumber,
          industry: formData.industry,
          address: {
            street: formData.address,
            city: formData.city,
            state: formData.state,
            zipCode: formData.zipCode,
            country: formData.country,
          },
        },
        businessType: formData.businessType,
      };

      if (formData.businessType === 'sell_debt') {
        businessData.debtSelling = {
          bondIssuer: formData.bondIssuer,
          bondMaturity: formData.bondMaturity,
          couponRate: Number(formData.couponRate),
          faceValue: Number(formData.faceValue),
          outstandingAmount: Number(formData.outstandingAmount),
          creditRating: formData.creditRating,
          collateralInfo: formData.collateralInfo,
        };
      } else if (formData.businessType === 'buy_loan') {
        businessData.loanBuying = {
          amountNeeded: Number(formData.loanAmountNeeded),
          purpose: formData.loanPurpose,
          term: formData.loanTerm,
          interestRatePreference: formData.interestRatePreference,
          collateralAvailable: formData.collateralAvailable,
        };
      }

      const response = await fetchWithAuth('/api/applications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          application_type: 'business',
          business_data: businessData,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create application');
      }

      const application = await response.json();

      // Call onComplete callback if provided, otherwise navigate
      if (onComplete) {
        onComplete(application.id);
      } else {
        navigate(`/dashboard/applications?success=${application.id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit application');
      console.error('Error submitting application:', err);
    } finally {
      setLoading(false);
    }
  };

  const updateField = (field: keyof FormData, value: string | File[]) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (validationErrors[field]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${
                      index <= currentStepIndex
                        ? 'bg-emerald-600 border-emerald-600 text-white'
                        : 'bg-slate-800 border-slate-700 text-slate-400'
                    }`}
                  >
                    {index < currentStepIndex ? (
                      <CheckCircle className="h-5 w-5" />
                    ) : (
                      <span>{index + 1}</span>
                    )}
                  </div>
                  <div className="mt-2 text-xs text-center max-w-[100px]">
                    <p className="text-slate-400">{step.title}</p>
                  </div>
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`h-1 flex-1 mx-2 ${
                      index < currentStepIndex ? 'bg-emerald-600' : 'bg-slate-700'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-2xl">{steps[currentStepIndex].title}</CardTitle>
            <CardDescription>{steps[currentStepIndex].description}</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-400">
                <AlertCircle className="h-5 w-5" />
                <span>{error}</span>
              </div>
            )}

            {/* Step 1: Business Information */}
            {currentStep === 'business' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Company Name *
                  </label>
                  <Input
                    value={formData.companyName}
                    onChange={(e) => updateField('companyName', e.target.value)}
                    className="bg-slate-900 border-slate-700 text-slate-100"
                    placeholder="ACME Corporation"
                  />
                  {validationErrors.companyName && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.companyName}</p>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Legal Entity Identifier (LEI) *
                    </label>
                    <Input
                      value={formData.lei}
                      onChange={(e) => updateField('lei', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="5493000X0X0X0X0X0X0X0X0X0X"
                    />
                    {validationErrors.lei && (
                      <p className="text-red-400 text-sm mt-1">{validationErrors.lei}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Registration Number *
                    </label>
                  <Input
                      value={formData.registrationNumber}
                      onChange={(e) => updateField('registrationNumber', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="12345678"
                    />
                    {validationErrors.registrationNumber && (
                      <p className="text-red-400 text-sm mt-1">{validationErrors.registrationNumber}</p>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Industry *
                  </label>
                  <Input
                    value={formData.industry}
                    onChange={(e) => updateField('industry', e.target.value)}
                    className="bg-slate-900 border-slate-700 text-slate-100"
                    placeholder="Financial Services"
                  />
                  {validationErrors.industry && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.industry}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Business Address *
                  </label>
                  <Input
                    value={formData.address}
                    onChange={(e) => updateField('address', e.target.value)}
                    className="bg-slate-900 border-slate-700 text-slate-100 mb-2"
                    placeholder="123 Business Street"
                  />
                  {validationErrors.address && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.address}</p>
                  )}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
                    <Input
                      value={formData.city}
                      onChange={(e) => updateField('city', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="City"
                    />
                    <Input
                      value={formData.state}
                      onChange={(e) => updateField('state', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="State"
                    />
                    <Input
                      value={formData.zipCode}
                      onChange={(e) => updateField('zipCode', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="ZIP Code"
                    />
                  </div>
                  <Input
                    value={formData.country}
                    onChange={(e) => updateField('country', e.target.value)}
                    className="bg-slate-900 border-slate-700 text-slate-100 mt-2"
                    placeholder="Country"
                  />
                </div>
              </div>
            )}

            {/* Step 2: Business Type Selection */}
            {currentStep === 'type' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-4">
                    What service are you interested in? *
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <button
                      type="button"
                      onClick={() => updateField('businessType', 'sell_debt')}
                      className={`p-6 rounded-lg border-2 transition-all text-left ${
                        formData.businessType === 'sell_debt'
                          ? 'border-emerald-600 bg-emerald-600/10'
                          : 'border-slate-700 bg-slate-900 hover:border-slate-600'
                      }`}
                    >
                      <TrendingDown className={`h-8 w-8 mb-3 ${formData.businessType === 'sell_debt' ? 'text-emerald-400' : 'text-slate-400'}`} />
                      <h3 className="text-lg font-semibold text-slate-100 mb-2">Sell Debt/Bonds</h3>
                      <p className="text-sm text-slate-400">
                        Sell your existing debt instruments or bonds to investors
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => updateField('businessType', 'buy_loan')}
                      className={`p-6 rounded-lg border-2 transition-all text-left ${
                        formData.businessType === 'buy_loan'
                          ? 'border-emerald-600 bg-emerald-600/10'
                          : 'border-slate-700 bg-slate-900 hover:border-slate-600'
                      }`}
                    >
                      <TrendingUp className={`h-8 w-8 mb-3 ${formData.businessType === 'buy_loan' ? 'text-emerald-400' : 'text-slate-400'}`} />
                      <h3 className="text-lg font-semibold text-slate-100 mb-2">Buy Loan</h3>
                      <p className="text-sm text-slate-400">
                        Apply for a business loan to fund your operations or expansion
                      </p>
                    </button>
                  </div>
                  {validationErrors.businessType && (
                    <p className="text-red-400 text-sm mt-2">{validationErrors.businessType}</p>
                  )}
                </div>
              </div>
            )}

            {/* Step 3: Transaction Details (Conditional) */}
            {currentStep === 'details' && (
              <div className="space-y-6">
                {formData.businessType === 'sell_debt' && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                      <TrendingDown className="h-5 w-5 text-emerald-400" />
                      Debt Selling Details
                    </h3>
                    
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Bond Issuer *
                      </label>
                      <Input
                        value={formData.bondIssuer}
                        onChange={(e) => updateField('bondIssuer', e.target.value)}
                        className="bg-slate-900 border-slate-700 text-slate-100"
                        placeholder="Issuer Company Name"
                      />
                      {validationErrors.bondIssuer && (
                        <p className="text-red-400 text-sm mt-1">{validationErrors.bondIssuer}</p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Bond Maturity Date *
                        </label>
                        <Input
                          type="date"
                          value={formData.bondMaturity}
                          onChange={(e) => updateField('bondMaturity', e.target.value)}
                          className="bg-slate-900 border-slate-700 text-slate-100"
                        />
                        {validationErrors.bondMaturity && (
                          <p className="text-red-400 text-sm mt-1">{validationErrors.bondMaturity}</p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Coupon Rate (%) *
                        </label>
                        <Input
                          type="number"
                          step="0.01"
                          value={formData.couponRate}
                          onChange={(e) => updateField('couponRate', e.target.value)}
                          className="bg-slate-900 border-slate-700 text-slate-100"
                          placeholder="5.25"
                        />
                        {validationErrors.couponRate && (
                          <p className="text-red-400 text-sm mt-1">{validationErrors.couponRate}</p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Face Value (USD) *
                        </label>
                        <Input
                          type="number"
                          value={formData.faceValue}
                          onChange={(e) => updateField('faceValue', e.target.value)}
                          className="bg-slate-900 border-slate-700 text-slate-100"
                          placeholder="1000000"
                        />
                        {validationErrors.faceValue && (
                          <p className="text-red-400 text-sm mt-1">{validationErrors.faceValue}</p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Outstanding Amount (USD) *
                        </label>
                        <Input
                          type="number"
                          value={formData.outstandingAmount}
                          onChange={(e) => updateField('outstandingAmount', e.target.value)}
                          className="bg-slate-900 border-slate-700 text-slate-100"
                          placeholder="750000"
                        />
                        {validationErrors.outstandingAmount && (
                          <p className="text-red-400 text-sm mt-1">{validationErrors.outstandingAmount}</p>
                        )}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Credit Rating
                      </label>
                      <select
                        value={formData.creditRating}
                        onChange={(e) => updateField('creditRating', e.target.value)}
                        className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      >
                        <option value="">Select credit rating</option>
                        <option value="AAA">AAA</option>
                        <option value="AA">AA</option>
                        <option value="A">A</option>
                        <option value="BBB">BBB</option>
                        <option value="BB">BB</option>
                        <option value="B">B</option>
                        <option value="CCC">CCC</option>
                        <option value="CC">CC</option>
                        <option value="C">C</option>
                        <option value="D">D</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Collateral Information
                      </label>
                      <textarea
                        value={formData.collateralInfo}
                        onChange={(e) => updateField('collateralInfo', e.target.value)}
                        className="w-full min-h-[100px] rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        placeholder="Describe any collateral backing this debt..."
                      />
                    </div>
                  </div>
                )}

                {formData.businessType === 'buy_loan' && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-emerald-400" />
                      Loan Requirements
                    </h3>

                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Loan Amount Needed (USD) *
                      </label>
                      <Input
                        type="number"
                        value={formData.loanAmountNeeded}
                        onChange={(e) => updateField('loanAmountNeeded', e.target.value)}
                        className="bg-slate-900 border-slate-700 text-slate-100"
                        placeholder="500000"
                      />
                      {validationErrors.loanAmountNeeded && (
                        <p className="text-red-400 text-sm mt-1">{validationErrors.loanAmountNeeded}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Loan Purpose *
                      </label>
                      <textarea
                        value={formData.loanPurpose}
                        onChange={(e) => updateField('loanPurpose', e.target.value)}
                        className="w-full min-h-[100px] rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        placeholder="Describe the purpose of the loan..."
                      />
                      {validationErrors.loanPurpose && (
                        <p className="text-red-400 text-sm mt-1">{validationErrors.loanPurpose}</p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Loan Term (months) *
                        </label>
                        <select
                          value={formData.loanTerm}
                          onChange={(e) => updateField('loanTerm', e.target.value)}
                          className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        >
                          <option value="">Select term</option>
                          <option value="12">12 months</option>
                          <option value="24">24 months</option>
                          <option value="36">36 months</option>
                          <option value="48">48 months</option>
                          <option value="60">60 months</option>
                          <option value="120">120 months (10 years)</option>
                        </select>
                        {validationErrors.loanTerm && (
                          <p className="text-red-400 text-sm mt-1">{validationErrors.loanTerm}</p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Interest Rate Preference (%)
                        </label>
                        <Input
                          type="number"
                          step="0.01"
                          value={formData.interestRatePreference}
                          onChange={(e) => updateField('interestRatePreference', e.target.value)}
                          className="bg-slate-900 border-slate-700 text-slate-100"
                          placeholder="5.5"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Collateral Available
                      </label>
                      <textarea
                        value={formData.collateralAvailable}
                        onChange={(e) => updateField('collateralAvailable', e.target.value)}
                        className="w-full min-h-[100px] rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        placeholder="Describe any collateral you can provide..."
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 4: Documents */}
            {currentStep === 'documents' && (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Financial Statements
                  </label>
                  <p className="text-sm text-slate-400 mb-4">
                    Upload balance sheet, income statement, cash flow (PDF, JPG, PNG - Max 10MB each)
                  </p>
                  <div className="border-2 border-dashed border-slate-700 rounded-lg p-6 text-center">
                    <Upload className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={(e) => handleFileUpload('financial', e)}
                      className="hidden"
                      id="financial-upload"
                    />
                    <label
                      htmlFor="financial-upload"
                      className="cursor-pointer inline-flex items-center px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg"
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Choose Financial Statements
                    </label>
                  </div>

                  {formData.financialStatements.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {formData.financialStatements.map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 bg-slate-900 rounded-lg border border-slate-700"
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-slate-400" />
                            <span className="text-sm text-slate-300">{file.name}</span>
                            <span className="text-xs text-slate-500">
                              ({(file.size / 1024 / 1024).toFixed(2)} MB)
                            </span>
                          </div>
                          <button
                            onClick={() => removeFile('financial', index)}
                            className="text-red-400 hover:text-red-300"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Legal Documents
                  </label>
                  <p className="text-sm text-slate-400 mb-4">
                    Upload articles of incorporation, board resolution (PDF, JPG, PNG - Max 10MB each)
                  </p>
                  <div className="border-2 border-dashed border-slate-700 rounded-lg p-6 text-center">
                    <Upload className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={(e) => handleFileUpload('legal', e)}
                      className="hidden"
                      id="legal-upload"
                    />
                    <label
                      htmlFor="legal-upload"
                      className="cursor-pointer inline-flex items-center px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg"
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Choose Legal Documents
                    </label>
                  </div>

                  {formData.legalDocuments.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {formData.legalDocuments.map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 bg-slate-900 rounded-lg border border-slate-700"
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-slate-400" />
                            <span className="text-sm text-slate-300">{file.name}</span>
                            <span className="text-xs text-slate-500">
                              ({(file.size / 1024 / 1024).toFixed(2)} MB)
                            </span>
                          </div>
                          <button
                            onClick={() => removeFile('legal', index)}
                            className="text-red-400 hover:text-red-300"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Step 5: Review */}
            {currentStep === 'review' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-4">Business Information</h3>
                  <div className="bg-slate-900 rounded-lg p-4 space-y-2 text-sm">
                    <p><span className="text-slate-400">Company:</span> <span className="text-slate-100">{formData.companyName}</span></p>
                    <p><span className="text-slate-400">LEI:</span> <span className="text-slate-100">{formData.lei}</span></p>
                    <p><span className="text-slate-400">Registration:</span> <span className="text-slate-100">{formData.registrationNumber}</span></p>
                    <p><span className="text-slate-400">Industry:</span> <span className="text-slate-100">{formData.industry}</span></p>
                    <p><span className="text-slate-400">Address:</span> <span className="text-slate-100">{formData.address}, {formData.city}, {formData.state} {formData.zipCode}, {formData.country}</span></p>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-4">
                    {formData.businessType === 'sell_debt' ? 'Debt Selling Details' : 'Loan Requirements'}
                  </h3>
                  <div className="bg-slate-900 rounded-lg p-4 space-y-2 text-sm">
                    {formData.businessType === 'sell_debt' ? (
                      <>
                        <p><span className="text-slate-400">Bond Issuer:</span> <span className="text-slate-100">{formData.bondIssuer}</span></p>
                        <p><span className="text-slate-400">Maturity:</span> <span className="text-slate-100">{formData.bondMaturity}</span></p>
                        <p><span className="text-slate-400">Coupon Rate:</span> <span className="text-slate-100">{formData.couponRate}%</span></p>
                        <p><span className="text-slate-400">Face Value:</span> <span className="text-slate-100">${Number(formData.faceValue).toLocaleString()}</span></p>
                        <p><span className="text-slate-400">Outstanding:</span> <span className="text-slate-100">${Number(formData.outstandingAmount).toLocaleString()}</span></p>
                        {formData.creditRating && (
                          <p><span className="text-slate-400">Credit Rating:</span> <span className="text-slate-100">{formData.creditRating}</span></p>
                        )}
                      </>
                    ) : (
                      <>
                        <p><span className="text-slate-400">Loan Amount:</span> <span className="text-slate-100">${Number(formData.loanAmountNeeded).toLocaleString()}</span></p>
                        <p><span className="text-slate-400">Purpose:</span> <span className="text-slate-100">{formData.loanPurpose}</span></p>
                        <p><span className="text-slate-400">Term:</span> <span className="text-slate-100">{formData.loanTerm} months</span></p>
                        {formData.interestRatePreference && (
                          <p><span className="text-slate-400">Rate Preference:</span> <span className="text-slate-100">{formData.interestRatePreference}%</span></p>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {(formData.financialStatements.length > 0 || formData.legalDocuments.length > 0) && (
                  <div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-4">
                      Documents ({formData.financialStatements.length + formData.legalDocuments.length})
                    </h3>
                    <div className="bg-slate-900 rounded-lg p-4 space-y-2">
                      {formData.financialStatements.map((file, index) => (
                        <p key={`financial-${index}`} className="text-sm text-slate-300">Financial: {file.name}</p>
                      ))}
                      {formData.legalDocuments.map((file, index) => (
                        <p key={`legal-${index}`} className="text-sm text-slate-300">Legal: {file.name}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-slate-700">
              <Button
                variant="outline"
                onClick={currentStepIndex === 0 ? () => navigate('/apply') : handleBack}
                disabled={loading}
                className="border-slate-700 text-slate-300 hover:bg-slate-700"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                {currentStepIndex === 0 ? 'Cancel' : 'Back'}
              </Button>

              {currentStepIndex < steps.length - 1 ? (
                <Button
                  onClick={handleNext}
                  disabled={loading || (currentStep === 'type' && !formData.businessType)}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  Next
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Submit Application
                    </>
                  )}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
