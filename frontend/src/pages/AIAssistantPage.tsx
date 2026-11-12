import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  Cpu,
  Layers,
  ShieldAlert,
  HeartPulse,
  Package,
  Trash2,
  FolderGit2,
  ArrowRight,
  HelpCircle,
  AlertCircle,
  Square,
  RotateCcw,
} from 'lucide-react';
import { Project, ConversationMessage, OllamaStatus } from '../types';
import { apiService } from '../services/api';
import { ChatMessage } from '../components/assistant/ChatMessage';
import { OllamaStatusModal } from '../components/assistant/OllamaStatusModal';

interface AIAssistantPageProps {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

export const AIAssistantPage: React.FC<AIAssistantPageProps> = ({
  activeProject,
  onOpenConnectModal,
}) => {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [inputText, setInputText] = useState<string>('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState<boolean>(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom of conversation
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Fetch Ollama health status
  const fetchStatus = useCallback(async () => {
    try {
      const status = await apiService.getAssistantStatus();
      setOllamaStatus(status);
    } catch (err) {
      console.warn('Could not fetch Ollama status:', err);
      setOllamaStatus({
        connected: false,
        base_url: 'http://localhost:11434',
        model: 'qwen2.5:3b',
        model_available: false,
        available_models: [],
        error: 'Unable to reach backend assistant status endpoint.',
      });
    }
  }, []);

  // Fetch contextual suggestions for the active project
  const fetchSuggestedQuestions = useCallback(async (projectId: number) => {
    try {
      const data = await apiService.getAssistantSuggestedQuestions(projectId);
      if (data && data.questions && data.questions.length > 0) {
        setSuggestedQuestions(data.questions);
      } else {
        setSuggestedQuestions([
          `Explain the architecture and main modules of ${activeProject?.name || 'this project'}.`,
          'What are the highest-risk components in this repository?',
          'What is the overall software health score and what factors drive it?',
          'What are the most active code change hotspots?',
        ]);
      }
    } catch (err) {
      console.warn('Failed to load suggested questions:', err);
      setSuggestedQuestions([
        'Explain the project architecture and modules.',
        'What are the highest-risk components in this repository?',
        'How healthy is this software project?',
        'Which files have the highest code churn?',
      ]);
    }
  }, [activeProject?.name]);

  // Initial load
  useEffect(() => {
    fetchStatus();
    if (activeProject) {
      fetchSuggestedQuestions(activeProject.id);
    }
  }, [activeProject, fetchStatus, fetchSuggestedQuestions]);

  // Send question to Assistant API via Real-Time Streaming SSE
  const handleSendMessage = async (textToSend?: string) => {
    const question = (textToSend || inputText).trim();
    if (!question || !activeProject || isLoading) return;

    // Reset input
    if (!textToSend) {
      setInputText('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
    setErrorMessage(null);

    // Abort any previous pending stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const userMsg: ConversationMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };

    const assistantMsgId = `assistant-${Date.now()}`;
    const assistantPlaceholder: ConversationMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
      sources: [],
      suggested_questions: [],
    };

    setMessages((prev) => [...prev, userMsg, assistantPlaceholder]);
    setIsLoading(true);

    try {
      await apiService.streamAssistant(
        activeProject.id,
        question,
        conversationId || undefined,
        {
          onStart: (data) => {
            if (data.conversation_id) {
              setConversationId(data.conversation_id);
            }
          },
          onSources: (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      sources: data.sources,
                      suggested_questions: m.suggested_questions,
                    }
                  : m
              )
            );
          },
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },
          onDone: (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      content: data.answer || m.content,
                      isStreaming: false,
                      suggested_questions: data.suggested_questions,
                      recommendations: data.recommendations,
                    }
                  : m
              )
            );
            if (data.conversation_id) {
              setConversationId(data.conversation_id);
            }
          },
          onError: (err) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      isStreaming: false,
                      content: m.content
                        ? `${m.content}\n\n**Error:** ${err}`
                        : `**Error:** ${err}`,
                    }
                  : m
              )
            );
          },
        },
        abortController.signal
      );
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, isStreaming: false } : m))
        );
      } else {
        console.error('Error during streaming assistant response:', err);
        const detail =
          err?.message ||
          'Could not reach AI Assistant engine. Please ensure backend and Ollama are running.';
        setErrorMessage(detail);

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  isStreaming: false,
                  content: m.content
                    ? `${m.content}\n\n**Error:** ${detail}`
                    : `**Error:** ${detail}\n\nPlease verify that Ollama is healthy and your local Qwen model is active.`,
                }
              : m
          )
        );
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  };

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m))
    );
  };

  const handleRegenerate = (targetMsg: ConversationMessage) => {
    const idx = messages.findIndex((m) => m.id === targetMsg.id);
    if (idx > 0 && messages[idx - 1].role === 'user') {
      const prevQuestion = messages[idx - 1].content;
      // Remove current assistant message and re-send question
      setMessages((prev) => prev.filter((m) => m.id !== targetMsg.id));
      handleSendMessage(prevQuestion);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  const handleClearConversation = async () => {
    if (conversationId && activeProject) {
      try {
        await apiService.clearAssistantConversation(activeProject.id, conversationId);
      } catch (err) {
        console.warn('Could not clear backend session:', err);
      }
    }
    setMessages([]);
    setConversationId(null);
    setErrorMessage(null);
  };

  if (!activeProject) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30 flex items-center justify-center mx-auto text-cyan-600 dark:text-cyan-400 shadow-xl shadow-cyan-500/10">
          <Bot className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">AI Project Assistant</h2>
          <p className="text-xs text-slate-600 dark:text-gray-400 max-w-md mx-auto leading-relaxed">
            Connect a software repository to ask questions about architecture, components,
            dependencies, health, risks, and code.
          </p>
        </div>
        <button
          onClick={onOpenConnectModal}
          className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold shadow-lg shadow-cyan-600/20 transition-all"
        >
          <FolderGit2 className="w-4 h-4" />
          <span>Connect Repository</span>
        </button>
      </div>
    );
  }

  const isOllamaConnected = ollamaStatus?.connected === true;
  const isModelReady = ollamaStatus?.model_available === true;
  const configuredModel = ollamaStatus?.model || 'qwen/qwen3.8-27b';
  const isGroq = ollamaStatus?.provider === 'groq' || !ollamaStatus?.base_url?.includes('localhost');

  // Identify index of the latest assistant message for showing the Regenerate button
  const assistantMessages = messages.filter((m) => m.role === 'assistant');
  const latestAssistantId =
    assistantMessages.length > 0 ? assistantMessages[assistantMessages.length - 1].id : null;

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] max-w-5xl mx-auto">
      {/* Assistant Header */}
      <div className="pb-4 border-b border-slate-200 dark:border-gray-800 shrink-0 flex flex-wrap items-center justify-between gap-3 transition-colors">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center text-white shadow-md shadow-cyan-500/20">
              <Bot className="w-4 h-4" />
            </div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center">
              AI Project Assistant
              <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-950 dark:text-cyan-400 dark:border-cyan-800">
                AI Core
              </span>
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-gray-400 mt-0.5">
            Ask questions about your software architecture, dependencies, risks, and codebase.
          </p>
        </div>

        {/* Status Badge & Actions */}
        <div className="flex items-center space-x-2">
          {/* Active Project Pill */}
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-slate-100 dark:bg-gray-900 border border-slate-200 dark:border-gray-800 text-xs text-slate-700 dark:text-gray-300 font-mono">
            <FolderGit2 className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
            <span className="truncate max-w-[140px] sm:max-w-[200px]">
              {activeProject.full_name}
            </span>
          </div>

          {/* Ollama Status Pill */}
          <button
            onClick={() => setIsStatusModalOpen(true)}
            className={`flex items-center space-x-2 px-3 py-1 rounded-lg border text-xs font-mono transition-all ${
              isOllamaConnected && isModelReady
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/30 dark:border-emerald-500/40 dark:text-emerald-400 dark:hover:bg-emerald-950/50'
                : isOllamaConnected && !isModelReady
                ? 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100 dark:bg-amber-950/30 dark:border-amber-500/40 dark:text-amber-400 dark:hover:bg-amber-950/50'
                : 'bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100 dark:bg-rose-950/30 dark:border-rose-500/40 dark:text-rose-400 dark:hover:bg-rose-950/50'
            }`}
            title="Click to view Ollama and Qwen configuration"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isOllamaConnected && isModelReady
                  ? 'bg-emerald-500 dark:bg-emerald-400 animate-pulse'
                  : 'bg-rose-500 dark:bg-rose-400'
              }`}
            />
            <Cpu className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">
              {isGroq ? 'Groq' : 'Ollama'} • {configuredModel}
            </span>
            <span className="sm:hidden">
              {isOllamaConnected ? 'Online' : 'Offline'}
            </span>
          </button>

          {/* Clear Chat Button */}
          {messages.length > 0 && (
            <button
              onClick={handleClearConversation}
              className="p-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-500 hover:text-rose-600 hover:bg-slate-200 dark:bg-gray-900 dark:border-gray-800 dark:text-gray-400 dark:hover:text-rose-400 transition-colors"
              title="Clear conversation"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          {/* Setup / Help Button */}
          <button
            onClick={() => setIsStatusModalOpen(true)}
            className="p-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-500 hover:text-cyan-600 hover:bg-slate-200 dark:bg-gray-900 dark:border-gray-800 dark:text-gray-400 dark:hover:text-cyan-400 transition-colors"
            title="Setup Guide & Help"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Conversation Area */}
      <div className="flex-1 overflow-y-auto py-4 px-2 space-y-2">
        {messages.length === 0 ? (
          /* Empty State / Welcome Screen */
          <div className="py-8 space-y-6 max-w-3xl mx-auto">
            {/* Welcome Hero Banner */}
            <div className="p-6 rounded-2xl bg-white dark:bg-gradient-to-b dark:from-gray-900/80 dark:to-[#111827]/80 border border-slate-200 dark:border-gray-800 text-center space-y-3 shadow-sm dark:shadow-xl backdrop-blur-sm transition-colors">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center mx-auto text-white shadow-lg shadow-cyan-500/20">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
                Software Intelligence Assistant for {activeProject.name}
              </h3>
              <p className="text-xs text-slate-600 dark:text-gray-300 max-w-lg mx-auto leading-relaxed">
                Powered by <strong className="text-cyan-600 dark:text-cyan-400 font-medium">{isGroq ? 'Groq Cloud LPU' : 'Local Qwen'}</strong> intelligence. Answers are
                grounded in real-time AST parsing, dependency graphs, health scores, and risk
                detections.
              </p>
              <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-cyan-50 dark:bg-cyan-950/60 border border-cyan-200 dark:border-cyan-800/80 text-[11px] text-cyan-700 dark:text-cyan-300 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 dark:bg-cyan-400 animate-ping" />
                <span>{isGroq ? 'Sub-Second Groq LPU Inference • Verified Repository Telemetry' : '100% Local Inference • Zero External Cloud Telemetry'}</span>
              </div>
            </div>

            {/* Capability Feature Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-white dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800 shadow-sm dark:shadow-none flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20 shrink-0">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-slate-900 dark:text-white">Architecture & Coupling</div>
                  <div className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
                    Query module organization, circular dependency cycles, and coupling hotspots.
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-white dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800 shadow-sm dark:shadow-none flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-cyan-50 dark:bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-500/20 shrink-0">
                  <Package className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-slate-900 dark:text-white">Component Blast Radius</div>
                  <div className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
                    Explore direct dependents and impact analysis before removing packages or files.
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-white dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800 shadow-sm dark:shadow-none flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 shrink-0">
                  <HeartPulse className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-slate-900 dark:text-white">Software Health Score</div>
                  <div className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
                    Understand overall health scoring, dimension breakdowns, and quality indicators.
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-white dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800 shadow-sm dark:shadow-none flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20 shrink-0">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-slate-900 dark:text-white">Active Engineering Risks</div>
                  <div className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
                    Inspect detected engineering risks, backlog staleness, and remediation priorities.
                  </div>
                </div>
              </div>
            </div>

            {/* Contextual Suggested Questions Section */}
            {suggestedQuestions.length > 0 && (
              <div className="space-y-2.5 pt-2">
                <div className="text-[11px] uppercase font-semibold text-slate-500 dark:text-gray-400 tracking-wider flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                  <span>Suggested Questions for {activeProject.name}</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {suggestedQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(q)}
                      className="p-3 rounded-xl bg-white hover:bg-slate-50 dark:bg-[#111827]/70 dark:hover:bg-gray-800/80 border border-slate-200 dark:border-gray-800/80 hover:border-cyan-500/40 text-left text-xs text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition-all flex items-start justify-between space-x-2 group shadow-sm"
                    >
                      <span className="leading-snug">{q}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan-600 dark:text-gray-400 dark:group-hover:text-cyan-400 shrink-0 mt-0.5 transition-colors" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Render Active Message Stream */
          <div className="space-y-1">
            {messages.map((m) => (
              <ChatMessage
                key={m.id}
                message={m}
                onSelectFollowUp={(followUp) => handleSendMessage(followUp)}
                onRegenerate={handleRegenerate}
                isLatestAssistant={m.id === latestAssistantId}
              />
            ))}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Bottom Input Area */}
      <div className="pt-3 border-t border-slate-200 dark:border-gray-800 shrink-0">
        {!isOllamaConnected && (
          <div className="mb-2.5 px-3.5 py-2 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-500/30 text-xs text-amber-800 dark:text-amber-300 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
              <span>
                Ollama is currently unreachable. Make sure <code className="font-mono bg-amber-100 dark:bg-black/40 px-1 py-0.5 rounded text-amber-900 dark:text-white">ollama serve</code> is running.
              </span>
            </div>
            <button
              onClick={() => setIsStatusModalOpen(true)}
              className="text-[11px] underline hover:text-amber-950 dark:hover:text-white font-medium ml-2 shrink-0"
            >
              Setup Guide
            </button>
          </div>
        )}

        {/* Suggested Follow-up Quick Pills above input if chat is active */}
        {messages.length > 0 && !isLoading && suggestedQuestions.length > 0 && (
          <div className="mb-2 flex items-center space-x-1.5 overflow-x-auto pb-1 text-xs scrollbar-none">
            <span className="text-[10px] text-slate-400 dark:text-gray-500 font-mono shrink-0 mr-1 flex items-center">
              <Sparkles className="w-3 h-3 mr-1 text-cyan-500" /> Suggestions:
            </span>
            {suggestedQuestions.slice(0, 3).map((sq, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(sq)}
                className="shrink-0 px-2.5 py-1 rounded-full bg-slate-100 hover:bg-cyan-50 dark:bg-gray-800/80 dark:hover:bg-cyan-950/40 border border-slate-200 dark:border-gray-700/80 hover:border-cyan-500/40 text-[11px] text-slate-600 dark:text-gray-300 hover:text-cyan-700 dark:hover:text-cyan-300 transition-all truncate max-w-[280px]"
                title={sq}
              >
                {sq}
              </button>
            ))}
          </div>
        )}

        {/* Input Box with Send / Stop Generating Button */}
        <div className="relative rounded-2xl bg-white dark:bg-[#111827]/95 border border-slate-300 dark:border-gray-800 focus-within:border-cyan-500/60 shadow-md dark:shadow-xl backdrop-blur-sm transition-all p-1.5 flex items-end space-x-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder={`Ask anything or inquiry about ${activeProject.name}'s architecture, dependencies, risks...`}
            className="flex-1 bg-transparent px-3 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-gray-400 resize-none focus:outline-none max-h-32 min-h-[38px] leading-relaxed"
          />

          {isLoading ? (
            <button
              onClick={handleStopGenerating}
              className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white dark:bg-gray-700 dark:hover:bg-gray-600 transition-all shadow-md shrink-0 flex items-center space-x-1.5 px-3"
              title="Stop generating response"
            >
              <Square className="w-3.5 h-3.5 fill-current text-rose-400" />
              <span className="text-[11px] font-medium hidden sm:inline">Stop</span>
            </button>
          ) : (
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputText.trim()}
              className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white disabled:opacity-40 disabled:hover:from-cyan-600 disabled:hover:to-blue-600 transition-all shadow-md shadow-cyan-600/20 shrink-0"
              title="Send message (Enter)"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="flex items-center justify-between px-2 pt-1.5 text-[10px] text-slate-400 dark:text-gray-400 font-mono">
          <span>Press Enter to send • Shift+Enter for new line</span>
          <span>Inference Model: {configuredModel}</span>
        </div>
      </div>

      {/* Ollama Status & Setup Guide Modal */}
      <OllamaStatusModal
        isOpen={isStatusModalOpen}
        onClose={() => setIsStatusModalOpen(false)}
        status={ollamaStatus}
        onRefreshStatus={fetchStatus}
      />
    </div>
  );
};
