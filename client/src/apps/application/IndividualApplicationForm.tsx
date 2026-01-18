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
  AlertCircle
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface FormData {
  // Personal Information
  name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
  
  // Financial Information
  income: string;
  employmentStatus: string;
  employerName: string;
  creditScoreRange: string;
  
  // Loan Requirements
  loanAmount: string;
  loanPurpose: string;
  termPreference: string;
  
  // Documents
  documents: File[];
}

type FormStep = 'personal' | 'financial' | 'loan' | 'documents' | 'review';

const steps: { id: FormStep; title: string; description: string }[] = [
  { id: 'personal', title: 'Personal Information', description: 'Your basic details' },
  { id: 'financial', title: 'Financial Information', description: 'Income and employment' },
  { id: 'loan', title: 'Loan Requirements', description: 'Loan amount and purpose' },
  { id: 'documents', title: 'Documents', description: 'Upload required documents' },
  { id: 'review', title: 'Review', description: 'Review and submit' },
];

interface IndividualApplicationFormProps {
  onComplete?: (applicationId: number) => void;
}

export function IndividualApplicationForm({ onComplete }: IndividualApplicationFormProps = {}) {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<FormStep>('personal');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    zipCode: '',
    country: '',
    income: '',
    employmentStatus: '',
    employerName: '',
    creditScoreRange: '',
    loanAmount: '',
    loanPurpose: '',
    termPreference: '',
    documents: [],
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const currentStepIndex = steps.findIndex(s => s.id === currentStep);

  const validateStep = (step: FormStep): boolean => {
    const errors: Record<string, string> = {};

    if (step === 'personal') {
      if (!formData.name.trim()) errors.name = 'Name is required';
      if (!formData.email.trim()) errors.email = 'Email is required';
      else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) errors.email = 'Invalid email format';
      if (!formData.phone.trim()) errors.phone = 'Phone is required';
      if (!formData.address.trim()) errors.address = 'Address is required';
      if (!formData.city.trim()) errors.city = 'City is required';
      if (!formData.state.trim()) errors.state = 'State is required';
      if (!formData.zipCode.trim()) errors.zipCode = 'ZIP code is required';
      if (!formData.country.trim()) errors.country = 'Country is required';
    } else if (step === 'financial') {
      if (!formData.income.trim()) errors.income = 'Income is required';
      else if (isNaN(Number(formData.income)) || Number(formData.income) <= 0) {
        errors.income = 'Income must be a positive number';
      }
      if (!formData.employmentStatus) errors.employmentStatus = 'Employment status is required';
      if (!formData.creditScoreRange) errors.creditScoreRange = 'Credit score range is required';
    } else if (step === 'loan') {
      if (!formData.loanAmount.trim()) errors.loanAmount = 'Loan amount is required';
      else if (isNaN(Number(formData.loanAmount)) || Number(formData.loanAmount) <= 0) {
        errors.loanAmount = 'Loan amount must be a positive number';
      }
      if (!formData.loanPurpose.trim()) errors.loanPurpose = 'Loan purpose is required';
      if (!formData.termPreference) errors.termPreference = 'Term preference is required';
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

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const validFiles = files.filter(file => {
      const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
      const maxSize = 10 * 1024 * 1024; // 10MB
      return validTypes.includes(file.type) && file.size <= maxSize;
    });

    setFormData(prev => ({
      ...prev,
      documents: [...prev.documents, ...validFiles],
    }));
  };

  const removeFile = (index: number) => {
    setFormData(prev => ({
      ...prev,
      documents: prev.documents.filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = async () => {
    if (!validateStep('review')) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Prepare form data
      const individualData = {
        personal: {
          name: formData.name,
          email: formData.email,
          phone: formData.phone,
          address: {
            street: formData.address,
            city: formData.city,
            state: formData.state,
            zipCode: formData.zipCode,
            country: formData.country,
          },
        },
        financial: {
          income: Number(formData.income),
          employmentStatus: formData.employmentStatus,
          employerName: formData.employerName,
          creditScoreRange: formData.creditScoreRange,
        },
        loan: {
          amount: Number(formData.loanAmount),
          purpose: formData.loanPurpose,
          termPreference: formData.termPreference,
        },
      };

      // Create application
      const response = await fetchWithAuth('/api/applications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          application_type: 'individual',
          individual_data: individualData,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create application');
      }

      const application = await response.json();

      // Upload documents if any
      if (formData.documents.length > 0) {
        // Note: Document upload would need a separate endpoint
        // For now, we'll just create the application
        console.log('Documents to upload:', formData.documents);
      }

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
    // Clear validation error for this field
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

            {/* Step 1: Personal Information */}
            {currentStep === 'personal' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Full Name *
                  </label>
                  <Input
                    value={formData.name}
                    onChange={(e) => updateField('name', e.target.value)}
                    className="bg-slate-900 border-slate-700 text-slate-100"
                    placeholder="John Doe"
                  />
                  {validationErrors.name && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.name}</p>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Email *
                    </label>
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) => updateField('email', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="john@example.com"
                    />
                    {validationErrors.email && (
                      <p className="text-red-400 text-sm mt-1">{validationErrors.email}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Phone *
                    </label>
                    <Input
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => updateField('phone', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="+1 (555) 123-4567"
                    />
                    {validationErrors.phone && (
                      <p className="text-red-400 text-sm mt-1">{validationErrors.phone}</p>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Address *
                  </label>
                  <Input
                    value={formData.address}
                    onChange={(e) => updateField('address', e.target.value)}
                    className="bg-slate-900 border-slate-700 text-slate-100"
                    placeholder="123 Main Street"
                  />
                  {validationErrors.address && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.address}</p>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      City *
                    </label>
                    <Input
                      value={formData.city}
                      onChange={(e) => updateField('city', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="New York"
                    />
                    {validationErrors.city && (
                      <p className="text-red-400 text-sm mt-1">{validationErrors.city}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      State *
                    </label>
                    <Input
                      value={formData.state}
                      onChange={(e) => updateField('state', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="NY"
                    />
                    {validationErrors.state && (
                      <p className="text-red-400 text-sm mt-1">{validationErrors.state}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      ZIP Code *
                    </label>
                    <Input
                      value={formData.zipCode}
                      onChange={(e) => updateField('zipCode', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="10001"
                    />
                    {validationErrors.zipCode && (
                      <p className="text-red-400 text-sm mt-1">{validationErrors.zipCode}</p>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Country *
                  </label>
                  <Input
                    value={formData.country}
                    onChange={(e) => updateField('country', e.target.value)}
                    className="bg-slate-900 border-slate-700 text-slate-100"
                    placeholder="United States"
                  />
                  {validationErrors.country && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.country}</p>
                  )}
                </div>
              </div>
            )}

            {/* Step 2: Financial Information */}
            {currentStep === 'financial' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Annual Income (USD) *
                  </label>
                  <Input
                    type="number"
                    value={formData.income}
                    onChange={(e) => updateField('income', e.target.value)}
                    className="bg-slate-900 border-slate-700 text-slate-100"
                    placeholder="75000"
                  />
                  {validationErrors.income && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.income}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Employment Status *
                  </label>
                  <select
                    value={formData.employmentStatus}
                    onChange={(e) => updateField('employmentStatus', e.target.value)}
                    className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="">Select employment status</option>
                    <option value="employed">Employed</option>
                    <option value="self_employed">Self-Employed</option>
                    <option value="unemployed">Unemployed</option>
                    <option value="retired">Retired</option>
                    <option value="student">Student</option>
                  </select>
                  {validationErrors.employmentStatus && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.employmentStatus}</p>
                  )}
                </div>

                {formData.employmentStatus === 'employed' || formData.employmentStatus === 'self_employed' ? (
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Employer Name
                    </label>
                    <Input
                      value={formData.employerName}
                      onChange={(e) => updateField('employerName', e.target.value)}
                      className="bg-slate-900 border-slate-700 text-slate-100"
                      placeholder="Company Name"
                    />
                  </div>
                ) : null}

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Credit Score Range *
                  </label>
                  <select
                    value={formData.creditScoreRange}
                    onChange={(e) => updateField('creditScoreRange', e.target.value)}
                    className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="">Select credit score range</option>
                    <option value="300-579">300-579 (Poor)</option>
                    <option value="580-669">580-669 (Fair)</option>
                    <option value="670-739">670-739 (Good)</option>
                    <option value="740-799">740-799 (Very Good)</option>
                    <option value="800-850">800-850 (Excellent)</option>
                  </select>
                  {validationErrors.creditScoreRange && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.creditScoreRange}</p>
                  )}
                </div>
              </div>
            )}

            {/* Step 3: Loan Requirements */}
            {currentStep === 'loan' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Loan Amount (USD) *
                  </label>
                  <Input
                    type="number"
                    value={formData.loanAmount}
                    onChange={(e) => updateField('loanAmount', e.target.value)}
                    className="bg-slate-900 border-slate-700 text-slate-100"
                    placeholder="50000"
                  />
                  {validationErrors.loanAmount && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.loanAmount}</p>
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

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Term Preference *
                  </label>
                  <select
                    value={formData.termPreference}
                    onChange={(e) => updateField('termPreference', e.target.value)}
                    className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="">Select term preference</option>
                    <option value="12">12 months</option>
                    <option value="24">24 months</option>
                    <option value="36">36 months</option>
                    <option value="48">48 months</option>
                    <option value="60">60 months</option>
                    <option value="other">Other</option>
                  </select>
                  {validationErrors.termPreference && (
                    <p className="text-red-400 text-sm mt-1">{validationErrors.termPreference}</p>
                  )}
                </div>
              </div>
            )}

            {/* Step 4: Documents */}
            {currentStep === 'documents' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Upload Documents
                  </label>
                  <p className="text-sm text-slate-400 mb-4">
                    Upload ID, proof of income, bank statements (PDF, JPG, PNG - Max 10MB each)
                  </p>
                  <div className="border-2 border-dashed border-slate-700 rounded-lg p-6 text-center">
                    <Upload className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="file-upload"
                    />
                    <label
                      htmlFor="file-upload"
                      className="cursor-pointer inline-flex items-center px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg"
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Choose Files
                    </label>
                  </div>

                  {formData.documents.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {formData.documents.map((file, index) => (
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
                            onClick={() => removeFile(index)}
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
                  <h3 className="text-lg font-semibold text-slate-100 mb-4">Personal Information</h3>
                  <div className="bg-slate-900 rounded-lg p-4 space-y-2 text-sm">
                    <p><span className="text-slate-400">Name:</span> <span className="text-slate-100">{formData.name}</span></p>
                    <p><span className="text-slate-400">Email:</span> <span className="text-slate-100">{formData.email}</span></p>
                    <p><span className="text-slate-400">Phone:</span> <span className="text-slate-100">{formData.phone}</span></p>
                    <p><span className="text-slate-400">Address:</span> <span className="text-slate-100">{formData.address}, {formData.city}, {formData.state} {formData.zipCode}, {formData.country}</span></p>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-4">Financial Information</h3>
                  <div className="bg-slate-900 rounded-lg p-4 space-y-2 text-sm">
                    <p><span className="text-slate-400">Annual Income:</span> <span className="text-slate-100">${Number(formData.income).toLocaleString()}</span></p>
                    <p><span className="text-slate-400">Employment Status:</span> <span className="text-slate-100 capitalize">{formData.employmentStatus.replace('_', ' ')}</span></p>
                    {formData.employerName && (
                      <p><span className="text-slate-400">Employer:</span> <span className="text-slate-100">{formData.employerName}</span></p>
                    )}
                    <p><span className="text-slate-400">Credit Score:</span> <span className="text-slate-100">{formData.creditScoreRange}</span></p>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-4">Loan Requirements</h3>
                  <div className="bg-slate-900 rounded-lg p-4 space-y-2 text-sm">
                    <p><span className="text-slate-400">Loan Amount:</span> <span className="text-slate-100">${Number(formData.loanAmount).toLocaleString()}</span></p>
                    <p><span className="text-slate-400">Purpose:</span> <span className="text-slate-100">{formData.loanPurpose}</span></p>
                    <p><span className="text-slate-400">Term:</span> <span className="text-slate-100">{formData.termPreference} months</span></p>
                  </div>
                </div>

                {formData.documents.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-4">Documents ({formData.documents.length})</h3>
                    <div className="bg-slate-900 rounded-lg p-4 space-y-2">
                      {formData.documents.map((file, index) => (
                        <p key={index} className="text-sm text-slate-300">{file.name}</p>
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
                  disabled={loading}
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
