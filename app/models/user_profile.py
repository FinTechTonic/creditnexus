"""User profile data models for structured profile extraction."""

from typing import Optional, List, Dict, Any
from datetime import date
from pydantic import BaseModel, Field, EmailStr


class Address(BaseModel):
    """Address information."""
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State or province")
    postal_code: Optional[str] = Field(None, description="Postal or ZIP code")
    country: Optional[str] = Field(None, description="Country")
    full_address: Optional[str] = Field(None, description="Full address as single string")


class CompanyInfo(BaseModel):
    """Company or organization information."""
    name: Optional[str] = Field(None, description="Company name")
    legal_name: Optional[str] = Field(None, description="Legal entity name")
    registration_number: Optional[str] = Field(None, description="Company registration number")
    tax_id: Optional[str] = Field(None, description="Tax identification number")
    lei: Optional[str] = Field(None, description="Legal Entity Identifier (LEI)")
    industry: Optional[str] = Field(None, description="Industry sector")
    website: Optional[str] = Field(None, description="Company website")
    address: Optional[Address] = Field(None, description="Company address")


class FinancialInfo(BaseModel):
    """Financial information."""
    annual_revenue: Optional[float] = Field(None, description="Annual revenue")
    revenue_currency: Optional[str] = Field(None, description="Currency for revenue")
    assets_under_management: Optional[float] = Field(None, description="Assets under management")
    aum_currency: Optional[str] = Field(None, description="Currency for AUM")
    credit_rating: Optional[str] = Field(None, description="Credit rating")
    credit_rating_agency: Optional[str] = Field(None, description="Credit rating agency")


class ContactInfo(BaseModel):
    """Contact information."""
    phone: Optional[str] = Field(None, description="Phone number")
    mobile: Optional[str] = Field(None, description="Mobile phone number")
    fax: Optional[str] = Field(None, description="Fax number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    website: Optional[str] = Field(None, description="Personal website")


class ProfessionalInfo(BaseModel):
    """Professional information."""
    job_title: Optional[str] = Field(None, description="Job title or position")
    department: Optional[str] = Field(None, description="Department")
    years_of_experience: Optional[int] = Field(None, description="Years of professional experience")
    certifications: Optional[List[str]] = Field(None, description="Professional certifications")
    licenses: Optional[List[str]] = Field(None, description="Professional licenses")
    specializations: Optional[List[str]] = Field(None, description="Areas of specialization")


class UserProfileData(BaseModel):
    """Structured user profile data extracted from documents.
    
    This model represents the structured profile information that can be extracted
    from uploaded documents (business cards, resumes, company documents, etc.)
    and merged with form data during signup.
    """
    # Personal Information
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    middle_name: Optional[str] = Field(None, description="Middle name or initial")
    full_name: Optional[str] = Field(None, description="Full name as single string")
    date_of_birth: Optional[date] = Field(None, description="Date of birth (ISO 8601 format)")
    nationality: Optional[str] = Field(None, description="Nationality")
    
    # Contact Information
    contact: Optional[ContactInfo] = Field(None, description="Contact information")
    personal_address: Optional[Address] = Field(None, description="Personal address")
    
    # Professional Information
    professional: Optional[ProfessionalInfo] = Field(None, description="Professional information")
    company: Optional[CompanyInfo] = Field(None, description="Company or organization information")
    
    # Financial Information (for applicants, companies)
    financial: Optional[FinancialInfo] = Field(None, description="Financial information")
    
    # Additional Metadata
    extracted_from: Optional[str] = Field(None, description="Source document filename")
    extraction_confidence: Optional[float] = Field(None, description="Confidence score (0.0-1.0)")
    extraction_date: Optional[str] = Field(None, description="Date of extraction (ISO 8601)")
    raw_extracted_text: Optional[str] = Field(None, description="Raw text extracted from document")
    
    # Role-specific fields
    role_specific_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional role-specific profile data"
    )
