import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  RefreshCw,
  Cpu,
  Layers,
  ShieldAlert,
  HeartPulse,
  Package,
  Activity,
  Trash2,
  FolderGit2,
  ArrowRight,
  HelpCircle,
  AlertCircle,
} from 'lucide-react';
import { Project, ConversationMessage, OllamaStatus, AssistantSourceItem } from '../types';
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
        model: 'qwen2.5:7b',
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
  }, [fetchStatus, fetchSuggestedQuestions, activeProject]);

  // Send message handler
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputText).trim();
    if (!query || isLoading) return;

    if (!activeProject) {
      onOpenConnectModal();
      return;
    }

    setErrorMessage(null);
    setInputText('');

    // Append user message immediately
    const userMessage: ConversationMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await apiService.askAssistant(
        activeProject.id,
        query,
        conversationId || undefined
      );

      setConversationId(response.conversation_id);

      const assistantMessage: ConversationMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toISOString(),
        sources: response.sources,
        suggested_questions: response.suggested_questions,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error('Error asking assistant:', err);
      const errText =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to generate response. Please verify Ollama is running.';

      setErrorMessage(errText);

      // Add friendly error message turn
      const errorTurn: ConversationMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `> **Assistant Notice:** ${errText}\n\nPlease ensure Ollama is running locally with the configured Qwen model.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorTurn]);
    } finally {
      setIsLoading(false);
      // Focus textarea
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  };

  // Clear conversation handler
  const handleClearConversation = async () => {
    if (conversationId && activeProject) {
      try {
        await apiService.clearAssistantConversation(activeProject.id, conversationId);
      } catch (err) {
        console.warn('Failed to clear conversation on backend:', err);
      }
    }
    setMessages([]);
    setConversationId(null);
    setErrorMessage(null);
    if (activeProject) {
      fetchSuggestedQuestions(activeProject.id);
    }
  };

  // Keyboard handler: Enter sends, Shift+Enter newlines
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!activeProject) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto text-cyan-400 shadow-xl shadow-cyan-500/10">
          <Bot className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-white tracking-tight">AI Project Assistant</h2>
          <p className="text-xs text-gray-400 max-w-md mx-auto leading-relaxed">
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
  const configuredModel = ollamaStatus?.model || 'qwen2.5:7b';

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] max-w-5xl mx-auto">
      {/* Assistant Header */}
      <div className="pb-4 border-b border-gray-800 shrink-0 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center text-white shadow-md shadow-cyan-500/20">
              <Bot className="w-4 h-4" />
            </div>
            <h2 className="text-base font-bold text-white tracking-tight flex items-center">
              AI Project Assistant
              <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800">
                Phase 7
              </span>
            </h2>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Ask questions about your software architecture, dependencies, risks, and codebase.
          </p>
        </div>

        {/* Status Badge & Actions */}
        <div className="flex items-center space-x-2">
          {/* Active Project Pill */}
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-gray-900 border border-gray-800 text-xs text-gray-300 font-mono">
            <FolderGit2 className="w-3.5 h-3.5 text-cyan-400" />
            <span className="truncate max-w-[140px] sm:max-w-[200px]">
              {activeProject.full_name}
            </span>
          </div>

          {/* Ollama Status Pill */}
          <button
            onClick={() => setIsStatusModalOpen(true)}
            className={`flex items-center space-x-2 px-3 py-1 rounded-lg border text-xs font-mono transition-all ${
              isOllamaConnected && isModelReady
                ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-400 hover:bg-emerald-950/50'
                : isOllamaConnected && !isModelReady
                ? 'bg-amber-950/30 border-amber-500/40 text-amber-400 hover:bg-amber-950/50'
                : 'bg-rose-950/30 border-rose-500/40 text-rose-400 hover:bg-rose-950/50'
            }`}
            title="Click to view Ollama and Qwen configuration"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isOllamaConnected && isModelReady
                  ? 'bg-emerald-400 animate-pulse'
                  : 'bg-rose-400'
              }`}
            />
            <Cpu className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">
              Ollama • {configuredModel}
            </span>
            <span className="sm:hidden">
              {isOllamaConnected ? 'Online' : 'Offline'}
            </span>
          </button>

          {/* Clear Chat Button */}
          {messages.length > 0 && (
            <button
              onClick={handleClearConversation}
              className="p-1.5 rounded-lg bg-gray-900 border border-gray-800 text-gray-400 hover:text-rose-400 hover:border-gray-700 transition-colors"
              title="Clear conversation"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          {/* Setup / Help Button */}
          <button
            onClick={() => setIsStatusModalOpen(true)}
            className="p-1.5 rounded-lg bg-gray-900 border border-gray-800 text-gray-400 hover:text-cyan-400 hover:border-gray-700 transition-colors"
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
            <div className="p-6 rounded-2xl bg-gradient-to-b from-gray-900/80 to-[#111827]/80 border border-gray-800 text-center space-y-3 shadow-xl backdrop-blur-sm">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center mx-auto text-white shadow-lg shadow-cyan-500/20">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Software Intelligence Assistant for {activeProject.name}
              </h3>
              <p className="text-xs text-gray-300 max-w-lg mx-auto leading-relaxed">
                Powered by a local <strong className="text-cyan-400 font-medium">Qwen</strong> model
                through <strong className="text-cyan-400 font-medium">Ollama</strong>. Answers are
                grounded in real-time AST parsing, dependency graphs, health scores, and risk
                detections from Phases 1–6.
              </p>
              <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/80 text-[11px] text-cyan-300 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                <span>100% Local Inference • Zero External Cloud Telemetry</span>
              </div>
            </div>

            {/* Capability Feature Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-gray-900/40 border border-gray-800 flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 shrink-0">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-white">Architecture & Coupling</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">
                    Query module organization, circular dependency cycles, and coupling hotspots.
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-gray-900/40 border border-gray-800 flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shrink-0">
                  <Package className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-white">Component Blast Radius</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">
                    Explore direct dependents and impact analysis before removing packages or files.
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-gray-900/40 border border-gray-800 flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                  <HeartPulse className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-white">Software Health Score</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">
                    Understand overall health scoring, dimension breakdowns, and quality indicators.
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-gray-900/40 border border-gray-800 flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-white">Active Engineering Risks</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">
                    Inspect detected engineering risks, backlog staleness, and remediation priorities.
                  </div>
                </div>
              </div>
            </div>

            {/* Contextual Suggested Questions Section */}
            {suggestedQuestions.length > 0 && (
              <div className="space-y-2.5 pt-2">
                <div className="text-[11px] uppercase font-semibold text-gray-400 tracking-wider flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Suggested Questions for {activeProject.name}</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {suggestedQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(q)}
                      className="p-3 rounded-xl bg-[#111827]/70 hover:bg-gray-800/80 border border-gray-800/80 hover:border-cyan-500/40 text-left text-xs text-slate-300 hover:text-white transition-all flex items-start justify-between space-x-2 group shadow-sm"
                    >
                      <span className="leading-snug">{q}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-cyan-400 shrink-0 mt-0.5 transition-colors" />
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
              />
            ))}
          </div>
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex justify-start items-center space-x-3 my-4 pr-12 animate-in fade-in">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-950 to-blue-900 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shrink-0">
              <Bot className="w-4 h-4 animate-bounce" />
            </div>
            <div className="p-3.5 rounded-2xl rounded-tl-sm bg-[#111827]/90 border border-gray-800 text-xs text-gray-300 flex items-center space-x-2.5 shadow-lg">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <span>Analyzing project telemetry & thinking with Qwen...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Bottom Input Area */}
      <div className="pt-3 border-t border-gray-800 shrink-0">
        {!isOllamaConnected && (
          <div className="mb-2.5 px-3.5 py-2 rounded-xl bg-amber-950/30 border border-amber-500/30 text-xs text-amber-300 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                Ollama is currently unreachable. Make sure <code className="font-mono text-white">ollama serve</code> is running.
              </span>
            </div>
            <button
              onClick={() => setIsStatusModalOpen(true)}
              className="text-[11px] underline hover:text-white font-medium ml-2 shrink-0"
            >
              Setup Guide
            </button>
          </div>
        )}

        <div className="relative rounded-2xl bg-[#111827]/95 border border-gray-800 focus-within:border-cyan-500/50 shadow-xl backdrop-blur-sm transition-all p-1.5 flex items-end space-x-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask about ${activeProject.name}'s architecture, dependencies, risks, files...`}
            className="flex-1 bg-transparent px-3 py-2 text-xs text-slate-100 placeholder-gray-400 resize-none focus:outline-none max-h-32 min-h-[38px] leading-relaxed"
          />

          <button
            onClick={() => handleSendMessage()}
            disabled={!inputText.trim() || isLoading}
            className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white disabled:opacity-40 disabled:hover:from-cyan-600 disabled:hover:to-blue-600 transition-all shadow-md shadow-cyan-600/20 shrink-0"
            title="Send message (Enter)"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center justify-between px-2 pt-1.5 text-[10px] text-gray-400 font-mono">
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
