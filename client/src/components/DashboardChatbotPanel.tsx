/**
 * Dashboard Chatbot Panel Component
 * 
 * Chatbot panel for the main dashboard that provides:
 * - Quick access to agent workflows (LangAlpha, DeepResearch, PeopleHub)
 * - Document and deal context awareness
 * - Workflow launching capabilities
 * - Conversation history
 * 
 * This is a simplified version of DigitizerChatbot optimized for dashboard use.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  Loader2,
  // X, Sparkles, Workflow removed - unused
  Search,
  BarChart3,
  User,
  // CheckCircle2, AlertCircle removed - unused
  Minimize2,
  Maximize2
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useFDC3, type WorkflowLinkContext } from '@/context/FDC3Context';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/toast';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  workflowLaunched?: string;
  workflowResult?: {
    workflow_type?: string;
    message?: string;
    result?: unknown;
  };
}

interface DashboardChatbotPanelProps {
  dealId?: number | null;
  documentId?: number | null;
  className?: string;
}

export function DashboardChatbotPanel({
  dealId,
  documentId,
  className = ''
}: DashboardChatbotPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [_workflowLaunching, setWorkflowLaunching] = useState<string | null>(null); // Prefix with _ - unused
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { broadcast } = useFDC3();
  const { addToast } = useToast();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: 'Hello! I can help you with:\n\n• Launching agent workflows (LangAlpha, DeepResearch, PeopleHub)\n• Answering questions about documents and deals\n• Providing analysis and insights\n\nWhat would you like to do?',
        timestamp: new Date()
      }]);
    }
  }, []);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // Check if message is a workflow launch request
      const lowerInput = input.toLowerCase();
      let workflowType: string | null = null;

      if (lowerInput.includes('langalpha') || lowerInput.includes('quantitative') || lowerInput.includes('analyze company') || lowerInput.includes('analyze market')) {
        workflowType = 'langalpha';
      } else if (lowerInput.includes('deepresearch') || lowerInput.includes('research') || lowerInput.includes('investigate')) {
        workflowType = 'deepresearch';
      } else if (lowerInput.includes('peoplehub') || lowerInput.includes('profile') || lowerInput.includes('person research')) {
        workflowType = 'peoplehub';
      }

      if (workflowType) {
        setWorkflowLaunching(workflowType);
        await handleWorkflowLaunch(workflowType, input.trim());
        setWorkflowLaunching(null);
      } else {
        // Regular chat message
        const response = await fetchWithAuth('/api/digitizer-chatbot/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: input.trim(),
            deal_id: dealId,
            document_id: documentId
          })
        });

        if (!response.ok) {
          throw new Error('Failed to get response');
        }

        const data = await response.json();
        
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.response || data.message || 'I received your message.',
          timestamp: new Date(),
          workflowLaunched: data.workflow_launched,
          workflowResult: data.workflow_result
        };

        setMessages(prev => [...prev, assistantMessage]);

        // Broadcast FDC3 context if workflow was launched
        if (data.workflow_launched && data.workflow_result) {
          try {
            const workflowContext: WorkflowLinkContext = {
              type: 'finos.creditnexus.workflow',
              id: { workflowId: `workflow_${Date.now()}` },
              workflowType: data.workflow_launched,
              linkPayload: JSON.stringify(data.workflow_result)
            };
            await broadcast(workflowContext);
          } catch (e) {
            console.warn('Failed to broadcast FDC3 context:', e);
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      addToast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to process message',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [input, loading, dealId, documentId, broadcast, addToast]);

  const handleWorkflowLaunch = async (workflowType: string, query: string) => {
    try {
      let endpoint = '';
      let body: Record<string, unknown> = {};

      if (workflowType === 'langalpha') {
        // Determine analysis type from query
        if (query.toLowerCase().includes('market')) {
          endpoint = '/api/quantitative-analysis/market';
          body = { query, deal_id: dealId };
        } else if (query.toLowerCase().includes('loan') || query.toLowerCase().includes('borrower')) {
          endpoint = '/api/quantitative-analysis/loan-application';
          body = { query, borrower_name: extractBorrowerName(query), deal_id: dealId };
        } else {
          endpoint = '/api/quantitative-analysis/company';
          body = { query, ticker: extractTicker(query), company_name: extractCompanyName(query), deal_id: dealId };
        }
      } else if (workflowType === 'deepresearch') {
        endpoint = '/api/deep-research/query';
        body = { query, deal_id: dealId };
      } else if (workflowType === 'peoplehub') {
        endpoint = '/api/business-intelligence/research-person';
        const personName = extractPersonName(query);
        body = { person_name: personName, deal_id: dealId };
      }

      if (!endpoint) {
        throw new Error(`Unknown workflow type: ${workflowType}`);
      }

      const response = await fetchWithAuth(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || errorData.message || 'Workflow launch failed');
      }

      const result = await response.json();
      
      const workflowMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `✅ ${workflowType === 'langalpha' ? 'LangAlpha' : workflowType === 'deepresearch' ? 'DeepResearch' : 'PeopleHub'} workflow launched successfully!\n\n${result.message || 'Analysis is in progress. You can view the results in the Agent Dashboard.'}`,
        timestamp: new Date(),
        workflowLaunched: workflowType,
        workflowResult: result
      };

      setMessages(prev => [...prev, workflowMessage]);

      // Broadcast FDC3 context
      try {
        const workflowContext: WorkflowLinkContext = {
          type: 'finos.creditnexus.workflow',
          id: { workflowId: `workflow_${Date.now()}` },
          workflowType: workflowType,
          linkPayload: JSON.stringify(result)
        };
        await broadcast(workflowContext);
      } catch (e) {
        console.warn('Failed to broadcast FDC3 context:', e);
      }

      addToast({
        title: 'Workflow Launched',
        description: `${workflowType} workflow started successfully`,
        variant: 'default'
      });
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `❌ Failed to launch ${workflowType} workflow: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      addToast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to launch workflow',
        variant: 'destructive'
      });
    }
  };

  // Helper functions to extract information from queries
  const extractTicker = (query: string): string | undefined => {
    const tickerMatch = query.match(/\b([A-Z]{1,5})\b/);
    return tickerMatch ? tickerMatch[1] : undefined;
  };

  const extractCompanyName = (query: string): string | undefined => {
    // Simple extraction - look for capitalized words after "company" or "analyze"
    const match = query.match(/(?:company|analyze|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i);
    return match ? match[1] : undefined;
  };

  const extractBorrowerName = (query: string): string | undefined => {
    const match = query.match(/(?:borrower|for|applicant)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i);
    return match ? match[1] : undefined;
  };

  const extractPersonName = (query: string): string => {
    const match = query.match(/(?:person|profile|research|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i);
    return match ? match[1] : 'Unknown Person';
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isMinimized) {
    return (
      <Card className={`bg-slate-800 border-slate-700 ${className}`}>
        <CardHeader className="p-3 cursor-pointer" onClick={() => setIsMinimized(false)}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-emerald-400" />
              <CardTitle className="text-sm text-slate-100">Chatbot</CardTitle>
            </div>
            <Maximize2 className="h-4 w-4 text-slate-400" />
          </div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className={`bg-slate-800 border-slate-700 flex flex-col ${className}`} style={{ height: '600px' }}>
      <CardHeader className="flex flex-row items-center justify-between p-4 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-emerald-400" />
          <CardTitle className="text-slate-100">Dashboard Assistant</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          {dealId && (
            <Badge variant="outline" className="text-xs">
              Deal {dealId}
            </Badge>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsMinimized(true)}
            className="h-8 w-8"
          >
            <Minimize2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      {/* Messages */}
      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.role === 'user'
                  ? 'bg-emerald-500/20 text-slate-100'
                  : 'bg-slate-900/50 text-slate-200'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              {message.workflowLaunched && (
                <div className="mt-2 pt-2 border-t border-slate-700">
                  <Badge variant="outline" className="text-xs mb-1">
                    {message.workflowLaunched === 'langalpha' && <BarChart3 className="h-3 w-3 mr-1" />}
                    {message.workflowLaunched === 'deepresearch' && <Search className="h-3 w-3 mr-1" />}
                    {message.workflowLaunched === 'peoplehub' && <User className="h-3 w-3 mr-1" />}
                    {message.workflowLaunched}
                  </Badge>
                  {message.workflowResult?.message && (
                    <p className="text-xs text-slate-400 mt-1">
                      {message.workflowResult.message}
                    </p>
                  )}
                </div>
              )}
              <p className="text-xs text-slate-500 mt-1">
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-900/50 rounded-lg p-3">
              <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </CardContent>

      {/* Quick Actions */}
      <div className="px-4 py-2 border-t border-slate-700">
        <div className="flex gap-2 mb-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setInput('Launch LangAlpha to analyze a company')}
            className="text-xs"
            disabled={loading}
          >
            <BarChart3 className="h-3 w-3 mr-1" />
            LangAlpha
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setInput('Launch DeepResearch to investigate')}
            className="text-xs"
            disabled={loading}
          >
            <Search className="h-3 w-3 mr-1" />
            DeepResearch
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setInput('Launch PeopleHub to research a person')}
            className="text-xs"
            disabled={loading}
          >
            <User className="h-3 w-3 mr-1" />
            PeopleHub
          </Button>
        </div>
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-700">
        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question or launch a workflow..."
            className="flex-1 bg-slate-900 border-slate-700 text-slate-100 resize-none"
            rows={2}
            disabled={loading}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="bg-emerald-500 hover:bg-emerald-600"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </Card>
  );
}
