/**
 * Document CDM Data Selector Component
 * 
 * Allows users to search, filter, and select documents from the library
 * to use their CDM data for template generation.
 */

import { useState, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { 
  Search, 
  FileText, 
  AlertCircle,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { SkeletonList } from '@/components/ui/loading-states';
import { EmptyState } from '@/components/ui/skeleton';
import type { CreditAgreementData } from '@/context/FDC3Context';
import { CdmPreviewCard } from './CdmPreviewCard';

interface DocumentSummary {
  id: number;
  title: string;
  borrower_name: string | null;
  borrower_lei: string | null;
  governing_law: string | null;
  total_commitment: number | null;
  currency: string | null;
  agreement_date: string | null;
  sustainability_linked: boolean;
  created_at: string;
  updated_at: string;
  workflow_state?: string | null;
}

interface DocumentCdmSelectorProps {
  onCdmDataSelect: (cdmData: CreditAgreementData, documentId: number) => void;
  onPreview?: (cdmData: CreditAgreementData, documentId: number) => void;
  className?: string;
}

interface DocumentWithCdm extends DocumentSummary {
  cdmData?: CreditAgreementData;
  completenessScore?: number;
}

export function DocumentCdmSelector({
  onCdmDataSelect,
  onPreview,
  className = '',
}: DocumentCdmSelectorProps) {
  const [documents, setDocuments] = useState<DocumentWithCdm[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // const [isSelecting, setIsSelecting] = useState(false); // Unused - kept for future use
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Calculate CDM data completeness score
  const calculateCompleteness = useCallback((cdmData: CreditAgreementData | null | undefined): number => {
    if (!cdmData) return 0;
    
    let score = 0;
    let maxScore = 0;
    
    // Parties (30 points)
    maxScore += 30;
    if (cdmData.parties && Array.isArray(cdmData.parties) && cdmData.parties.length > 0) {
      score += 30;
    }
    
    // Facilities (30 points)
    maxScore += 30;
    if (cdmData.facilities && Array.isArray(cdmData.facilities) && cdmData.facilities.length > 0) {
      score += 30;
    }
    
    // Agreement date (10 points)
    maxScore += 10;
    if (cdmData.agreement_date) {
      score += 10;
    }
    
    // Governing law (10 points)
    maxScore += 10;
    if (cdmData.governing_law) {
      score += 10;
    }
    
    // Deal ID (10 points)
    maxScore += 10;
    if (cdmData.deal_id) {
      score += 10;
    }
    
    // Loan identification number (10 points)
    maxScore += 10;
    if (cdmData.loan_identification_number) {
      score += 10;
    }
    
    return Math.round((score / maxScore) * 100);
  }, []);

  // Debounce search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Fetch documents
  useEffect(() => {
    fetchDocuments();
  }, [debouncedSearch]);

  const fetchDocuments = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        limit: '50',
        offset: '0',
      });
      
      if (debouncedSearch.trim()) {
        params.append('search', debouncedSearch.trim());
      }
      
      const response = await fetchWithAuth(`/api/documents?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }
      
      const data = await response.json();
      const docs = data.documents || [];
      
      // Filter to only show documents that have CDM data and calculate completeness
      const docsWithCdm = await Promise.all(
        docs.map(async (doc: DocumentSummary) => {
          try {
            const cdmResponse = await fetchWithAuth(`/api/documents/${doc.id}?include_cdm_data=true`);
            if (cdmResponse.ok) {
              const responseData = await cdmResponse.json();
              if (responseData.cdm_data) {
                const cdmData = responseData.cdm_data as CreditAgreementData;
                const completenessScore = calculateCompleteness(cdmData);
                return {
                  ...doc,
                  cdmData,
                  completenessScore,
                } as DocumentWithCdm;
              }
            }
            return null;
          } catch {
            return null;
          }
        })
      );
      
      setDocuments(docsWithCdm.filter((doc: DocumentWithCdm | null) => doc !== null) as DocumentWithCdm[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
      console.error('Error fetching documents:', err);
    } finally {
      setIsLoading(false);
    }
  }, [debouncedSearch]);

  const handleDocumentSelect = useCallback(async (documentId: number) => {
    try {
      // setIsSelecting(true); // Unused
      setError(null);
      
      const response = await fetchWithAuth(`/api/documents/${documentId}?include_cdm_data=true`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch document CDM data');
      }
      
      const data = await response.json();
      
      if (!data.cdm_data) {
        throw new Error('This document does not have CDM data');
      }
      
      // Ensure parties have 'id' field
      const cdmData = data.cdm_data as CreditAgreementData;
      if (cdmData.parties) {
        cdmData.parties = cdmData.parties.map((party, idx) => ({
          ...party,
          id: party.id || `party_${idx}`,
        }));
      }
      
      setSelectedDocumentId(documentId);
      onCdmDataSelect(cdmData, documentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select document');
      console.error('Error selecting document:', err);
    } finally {
      // setIsSelecting(false); // Unused
    }
  }, [onCdmDataSelect]);

  // Helper functions - unused but kept for future use
  // const formatCurrency = (amount: number | null, currency: string | null): string => {
  //   if (!amount) return 'N/A';
  //   const currencySymbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : currency || '';
  //   return `${currencySymbol}${amount.toLocaleString()}`;
  // };

  // const formatDate = (dateString: string | null): string => {
  //   if (!dateString) return 'N/A';
  //   try {
  //     return new Date(dateString).toLocaleDateString();
  //   } catch {
  //     return dateString;
  //   }
  // };

  // const getStatusBadge = (state: string | null | undefined) => {
  //   if (!state) return null;
  //   const stateColors: Record<string, string> = {
  //     'approved': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  //     'published': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  //     'under_review': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  //     'draft': 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  //   };
  //   return stateColors[state] || 'bg-slate-500/20 text-slate-400 border-slate-500/30';
  // };

  // const getCompletenessColor = (score: number): string => {
  //   if (score >= 80) return 'text-emerald-400 bg-emerald-500/20 border-emerald-500/30';
  //   if (score >= 50) return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30';
  //   return 'text-red-400 bg-red-500/20 border-red-500/30';
  // };

  const handlePreview = useCallback((doc: DocumentWithCdm) => {
    if (doc.cdmData && onPreview) {
      onPreview(doc.cdmData, doc.id);
    }
  }, [onPreview]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          type="text"
          placeholder="Search documents by title or borrower name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10 bg-slate-900/50 border-slate-600 text-slate-100 focus:ring-emerald-500/20 focus:border-emerald-500"
        />
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <SkeletonList count={5} />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-12 w-12 text-slate-500" />}
          title="No documents found"
          description={
            debouncedSearch
              ? "No documents with CDM data match your search. Try a different search term."
              : "No documents with CDM data found. Extract some documents first in the Document Parser."
          }
        />
      ) : (
        <div className="space-y-4">
          {/* Grid Container with Horizontal Scroll */}
          <div className="relative">
            {/* Scrollable Grid: 2 rows × 3 columns (6 visible cards) */}
            <div className="overflow-x-auto overflow-y-hidden pb-4 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
              <div 
                className="inline-grid gap-4"
                style={{ 
                  gridTemplateColumns: 'repeat(3, minmax(280px, 320px))',
                  gridTemplateRows: 'repeat(2, auto)',
                  gridAutoFlow: 'column',
                  minWidth: 'max-content'
                }}
              >
                {documents.map((doc) => {
                  const isSelected = selectedDocumentId === doc.id;
                  
                  return (
                    <CdmPreviewCard
                      key={doc.id}
                      documentId={doc.id}
                      title={doc.title}
                      borrowerName={doc.borrower_name}
                      borrowerLei={doc.borrower_lei}
                      governingLaw={doc.governing_law}
                      totalCommitment={doc.total_commitment}
                      currency={doc.currency}
                      agreementDate={doc.agreement_date}
                      completenessScore={doc.completenessScore}
                      isSelected={isSelected}
                      onSelect={handleDocumentSelect}
                      onPreview={onPreview ? () => handlePreview(doc) : undefined}
                    />
                  );
                })}
              </div>
            </div>
            
            {/* Scroll Indicators */}
            {documents.length > 6 && (
              <div className="flex items-center justify-center gap-2 mt-2 text-xs text-gray-400">
                <ChevronLeft className="w-4 h-4" />
                <span>Scroll horizontally to see more documents ({documents.length} total)</span>
                <ChevronRight className="w-4 h-4" />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
