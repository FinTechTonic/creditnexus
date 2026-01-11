import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Building2, User, DollarSign, MapPin } from 'lucide-react';

export interface ApplicantFormData {
  // Personal Information
  firstName: string;
  lastName: string;
  phone: string;
  dateOfBirth: string;
  nationality: string;
  
  // Address
  street: string;
  city: string;
  state: string;
  postalCode: string;
  country: string;
  
  // Company Information
  companyName: string;
  companyLEI: string;
  companyRegistration: string;
  companyTaxId: string;
  industry: string;
  jobTitle: string;
  department: string;
  
  // Financial Information
  annualRevenue: string;
  revenueCurrency: string;
  creditRating: string;
  creditRatingAgency: string;
}

interface SignupFormApplicantProps {
  formData: Partial<ApplicantFormData>;
  onChange: (data: Partial<ApplicantFormData>) => void;
  errors?: Record<string, string>;
}

export function SignupFormApplicant({ formData, onChange, errors = {} }: SignupFormApplicantProps) {
  const updateField = (field: keyof ApplicantFormData, value: string) => {
    onChange({ [field]: value });
  };

  return (
    <div className="space-y-6">
      {/* Personal Information */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <User className="h-5 w-5" />
          <h3 className="font-semibold">Personal Information</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="firstName">First Name</Label>
            <Input
              id="firstName"
              value={formData.firstName || ''}
              onChange={(e) => updateField('firstName', e.target.value)}
              className={errors.firstName ? 'border-red-500' : ''}
              placeholder="John"
            />
            {errors.firstName && (
              <p className="mt-1 text-sm text-red-400">{errors.firstName}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="lastName">Last Name</Label>
            <Input
              id="lastName"
              value={formData.lastName || ''}
              onChange={(e) => updateField('lastName', e.target.value)}
              className={errors.lastName ? 'border-red-500' : ''}
              placeholder="Smith"
            />
            {errors.lastName && (
              <p className="mt-1 text-sm text-red-400">{errors.lastName}</p>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="phone">Phone Number</Label>
            <Input
              id="phone"
              type="tel"
              value={formData.phone || ''}
              onChange={(e) => updateField('phone', e.target.value)}
              className={errors.phone ? 'border-red-500' : ''}
              placeholder="+1 (555) 123-4567"
            />
            {errors.phone && (
              <p className="mt-1 text-sm text-red-400">{errors.phone}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="dateOfBirth">Date of Birth</Label>
            <Input
              id="dateOfBirth"
              type="date"
              value={formData.dateOfBirth || ''}
              onChange={(e) => updateField('dateOfBirth', e.target.value)}
              className={errors.dateOfBirth ? 'border-red-500' : ''}
            />
            {errors.dateOfBirth && (
              <p className="mt-1 text-sm text-red-400">{errors.dateOfBirth}</p>
            )}
          </div>
        </div>
        
        <div>
          <Label htmlFor="nationality">Nationality</Label>
          <Input
            id="nationality"
            value={formData.nationality || ''}
            onChange={(e) => updateField('nationality', e.target.value)}
            className={errors.nationality ? 'border-red-500' : ''}
            placeholder="US"
          />
          {errors.nationality && (
            <p className="mt-1 text-sm text-red-400">{errors.nationality}</p>
          )}
        </div>
      </div>

      {/* Address */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <MapPin className="h-5 w-5" />
          <h3 className="font-semibold">Address</h3>
        </div>
        
        <div>
          <Label htmlFor="street">Street Address</Label>
          <Input
            id="street"
            value={formData.street || ''}
            onChange={(e) => updateField('street', e.target.value)}
            className={errors.street ? 'border-red-500' : ''}
            placeholder="123 Main St"
          />
          {errors.street && (
            <p className="mt-1 text-sm text-red-400">{errors.street}</p>
          )}
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="city">City</Label>
            <Input
              id="city"
              value={formData.city || ''}
              onChange={(e) => updateField('city', e.target.value)}
              className={errors.city ? 'border-red-500' : ''}
              placeholder="New York"
            />
            {errors.city && (
              <p className="mt-1 text-sm text-red-400">{errors.city}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="state">State/Province</Label>
            <Input
              id="state"
              value={formData.state || ''}
              onChange={(e) => updateField('state', e.target.value)}
              className={errors.state ? 'border-red-500' : ''}
              placeholder="NY"
            />
            {errors.state && (
              <p className="mt-1 text-sm text-red-400">{errors.state}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="postalCode">Postal Code</Label>
            <Input
              id="postalCode"
              value={formData.postalCode || ''}
              onChange={(e) => updateField('postalCode', e.target.value)}
              className={errors.postalCode ? 'border-red-500' : ''}
              placeholder="10001"
            />
            {errors.postalCode && (
              <p className="mt-1 text-sm text-red-400">{errors.postalCode}</p>
            )}
          </div>
        </div>
        
        <div>
          <Label htmlFor="country">Country</Label>
          <Input
            id="country"
            value={formData.country || ''}
            onChange={(e) => updateField('country', e.target.value)}
            className={errors.country ? 'border-red-500' : ''}
            placeholder="United States"
          />
          {errors.country && (
            <p className="mt-1 text-sm text-red-400">{errors.country}</p>
          )}
        </div>
      </div>

      {/* Company Information */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <Building2 className="h-5 w-5" />
          <h3 className="font-semibold">Company Information</h3>
        </div>
        
        <div>
          <Label htmlFor="companyName">Company Name</Label>
          <Input
            id="companyName"
            value={formData.companyName || ''}
            onChange={(e) => updateField('companyName', e.target.value)}
            className={errors.companyName ? 'border-red-500' : ''}
            placeholder="ACME Corporation"
          />
          {errors.companyName && (
            <p className="mt-1 text-sm text-red-400">{errors.companyName}</p>
          )}
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="companyLEI">Company LEI</Label>
            <Input
              id="companyLEI"
              value={formData.companyLEI || ''}
              onChange={(e) => updateField('companyLEI', e.target.value)}
              className={errors.companyLEI ? 'border-red-500' : ''}
              placeholder="5493000IBP32UQZ0KL24"
            />
            {errors.companyLEI && (
              <p className="mt-1 text-sm text-red-400">{errors.companyLEI}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="companyRegistration">Registration Number</Label>
            <Input
              id="companyRegistration"
              value={formData.companyRegistration || ''}
              onChange={(e) => updateField('companyRegistration', e.target.value)}
              className={errors.companyRegistration ? 'border-red-500' : ''}
              placeholder="12345678"
            />
            {errors.companyRegistration && (
              <p className="mt-1 text-sm text-red-400">{errors.companyRegistration}</p>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="companyTaxId">Tax ID / EIN</Label>
            <Input
              id="companyTaxId"
              value={formData.companyTaxId || ''}
              onChange={(e) => updateField('companyTaxId', e.target.value)}
              className={errors.companyTaxId ? 'border-red-500' : ''}
              placeholder="12-3456789"
            />
            {errors.companyTaxId && (
              <p className="mt-1 text-sm text-red-400">{errors.companyTaxId}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="industry">Industry</Label>
            <Input
              id="industry"
              value={formData.industry || ''}
              onChange={(e) => updateField('industry', e.target.value)}
              className={errors.industry ? 'border-red-500' : ''}
              placeholder="Technology"
            />
            {errors.industry && (
              <p className="mt-1 text-sm text-red-400">{errors.industry}</p>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="jobTitle">Job Title</Label>
            <Input
              id="jobTitle"
              value={formData.jobTitle || ''}
              onChange={(e) => updateField('jobTitle', e.target.value)}
              className={errors.jobTitle ? 'border-red-500' : ''}
              placeholder="CEO"
            />
            {errors.jobTitle && (
              <p className="mt-1 text-sm text-red-400">{errors.jobTitle}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="department">Department</Label>
            <Input
              id="department"
              value={formData.department || ''}
              onChange={(e) => updateField('department', e.target.value)}
              className={errors.department ? 'border-red-500' : ''}
              placeholder="Executive"
            />
            {errors.department && (
              <p className="mt-1 text-sm text-red-400">{errors.department}</p>
            )}
          </div>
        </div>
      </div>

      {/* Financial Information */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <DollarSign className="h-5 w-5" />
          <h3 className="font-semibold">Financial Information</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="annualRevenue">Annual Revenue</Label>
            <Input
              id="annualRevenue"
              type="number"
              value={formData.annualRevenue || ''}
              onChange={(e) => updateField('annualRevenue', e.target.value)}
              className={errors.annualRevenue ? 'border-red-500' : ''}
              placeholder="1000000"
            />
            {errors.annualRevenue && (
              <p className="mt-1 text-sm text-red-400">{errors.annualRevenue}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="revenueCurrency">Currency</Label>
            <Input
              id="revenueCurrency"
              value={formData.revenueCurrency || 'USD'}
              onChange={(e) => updateField('revenueCurrency', e.target.value)}
              className={errors.revenueCurrency ? 'border-red-500' : ''}
              placeholder="USD"
            />
            {errors.revenueCurrency && (
              <p className="mt-1 text-sm text-red-400">{errors.revenueCurrency}</p>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="creditRating">Credit Rating</Label>
            <Input
              id="creditRating"
              value={formData.creditRating || ''}
              onChange={(e) => updateField('creditRating', e.target.value)}
              className={errors.creditRating ? 'border-red-500' : ''}
              placeholder="AAA"
            />
            {errors.creditRating && (
              <p className="mt-1 text-sm text-red-400">{errors.creditRating}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="creditRatingAgency">Rating Agency</Label>
            <Input
              id="creditRatingAgency"
              value={formData.creditRatingAgency || ''}
              onChange={(e) => updateField('creditRatingAgency', e.target.value)}
              className={errors.creditRatingAgency ? 'border-red-500' : ''}
              placeholder="S&P"
            />
            {errors.creditRatingAgency && (
              <p className="mt-1 text-sm text-red-400">{errors.creditRatingAgency}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
