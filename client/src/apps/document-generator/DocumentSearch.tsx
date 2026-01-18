/**
 * Document Search Component
 * 
 * Search input with results display and document selection.
 * Uses ChromaDB similarity search to find similar documents based on query or CDM data.
 */

import React, { useState, useCallback } from 'react';
import { Search, Loader2, AlertCircle, CheckCircle2, FileText, Building2, Calendar, DollarSign, Scale, X, ExternalLink } from 'lucide-react';
import { fetchWithAuth } from '../../context/AuthContext';

interface DocumentResult {
  document_id: number;
  similarity_score: number;
  distance: number;
  document: {
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
  };
  cdm_data?: Record<string, unknown> | null;
  workflow?: {
    state: string;
    priority: string;
  } | null;
  latest_version?: {
    id: number;
    version_number: number;
    extracted_data: Record<string, unknown>;
  } | null;
}

interface SearchResponse {
  status: string;
  query: string;
  results_count: number;
  documents: DocumentResult[];
}

interface DocumentSearchProps {
  onDocumentSelect?: (document: DocumentResult) => void;
  onCdmDataSelect?: (cdmData: Record<string, unknown>) => void;
  initialQuery?: string;
  topK?: number;
  className?: string;
  theme?: 'light' | 'dark';
  onError?: (error: string) => void;
}

export function DocumentSearch({
  onDocumentSelect,
  onCdmDataSelect,
  initialQuery = '',
  topK = 5,
  className = '',
  theme = 'light',
}: DocumentSearchProps) {
  const isDark = theme === 'dark';
  const [query, setQuery] = useState(initialQuery);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<DocumentResult[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<DocumentResult | null>(null);
  const [showCdmData, setShowCdmData] = useState(false);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }

    try {
      setIsSearching(true);
      setError(null);
      setSearchResults([]);
      setSelectedDocument(null);
      setShowCdmData(false);

      const response = await fetchWithAuth('/api/documents/retrieve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          top_k: topK,
          extract_cdm: true,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail?.message || errorData.detail || 'Search failed';
        throw new Error(errorMessage);
      }

      const data: SearchResponse = await response.json();
      setSearchResults(data.documents || []);

      if (data.documents.length === 0) {
        setError('No similar documents found');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Search failed';
      setError(errorMessage);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [query, topK]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  }, [handleSearch]);

  const handleSelectDocument = useCallback((document: DocumentResult) => {
    setSelectedDocument(document);
    setShowCdmData(false);

    if (onDocumentSelect) {
      onDocumentSelect(document);
    }

    if (onCdmDataSelect && document.cdm_data) {
      onCdmDataSelect(document.cdm_data);
    }
  }, [onDocumentSelect, onCdmDataSelect]);

  const formatCurrency = (amount: number | null, currency: string | null): string => {
    if (!amount) return 'N/A';
    const currencySymbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : currency || '';
    return `${currencySymbol}${amount.toLocaleString()}`;
  };

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return dateString;
    }
  };

  return (
    <div className={`${isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-gray-200'} rounded-lg border p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <Search className={`w-5 h-5 ${isDark ? 'text-slate-400' : 'text-gray-600'}`} />
        <h3 className={`text-lg font-semibold ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>Document Search</h3>
      </div>

      {/* Search Input */}
      <div className="space-y-3 mb-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Search by text or paste CDM data (JSON)..."
            className={`flex-1 px-4 py-2 border ${isDark ? 'border-slate-600 bg-slate-900/50 text-slate-100 focus:ring-emerald-500/20 focus:border-emerald-500' : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'} rounded-lg focus:ring-2 disabled:opacity-50`}
            disabled={isSearching}
          />
          <button
            onClick={handleSearch}
            disabled={isSearching || !query.trim()}
            className={`px-6 py-2 ${isDark ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2`}
          >
            {isSearching ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Search
              </>
            )}
          </button>
        </div>

        <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>
          Enter search text or paste CDM data as JSON to find similar documents
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className={`mb-4 ${isDark ? 'bg-red-500/10 border-red-500/20' : 'bg-red-50 border-red-200'} rounded-lg p-3`}>
          <div className="flex items-center gap-2">
            <AlertCircle className={`w-4 h-4 ${isDark ? 'text-red-400' : 'text-red-600'}`} />
            <p className={`text-sm ${isDark ? 'text-red-400' : 'text-red-700'}`}>{error}</p>
          </div>
        </div>
      )}

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className={`text-sm font-medium ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>
              Found {searchResults.length} similar document{searchResults.length > 1 ? 's' : ''}
            </h4>
            <button
              onClick={() => {
                setSearchResults([]);
                setSelectedDocument(null);
                setShowCdmData(false);
              }}
              className={`text-xs ${isDark ? 'text-slate-400 hover:text-slate-200' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Clear
            </button>
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {searchResults.map((doc) => (
              <div
                key={doc.document_id}
                className={`border rounded-lg p-4 cursor-pointer transition-all ${
                  selectedDocument?.document_id === doc.document_id
                    ? (isDark ? 'border-emerald-500 bg-emerald-500/10' : 'border-blue-500 bg-blue-50')
                    : (isDark ? 'border-slate-700 hover:border-slate-600 hover:bg-slate-800/50' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50')
                }`}
                onClick={() => handleSelectDocument(doc)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className={`w-4 h-4 ${isDark ? 'text-slate-400' : 'text-gray-600'}`} />
                      <h5 className={`font-medium ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>{doc.document.title}</h5>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs px-2 py-0.5 rounded ${isDark ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-100 text-blue-800'}`}>
                        {(doc.similarity_score * 100).toFixed(1)}% match
                      </span>
                      {doc.document.sustainability_linked && (
                        <span className={`text-xs px-2 py-0.5 rounded flex items-center gap-1 ${isDark ? 'bg-emerald-500/20 text-emerald-400' : 'bg-green-100 text-green-800'}`}>
                          <Scale className="w-3 h-3" />
                          ESG
                        </span>
                      )}
                    </div>
                  </div>
                  {selectedDocument?.document_id === doc.document_id && (
                    <CheckCircle2 className={`w-5 h-5 ${isDark ? 'text-emerald-400' : 'text-blue-600'}`} />
                  )}
                </div>

                <div className={`grid grid-cols-2 gap-2 text-xs ${isDark ? 'text-slate-400' : 'text-gray-600'}`}>
                  {doc.document.borrower_name && (
                    <div className="flex items-center gap-1">
                      <Building2 className="w-3 h-3" />
                      <span>{doc.document.borrower_name}</span>
                    </div>
                  )}
                  {doc.document.agreement_date && (
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      <span>{formatDate(doc.document.agreement_date)}</span>
                    </div>
                  )}
                  {doc.document.total_commitment && (
                    <div className="flex items-center gap-1">
                      <DollarSign className="w-3 h-3" />
                      <span>{formatCurrency(doc.document.total_commitment, doc.document.currency)}</span>
                    </div>
                  )}
                  {doc.document.governing_law && (
                    <div className="flex items-center gap-1">
                      <Scale className="w-3 h-3" />
                      <span>{doc.document.governing_law}</span>
                    </div>
                  )}
                </div>

                {doc.workflow && (
                  <div className="mt-2 text-xs">
                    <span className={`px-2 py-0.5 rounded ${
                      doc.workflow.state === 'approved' 
                        ? (isDark ? 'bg-emerald-500/20 text-emerald-400' : 'bg-green-100 text-green-800')
                        : doc.workflow.state === 'published'
                        ? (isDark ? 'bg-blue-500/20 text-blue-400' : 'bg-blue-100 text-blue-800')
                        : doc.workflow.state === 'under_review'
                        ? (isDark ? 'bg-yellow-500/20 text-yellow-400' : 'bg-yellow-100 text-yellow-800')
                        : (isDark ? 'bg-slate-700 text-slate-300' : 'bg-gray-100 text-gray-800')
                    }`}>
                      {doc.workflow.state}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Selected Document Details */}
      {selectedDocument && (
        <div className="mt-4 space-y-3">
          <div className={`${isDark ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-blue-50 border-blue-200'} rounded-lg p-3`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className={`w-4 h-4 ${isDark ? 'text-emerald-400' : 'text-blue-600'}`} />
                <span className={`text-sm font-medium ${isDark ? 'text-emerald-300' : 'text-blue-800'}`}>Selected Document</span>
              </div>
              <button
                onClick={() => {
                  setSelectedDocument(null);
                  setShowCdmData(false);
                }}
                className={`${isDark ? 'text-emerald-400 hover:text-emerald-300' : 'text-blue-600 hover:text-blue-800'}`}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-blue-700'}`}>
              {selectedDocument.document.title} • Similarity: {(selectedDocument.similarity_score * 100).toFixed(1)}%
            </p>
          </div>

          {/* CDM Data Toggle */}
          {selectedDocument.cdm_data && (
            <div>
              <button
                onClick={() => setShowCdmData(!showCdmData)}
                className={`w-full px-4 py-2 ${isDark ? 'bg-slate-700 text-slate-200 hover:bg-slate-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'} rounded-lg font-medium text-sm transition-colors flex items-center justify-between`}
              >
                <span>View CDM Data</span>
                <ExternalLink className={`w-4 h-4 transition-transform ${showCdmData ? 'rotate-90' : ''}`} />
              </button>

              {showCdmData && (
                <div className={`mt-2 ${isDark ? 'bg-slate-900/50' : 'bg-gray-50'} rounded-lg p-3 max-h-64 overflow-y-auto`}>
                  <pre className={`text-xs ${isDark ? 'text-slate-300' : 'text-gray-700'} whitespace-pre-wrap`}>
                    {JSON.stringify(selectedDocument.cdm_data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Use CDM Data Button */}
          {selectedDocument.cdm_data && onCdmDataSelect && (
            <button
              onClick={() => {
                if (selectedDocument.cdm_data) {
                  onCdmDataSelect(selectedDocument.cdm_data);
                }
              }}
              className={`w-full px-4 py-2 ${isDark ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-lg font-medium text-sm transition-colors`}
            >
              Use This CDM Data
            </button>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isSearching && searchResults.length === 0 && !error && query && (
        <div className={`text-center py-8 ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>
          <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No results found. Try a different search query.</p>
        </div>
      )}
    </div>
  );
}















