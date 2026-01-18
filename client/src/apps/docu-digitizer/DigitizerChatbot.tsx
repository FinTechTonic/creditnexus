/**
 * Digitizer Chatbot Component
 * 
 * Modal chatbot for document digitizer UI with:
 * - Chat interface for document questions
 * - Workflow launching (PeopleHub, DeepResearch, LangAlpha)
 * - FDC3 integration for context broadcasting
 * - Deal and document context integration
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Send,
  Loader2,
  X,
  Sparkles,
  Workflow,
  User,
  Search,
  BarChart3,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { fetchWithAuth } from '../../context/AuthContext';
import { useFDC3 } from '../../context/FDC3Context';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { AgentProgressIndicator } from '../../components/agent-results/AgentProgressIndicator';
import type { AgentProgressStep } from '../../components/agent-results/AgentProgressIndicator';
import { useToast } from '../../components/ui/toast';

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

interface DigitizerChatbotProps {
  isOpen: boolean;
  onClose: () => void;
  dealId?: number | null;
  documentId?: number | null;
  documentContext?: Record<string, unknown>; // Extracted CDM data
  onWorkflowLaunched?: (workflowType: string, result: unknown) => void;
}

export function DigitizerChatbot({
  isOpen,
  onClose,
  dealId,
  documentId,
  documentContext,
  onWorkflowLaunched,
}: DigitizerChatbotProps) {
  const { broadcast } = useFDC3();
  const { addToast } = useToast();
  const [sessionId] = useState(() => `chatbot-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your AI assistant for document digitization. I can help you:\n\n• Answer questions about extracted documents\n• Launch research workflows (PeopleHub, DeepResearch, LangAlpha)\n• Understand deal context and document data\n\nHow can I help you today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [workflowProgress, setWorkflowProgress] = useState<{
    workflowType: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
    currentStep?: string;
    progress?: number;
    steps?: AgentProgressStep[];
    message?: string;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);
  
  // Helper function to get workflow label
  const getWorkflowLabel = useCallback((workflowType?: string) => {
    switch (workflowType) {
      case 'peoplehub':
        return 'PeopleHub';
      case 'deepresearch':
        return 'DeepResearch';
      case 'langalpha':
        return 'LangAlpha';
      default:
        return 'Workflow';
    }
  }, []);
  
  // Monitor workflow progress and show completion notifications for long-running workflows
  useEffect(() => {
    // Find the most recent workflow launch from messages
    const lastWorkflowMessage = [...messages].reverse().find(
      msg => msg.workflowLaunched && msg.workflowResult
    );
    
    if (!lastWorkflowMessage?.workflowLaunched || !lastWorkflowMessage?.workflowResult) {
      return;
    }
    
    const workflowLaunched = lastWorkflowMessage.workflowLaunched;
    const workflowResult = lastWorkflowMessage.workflowResult;
    
    // If workflow is already completed or failed, don't poll
    if (workflowProgress?.status === 'completed' || workflowProgress?.status === 'failed' || workflowProgress?.status === 'cancelled') {
      return;
    }
    
    // Check if workflow has an analysis_id or result_id that we can poll
    const analysisId = (workflowResult as any)?.analysis_id || (workflowResult as any)?.result?.analysis_id;
    const researchId = (workflowResult as any)?.research_id || (workflowResult as any)?.result?.research_id;
    
    if (!analysisId && !researchId) {
      return;
    }
    
    // Poll for completion status (for long-running workflows)
    const pollInterval = setInterval(async () => {
      try {
        let statusResponse;
        if (analysisId && workflowLaunched === 'langalpha') {
          statusResponse = await fetchWithAuth(`/api/quantitative-analysis/results/${analysisId}`);
        } else if (researchId && workflowLaunched === 'deepresearch') {
          statusResponse = await fetchWithAuth(`/api/deep-research/results/${researchId}`);
        }
        
        if (statusResponse && statusResponse.ok) {
          const statusData = await statusResponse.json();
          const status = statusData.status || statusData.result?.status;
          
          if (status === 'completed' || status === 'success') {
            clearInterval(pollInterval);
            setWorkflowProgress(prev => {
              if (prev?.status === 'completed') return prev; // Already notified
              return {
                ...prev!,
                status: 'completed',
                progress: 100,
                currentStep: 'Workflow completed',
                message: 'Workflow has completed successfully'
              };
            });
            
            // Show completion notification
            addToast(
              `${getWorkflowLabel(workflowLaunched)} workflow completed successfully`,
              'success',
              5000
            );
          } else if (status === 'failed' || status === 'error') {
            clearInterval(pollInterval);
            setWorkflowProgress(prev => {
              if (prev?.status === 'failed') return prev; // Already notified
              return {
                ...prev!,
                status: 'failed',
                progress: 0,
                currentStep: 'Workflow failed',
                message: statusData.message || 'Workflow encountered an error'
              };
            });
            
            // Show failure notification
            addToast(
              `${getWorkflowLabel(workflowLaunched)} workflow failed: ${statusData.message || 'Unknown error'}`,
              'error',
              7000
            );
          }
        }
      } catch (e) {
        // Silently fail - polling is best effort
        console.debug('Failed to poll workflow status:', e);
      }
    }, 3000); // Poll every 3 seconds
    
    // Clean up interval when component unmounts or dependencies change
    return () => clearInterval(pollInterval);
  }, [messages, workflowProgress, addToast, getWorkflowLabel]);

  const addMessage = useCallback((role: 'user' | 'assistant', content: string, metadata?: {
    workflowLaunched?: string;
    workflowResult?: unknown;
  }) => {
    const newMessage: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role,
      content,
      timestamp: new Date(),
      workflowLaunched: metadata?.workflowLaunched,
      workflowResult: metadata?.workflowResult as ChatMessage['workflowResult'],
    };
    setMessages(prev => [...prev, newMessage]);
    return newMessage;
  }, []);

  const handleSendMessage = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setError(null);

    // Add user message
    addMessage('user', userMessage);

    setIsLoading(true);

    try {
      // Build conversation history
      const conversationHistory = messages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
        .slice(-10) // Last 10 messages
        .map(msg => ({
          role: msg.role,
          content: msg.content,
        }));

      // Call chatbot API
      const response = await fetchWithAuth('/api/digitizer-chatbot/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          deal_id: dealId || undefined,
          document_id: documentId || undefined,
          conversation_history: conversationHistory,
          document_context: documentContext,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to get response' }));
        throw new Error(errorData.detail?.message || errorData.message || 'Chat request failed');
      }

      const data = await response.json();

      if (data.status === 'success') {
        const reply = data.response || 'I apologize, but I couldn\'t generate a response.';
        
        // Check if workflow was launched
        const workflowLaunched = data.workflow_launched;
        const workflowResult = data.workflow_result;

        // Add assistant message
        addMessage('assistant', reply, {
          workflowLaunched,
          workflowResult,
        });

        // Broadcast FDC3 context if workflow was launched
        if (workflowLaunched && workflowResult) {
          // Set workflow progress
          setWorkflowProgress({
            workflowType: workflowLaunched,
            status: 'running',
            currentStep: 'Initializing workflow...',
            progress: 10,
            message: 'Workflow has been launched and is processing'
          });

          try {
            await broadcast({
              type: 'fdc3.creditnexus.workflow',
              workflowType: workflowLaunched,
              workflowResult: workflowResult,
              dealId: dealId?.toString(),
              documentId: documentId?.toString(),
            } as any);
          } catch (e) {
            console.warn('Failed to broadcast FDC3 context:', e);
          }

          // Notify parent component
          if (onWorkflowLaunched) {
            onWorkflowLaunched(workflowLaunched, workflowResult);
          }
          
          // Show workflow launch notification
          addToast(
            `${getWorkflowLabel(workflowLaunched)} workflow launched successfully`,
            'info',
            3000
          );

          // Update progress based on workflow result
          if (workflowResult && typeof workflowResult === 'object' && 'status' in workflowResult) {
            const resultStatus = (workflowResult as any).status;
            if (resultStatus === 'success' || resultStatus === 'completed') {
              setWorkflowProgress(prev => prev ? {
                ...prev,
                status: 'completed',
                progress: 100,
                currentStep: 'Workflow completed',
                message: 'Workflow has completed successfully'
              } : null);
              
              // Show completion notification
              addToast(
                `${getWorkflowLabel(workflowLaunched)} workflow completed successfully`,
                'success',
                5000
              );
            } else if (resultStatus === 'failed' || resultStatus === 'error') {
              setWorkflowProgress(prev => prev ? {
                ...prev,
                status: 'failed',
                progress: 0,
                currentStep: 'Workflow failed',
                message: (workflowResult as any).message || 'Workflow encountered an error'
              } : null);
              
              // Show failure notification
              addToast(
                `${getWorkflowLabel(workflowLaunched)} workflow failed: ${(workflowResult as any).message || 'Unknown error'}`,
                'error',
                7000
              );
            }
          }
        }

        // Broadcast chatbot interaction context
        try {
          await broadcast({
            type: 'fdc3.creditnexus.chatbot',
            sessionId,
            message: userMessage,
            response: reply,
            dealId: dealId?.toString(),
            documentId: documentId?.toString(),
          } as any);
        } catch (e) {
          console.warn('Failed to broadcast FDC3 context:', e);
        }
        
        // Check if conversation summary should be fetched and broadcasted
        // (e.g., when conversation reaches certain length or user switches windows)
        // Only fetch if we have enough messages (10+) to make summary meaningful
        if (messages.length >= 10 && messages.length % 20 === 0) {
          try {
            const summaryResponse = await fetchWithAuth(`/api/chatbot/summary/${sessionId}`);
            if (summaryResponse.ok) {
              const summaryData = await summaryResponse.json();
              if (summaryData.summary) {
                // Broadcast conversation summary via FDC3 for memory sharing
                await broadcast({
                  type: 'fdc3.creditnexus.conversation_summary',
                  sessionId,
                  summary: summaryData.summary,
                  keyPoints: summaryData.key_points || [],
                  messageCount: summaryData.metadata?.message_count || 0,
                  dealId: dealId?.toString(),
                  documentId: documentId?.toString(),
                  summaryUpdatedAt: summaryData.metadata?.summary_updated_at
                } as any);
              }
            }
          } catch (e) {
            // Silently fail - summary fetching is optional
            console.debug('Conversation summary not available or failed to fetch:', e);
          }
        }
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
  }, [input, isLoading, messages, sessionId, dealId, documentId, documentContext, addMessage, broadcast, onWorkflowLaunched, addToast, getWorkflowLabel]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const getWorkflowIcon = (workflowType?: string) => {
    switch (workflowType) {
      case 'peoplehub':
        return <User className="w-4 h-4" />;
      case 'deepresearch':
        return <Search className="w-4 h-4" />;
      case 'langalpha':
        return <BarChart3 className="w-4 h-4" />;
      default:
        return <Workflow className="w-4 h-4" />;
    }
  };


  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[85vh] p-0 overflow-hidden bg-slate-900 border-slate-700">
        <DialogHeader className="px-6 py-4 border-b border-slate-700">
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2 text-slate-100">
              <Sparkles className="w-5 h-5" />
              Document Digitizer Assistant
            </DialogTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="text-slate-400 hover:text-slate-100"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
          {(dealId || documentId) && (
            <div className="flex items-center gap-2 mt-2 text-sm text-slate-400">
              {dealId && <Badge variant="outline">Deal: {dealId}</Badge>}
              {documentId && <Badge variant="outline">Document: {documentId}</Badge>}
            </div>
          )}
        </DialogHeader>

        <div className="flex flex-col h-[calc(85vh-120px)]">
          {/* Messages Area */}
          <div className="flex-1 px-6 py-4 overflow-y-auto">
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-slate-300" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-800 text-slate-100 border border-slate-700'
                    }`}
                  >
                    <div className="whitespace-pre-wrap break-words">{message.content}</div>
                    {message.workflowLaunched && (
                      <div className="mt-2 pt-2 border-t border-slate-600">
                        <div className="flex items-center gap-2 text-xs text-slate-400">
                          {getWorkflowIcon(message.workflowLaunched)}
                          <span>
                            {getWorkflowLabel(message.workflowLaunched)} workflow launched
                          </span>
                          {message.workflowResult && (
                            <CheckCircle2 className="w-3 h-3 text-green-500 ml-1" />
                          )}
                        </div>
                        {message.workflowResult?.message && (
                          <div className="mt-1 text-xs text-slate-300">
                            {message.workflowResult.message}
                          </div>
                        )}
                      </div>
                    )}
                    <div className="mt-1 text-xs opacity-70">
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                  {message.role === 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-slate-300" />
                  </div>
                  <div className="bg-slate-800 text-slate-100 border border-slate-700 rounded-lg px-4 py-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                </div>
              )}
              
              {/* Workflow Progress Indicator */}
              {workflowProgress && (
                <div className="mt-4">
                  <AgentProgressIndicator
                    agentType={workflowProgress.workflowType as 'deepresearch' | 'langalpha' | 'peoplehub'}
                    status={workflowProgress.status}
                    currentStep={workflowProgress.currentStep}
                    progress={workflowProgress.progress}
                    steps={workflowProgress.steps}
                    message={workflowProgress.message}
                    onCancel={() => {
                      setWorkflowProgress(prev => prev ? {
                        ...prev,
                        status: 'cancelled',
                        message: 'Workflow cancelled by user'
                      } : null);
                    }}
                  />
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="px-6 py-2 bg-red-900/20 border-t border-red-800">
              <div className="flex items-center gap-2 text-sm text-red-400">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="px-6 py-4 border-t border-slate-700">
            <div className="flex gap-2">
              <Textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question or launch a workflow (e.g., 'Research person John Doe' or 'Deep research on credit risk')..."
                className="flex-1 min-h-[60px] max-h-[120px] bg-slate-800 border-slate-700 text-slate-100 placeholder:text-slate-500 resize-none"
                disabled={isLoading}
              />
              <Button
                onClick={handleSendMessage}
                disabled={!input.trim() || isLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
            <div className="mt-2 text-xs text-slate-500">
              Tip: Say "Research person [name]" to launch PeopleHub, or "Deep research [query]" for DeepResearch
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
