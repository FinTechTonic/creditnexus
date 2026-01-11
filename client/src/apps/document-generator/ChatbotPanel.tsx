/**
 * Chatbot Panel Component
 * 
 * Provides AI-powered assistance for LMA template generation:
 * - Interactive chat interface
 * - Template suggestions based on CDM data
 * - Field filling assistance
 * - CDM data updates from chatbot
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import {
  MessageSquare,
  Send,
  Loader2,
  AlertCircle,
  Sparkles,
  FileText,
  CheckCircle2,
  ChevronRight,
  X,
  Building2,
  Calendar,
  Clock,
  Folder,
  ListChecks,
  Info,
  Search,
  ChevronDown,
} from 'lucide-react';
import { fetchWithAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/button';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  suggestions?: TemplateSuggestion[];
  fieldGuidance?: FieldGuidance;
}

interface TemplateSuggestion {
  template_id: number;
  template_code: string;
  name: string;
  category: string;
  confidence?: number;
  reasoning?: string;
}

interface FieldGuidance {
  missing_fields: string[];
  suggestions: Record<string, {
    suggested_value?: unknown;
    question?: string;
    example?: string;
  }>;
  questions: string[];
  guidance: string;
}

interface Deal {
  id: number;
  deal_id: string;
  status: string;
  deal_type: string | null;
  deal_data: Record<string, unknown> | null;
  created_at: string;
}

interface DealDocument {
  id: number;
  title: string;
  filename: string;
  created_at: string;
}

interface TemplateRecommendation {
  template_id: number;
  name: string;
  category: string;
  reason: string;
  priority?: 'high' | 'medium' | 'low';
}

interface TemplateRecommendations {
  missing_required: TemplateRecommendation[];
  optional_not_generated: TemplateRecommendation[];
  generated_templates: TemplateRecommendation[];
  completion_status: {
    required_generated: number;
    required_total: number;
    completion_percentage: number;
  };
}

interface ChatbotPanelProps {
  cdmData?: Record<string, unknown>;
  onCdmDataUpdate?: (updatedCdmData: Record<string, unknown>) => void;
  onTemplateSelect?: (templateId: number) => void;
  onClose?: () => void;
  className?: string;
  dealId?: number | null;
  onDealIdChange?: (dealId: number | null) => void;
}

export function ChatbotPanel({
  cdmData = {},
  onCdmDataUpdate,
  onTemplateSelect,
  onClose,
  className = '',
  dealId: propDealId = null,
  onDealIdChange,
}: ChatbotPanelProps) {
  const { dealId: urlDealId } = useParams<{ dealId?: string }>();
  const location = useLocation();
  
  // Auto-select deal from URL if on deal detail page
  const [internalDealId, setInternalDealId] = useState<number | null>(() => {
    if (propDealId) return propDealId;
    if (urlDealId) return parseInt(urlDealId, 10);
    return null;
  });
  
  const dealId = propDealId || internalDealId;
  
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your AI assistant for LMA template generation. I can help you:\n\n• Suggest templates based on your CDM data\n• Fill missing required fields\n• Answer questions about templates and CDM structure\n\nHow can I help you today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [templateSuggestions, setTemplateSuggestions] = useState<TemplateSuggestion[]>([]);
  const [deal, setDeal] = useState<Deal | null>(null);
  const [dealDocuments, setDealDocuments] = useState<DealDocument[]>([]);
  const [templateRecommendations, setTemplateRecommendations] = useState<TemplateRecommendations | null>(null);
  const [loadingDealContext, setLoadingDealContext] = useState(false);
  const [showDealContext, setShowDealContext] = useState(true);
  const [availableDeals, setAvailableDeals] = useState<Deal[]>([]);
  const [loadingDeals, setLoadingDeals] = useState(false);
  const [showDealSelector, setShowDealSelector] = useState(false);
  const [dealSearchQuery, setDealSearchQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Auto-select deal from URL if on deal detail page
  useEffect(() => {
    if (urlDealId && !propDealId) {
      const parsedId = parseInt(urlDealId, 10);
      if (!isNaN(parsedId) && parsedId !== internalDealId) {
        setInternalDealId(parsedId);
        if (onDealIdChange) {
          onDealIdChange(parsedId);
        }
      }
    }
  }, [urlDealId, propDealId, internalDealId, onDealIdChange]);

  // Load deal context when dealId is provided
  useEffect(() => {
    if (dealId) {
      loadDealContext();
    } else {
      // Clear deal context when no deal selected
      setDeal(null);
      setDealDocuments([]);
      setTemplateRecommendations(null);
    }
  }, [dealId]);

  // Load available deals for selection
  useEffect(() => {
    if (showDealSelector) {
      loadAvailableDeals();
    }
  }, [showDealSelector]);

  const loadDealContext = useCallback(async () => {
    if (!dealId) return;

    setLoadingDealContext(true);
    try {
      // Load deal details
      const dealResponse = await fetchWithAuth(`/api/deals/${dealId}`);
      if (dealResponse.ok) {
        const dealData = await dealResponse.json();
        setDeal(dealData.deal);
        setDealDocuments(dealData.documents || []);
      }

      // Load template recommendations
      try {
        const recResponse = await fetchWithAuth(`/api/deals/${dealId}/template-recommendations`);
        if (recResponse.ok) {
          const recData = await recResponse.json();
          if (recData.status === 'success' && recData.recommendations) {
            setTemplateRecommendations(recData.recommendations);
          }
        }
      } catch (err) {
        console.warn('Failed to load template recommendations:', err);
      }
    } catch (err) {
      console.error('Failed to load deal context:', err);
    } finally {
      setLoadingDealContext(false);
    }
  }, [dealId]);

  const loadAvailableDeals = useCallback(async () => {
    setLoadingDeals(true);
    try {
      const params = new URLSearchParams();
      params.append('limit', '20');
      if (dealSearchQuery.trim()) {
        params.append('search', dealSearchQuery.trim());
      }
      
      const response = await fetchWithAuth(`/api/deals?${params.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setAvailableDeals(data.deals || []);
      }
    } catch (err) {
      console.error('Failed to load deals:', err);
    } finally {
      setLoadingDeals(false);
    }
  }, [dealSearchQuery]);

  const handleSelectDeal = useCallback((selectedDealId: number) => {
    setInternalDealId(selectedDealId);
    setShowDealSelector(false);
    if (onDealIdChange) {
      onDealIdChange(selectedDealId);
    }
  }, [onDealIdChange]);

  const handleClearDeal = useCallback(() => {
    setInternalDealId(null);
    setDeal(null);
    setDealDocuments([]);
    setTemplateRecommendations(null);
    if (onDealIdChange) {
      onDealIdChange(null);
    }
  }, [onDealIdChange]);

  const addMessage = useCallback((role: 'user' | 'assistant', content: string, extras?: {
    suggestions?: TemplateSuggestion[];
    fieldGuidance?: FieldGuidance;
  }) => {
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
      ...extras,
    };
    setMessages((prev) => [...prev, newMessage]);
    return newMessage;
  }, []);

  const handleSendMessage = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setError(null);
    setIsLoading(true);

    // Add user message
    addMessage('user', userMessage);

    try {
      // Call chatbot chat endpoint
      const response = await fetchWithAuth('/api/chatbot/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          cdm_context: Object.keys(cdmData).length > 0 ? cdmData : undefined,
          deal_id: dealId || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to get response' }));
        throw new Error(errorData.detail?.message || errorData.message || 'Chat request failed');
      }

      const data = await response.json();

      if (data.status === 'success') {
        const reply = data.reply || 'I apologize, but I couldn\'t generate a response.';
        
        // Check if response includes template suggestions
        let suggestions: TemplateSuggestion[] | undefined;
        if (data.template_suggestions && data.template_suggestions.length > 0) {
          suggestions = data.template_suggestions;
          setTemplateSuggestions(suggestions);
          setShowSuggestions(true);
        }

        // Check if response includes field guidance
        let fieldGuidance: FieldGuidance | undefined;
        if (data.field_guidance) {
          fieldGuidance = data.field_guidance;
        }

        addMessage('assistant', reply, {
          suggestions,
          fieldGuidance,
        });
      } else {
        throw new Error(data.message || 'Chat request failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);
      addMessage('assistant', `I apologize, but I encountered an error: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, cdmData, addMessage]);

  const handleSuggestTemplates = useCallback(async () => {
    if (Object.keys(cdmData).length === 0) {
      setError('Please provide CDM data to get template suggestions');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchWithAuth('/api/chatbot/suggest-templates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cdm_data: cdmData,
          deal_id: dealId || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to get suggestions' }));
        throw new Error(errorData.detail?.message || errorData.message || 'Template suggestion failed');
      }

      const data = await response.json();

      if (data.status === 'success' && data.suggestions) {
        const suggestions: TemplateSuggestion[] = data.suggestions.map((s: any) => ({
          template_id: s.template_id,
          template_code: s.template_code || s.code,
          name: s.name || s.template_name,
          category: s.category,
          confidence: s.confidence,
          reasoning: s.reasoning,
        }));

        setTemplateSuggestions(suggestions);
        setShowSuggestions(true);

        const reasoning = data.reasoning || 'Based on your CDM data, here are some template suggestions:';
        addMessage('assistant', reasoning, { suggestions });
      } else {
        throw new Error(data.message || 'No template suggestions available');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get template suggestions';
      setError(errorMessage);
      addMessage('assistant', `I couldn't generate template suggestions: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  }, [cdmData, addMessage]);

  const handleFillFields = useCallback(async (requiredFields: string[]) => {
    if (requiredFields.length === 0) {
      setError('No required fields specified');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchWithAuth('/api/chatbot/fill-fields', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cdm_data: cdmData,
          required_fields: requiredFields,
          conversation_context: 'User is filling missing fields in CDM data for template generation',
          deal_id: dealId || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to get field guidance' }));
        throw new Error(errorData.detail?.message || errorData.message || 'Field filling failed');
      }

      const data = await response.json();

      if (data.status === 'success') {
        const fieldGuidance: FieldGuidance = {
          missing_fields: data.missing_fields || [],
          suggestions: data.suggestions || {},
          questions: data.questions || [],
          guidance: data.guidance || '',
        };

        if (data.all_fields_present && data.filled_data) {
          // All fields are present, update CDM data
          if (onCdmDataUpdate) {
            onCdmDataUpdate(data.filled_data);
          }
          addMessage('assistant', 'Great! All required fields are now filled. Your CDM data has been updated.', {
            fieldGuidance,
          });
        } else {
          addMessage('assistant', data.guidance || 'Here\'s guidance on filling the missing fields:', {
            fieldGuidance,
          });
        }
      } else {
        throw new Error(data.message || 'Field filling failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get field guidance';
      setError(errorMessage);
      addMessage('assistant', `I couldn't provide field guidance: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  }, [cdmData, onCdmDataUpdate, addMessage]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const handleSelectTemplate = useCallback((templateId: number) => {
    if (onTemplateSelect) {
      onTemplateSelect(templateId);
    }
    setShowSuggestions(false);
  }, [onTemplateSelect]);

  const formatTimestamp = (date: Date): string => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`flex h-full bg-slate-800 ${className}`}>
      {/* Deal Context Sidebar */}
      {dealId && deal && showDealContext && (
        <div className="w-80 border-r border-slate-700 flex flex-col bg-slate-900/50">
          <div className="p-4 border-b border-slate-700 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Info className="w-4 h-4" />
              Deal Context
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowDealContext(false)}
              className="h-6 w-6 p-0 text-slate-400 hover:text-slate-100"
            >
              <X className="w-3 h-3" />
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Deal Info */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Building2 className="w-4 h-4 text-slate-400" />
                <span className="font-medium">{deal.deal_id}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Clock className="w-3 h-3" />
                <span>Status: {deal.status}</span>
              </div>
              {deal.deal_type && (
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <FileText className="w-3 h-3" />
                  <span>Type: {deal.deal_type}</span>
                </div>
              )}
            </div>

            {/* Attached Documents */}
            {dealDocuments.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                  <Folder className="w-3 h-3" />
                  <span>Documents ({dealDocuments.length})</span>
                </div>
                <div className="space-y-1">
                  {dealDocuments.slice(0, 5).map((doc) => (
                    <div
                      key={doc.id}
                      className="text-xs text-slate-400 p-2 bg-slate-800 rounded border border-slate-700"
                    >
                      {doc.title || doc.filename}
                    </div>
                  ))}
                  {dealDocuments.length > 5 && (
                    <div className="text-xs text-slate-500 text-center">
                      +{dealDocuments.length - 5} more
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Template Recommendations */}
            {templateRecommendations && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                  <ListChecks className="w-3 h-3" />
                  <span>Template Recommendations</span>
                </div>
                
                {/* Completion Status */}
                {templateRecommendations.completion_status && (
                  <div className="p-2 bg-slate-800 rounded border border-slate-700">
                    <div className="text-xs text-slate-400 mb-1">Completion</div>
                    <div className="text-sm font-medium text-slate-200">
                      {templateRecommendations.completion_status.required_generated}/
                      {templateRecommendations.completion_status.required_total} required
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-1.5 mt-1">
                      <div
                        className="bg-emerald-500 h-1.5 rounded-full"
                        style={{
                          width: `${templateRecommendations.completion_status.completion_percentage}%`,
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Missing Required Templates */}
                {templateRecommendations.missing_required.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs text-yellow-400 font-medium">
                      Missing Required ({templateRecommendations.missing_required.length})
                    </div>
                    {templateRecommendations.missing_required.slice(0, 3).map((rec) => (
                      <button
                        key={rec.template_id}
                        onClick={() => onTemplateSelect?.(rec.template_id)}
                        className="w-full text-left text-xs p-2 bg-yellow-500/10 border border-yellow-500/30 rounded hover:bg-yellow-500/20 transition-colors"
                      >
                        <div className="font-medium text-slate-200">{rec.name}</div>
                        <div className="text-slate-400 mt-0.5">{rec.category}</div>
                        {rec.reason && (
                          <div className="text-slate-500 mt-1 text-[10px]">{rec.reason}</div>
                        )}
                      </button>
                    ))}
                  </div>
                )}

                {/* Optional Templates */}
                {templateRecommendations.optional_not_generated.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs text-slate-400 font-medium">
                      Optional ({templateRecommendations.optional_not_generated.length})
                    </div>
                    {templateRecommendations.optional_not_generated.slice(0, 2).map((rec) => (
                      <button
                        key={rec.template_id}
                        onClick={() => onTemplateSelect?.(rec.template_id)}
                        className="w-full text-left text-xs p-2 bg-slate-800 border border-slate-700 rounded hover:bg-slate-700 transition-colors"
                      >
                        <div className="font-medium text-slate-300">{rec.name}</div>
                        <div className="text-slate-500 mt-0.5">{rec.category}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {loadingDealContext && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <div className={`flex flex-col h-full flex-1 ${dealId && deal && !showDealContext ? '' : ''}`}>
        {/* Header */}
        <div className="border-b border-slate-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-semibold text-slate-100">AI Assistant</h2>
              {dealId && deal && !showDealContext && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowDealContext(true)}
                  className="text-xs text-slate-400 hover:text-slate-100 ml-2"
                >
                  <Info className="w-3 h-3 mr-1" />
                  Show Deal Context
                </Button>
              )}
              {!dealId && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDealSelector(true)}
                  className="text-xs border-slate-600 text-slate-300 hover:bg-slate-700 ml-2"
                >
                  <Search className="w-3 h-3 mr-1" />
                  Select Deal
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleSuggestTemplates}
                disabled={isLoading || Object.keys(cdmData).length === 0}
                title="Get template suggestions"
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                <FileText className="w-4 h-4 mr-1" />
                Suggest Templates
              </Button>
              {onClose && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onClose}
                  className="text-slate-400 hover:text-slate-100"
                  aria-label="Close chatbot"
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Get help with template selection, field filling, and CDM structure
            {dealId && deal && ` • Context: ${deal.deal_id}`}
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-700 text-slate-100'
                }`}
              >
                <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                <div
                  className={`text-xs mt-1 ${
                    message.role === 'user' ? 'text-emerald-100' : 'text-slate-400'
                  }`}
                >
                  {formatTimestamp(message.timestamp)}
                </div>

                {/* Template Suggestions */}
                {message.suggestions && message.suggestions.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-600">
                    <div className="text-xs font-semibold mb-2 text-slate-200">Template Suggestions:</div>
                    <div className="space-y-2">
                      {message.suggestions.map((suggestion) => (
                        <button
                          key={suggestion.template_id}
                          onClick={() => handleSelectTemplate(suggestion.template_id)}
                          className="w-full text-left p-2 bg-slate-800 rounded border border-slate-600 hover:border-emerald-500 hover:bg-emerald-500/10 transition-colors"
                        >
                          <div className="font-medium text-sm text-slate-100">{suggestion.name}</div>
                          <div className="text-xs text-slate-400 mt-1">
                            {suggestion.category} • {suggestion.template_code}
                          </div>
                          {suggestion.reasoning && (
                            <div className="text-xs text-slate-300 mt-1">{suggestion.reasoning}</div>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Field Guidance */}
                {message.fieldGuidance && (
                  <div className="mt-3 pt-3 border-t border-slate-600">
                    <div className="text-xs font-semibold mb-2 text-slate-200">Field Guidance:</div>
                    {message.fieldGuidance.missing_fields.length > 0 && (
                      <div className="mb-2">
                        <div className="text-xs text-yellow-400 font-medium">
                          Missing Fields: {message.fieldGuidance.missing_fields.join(', ')}
                        </div>
                      </div>
                    )}
                    {message.fieldGuidance.questions.length > 0 && (
                      <div className="mb-2">
                        <div className="text-xs font-medium mb-1 text-slate-200">Questions:</div>
                        <ul className="text-xs space-y-1 list-disc list-inside text-slate-300">
                          {message.fieldGuidance.questions.map((q, idx) => (
                            <li key={idx}>{q}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {Object.keys(message.fieldGuidance.suggestions).length > 0 && (
                      <div className="mt-2">
                        <div className="text-xs font-medium mb-1 text-slate-200">Suggestions:</div>
                        <div className="space-y-1">
                          {Object.entries(message.fieldGuidance.suggestions).map(([field, guidance]) => (
                            <div key={field} className="text-xs text-slate-300">
                              <span className="font-medium">{field}:</span>{' '}
                              {guidance.suggested_value !== undefined && (
                                <span className="text-emerald-400">{String(guidance.suggested_value)}</span>
                              )}
                              {guidance.question && <span className="text-slate-400"> - {guidance.question}</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-700 rounded-lg px-4 py-2">
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                  Thinking...
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error Display */}
        {error && (
          <div className="mx-4 mb-2 bg-red-500/10 border border-red-500/50 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              <p className="text-sm text-red-400">{error}</p>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-400 hover:text-red-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-slate-700 p-4">
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question or request help..."
              className="flex-1 px-4 py-2 border border-slate-600 rounded-lg bg-slate-900/50 text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 resize-none"
              rows={2}
              disabled={isLoading}
            />
            <Button
              onClick={handleSendMessage}
              disabled={isLoading || !input.trim()}
              className="px-6 bg-emerald-600 hover:bg-emerald-700"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
        </div>
      </div>
    </div>
  );
}














