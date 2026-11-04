import React, { useState } from 'react';
import {
  Bot,
  User,
  FileCode,
  Layers,
  ShieldAlert,
  HeartPulse,
  Package,
  Activity,
  ChevronDown,
  ChevronUp,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { ConversationMessage } from '../../types';
import { MarkdownRenderer } from './MarkdownRenderer';

interface ChatMessageProps {
  message: ConversationMessage;
  onSelectFollowUp?: (question: string) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onSelectFollowUp }) => {
  const isUser = message.role === 'user';
  const [showSources, setShowSources] = useState<boolean>(false);

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const renderSourceIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'file':
        return <FileCode className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" />;
      case 'component':
        return <Layers className="w-3.5 h-3.5 text-cyan-500 dark:text-cyan-400" />;
      case 'risk':
        return <ShieldAlert className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" />;
      case 'health':
        return <HeartPulse className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />;
      case 'dependency':
        return <Package className="w-3.5 h-3.5 text-purple-500 dark:text-purple-400" />;
      case 'hotspot':
        return <Activity className="w-3.5 h-3.5 text-rose-500 dark:text-rose-400" />;
      default:
        return <Sparkles className="w-3.5 h-3.5 text-cyan-500 dark:text-cyan-400" />;
    }
  };

  if (isUser) {
    return (
      <div className="flex justify-end items-start space-x-3 my-4 pl-12">
        <div className="flex flex-col items-end max-w-2xl">
          <div className="px-4 py-2.5 rounded-2xl rounded-tr-sm bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md text-xs leading-relaxed font-sans">
            {message.content}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-gray-400 font-mono mt-1 mr-1">
            {formatTime(message.timestamp)}
          </span>
        </div>
        <div className="w-8 h-8 rounded-xl bg-slate-100 border border-slate-200 text-slate-700 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300 flex items-center justify-center shrink-0 shadow-sm">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  const sources = message.sources || [];
  const followUps = message.suggested_questions || [];

  return (
    <div className="flex justify-start items-start space-x-3 my-4 pr-12 group">
      {/* Bot Avatar */}
      <div className="w-8 h-8 rounded-xl bg-cyan-50 border border-cyan-200 text-cyan-600 dark:bg-gradient-to-tr dark:from-cyan-950 dark:to-blue-900 dark:border-cyan-500/40 dark:text-cyan-400 flex items-center justify-center shrink-0 shadow-sm dark:shadow-lg dark:shadow-cyan-500/10">
        <Bot className="w-4 h-4" />
      </div>

      <div className="flex-1 max-w-3xl min-w-0">
        {/* Assistant Response Card */}
        <div className="p-4 rounded-2xl rounded-tl-sm bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800 shadow-sm dark:shadow-xl backdrop-blur-sm transition-colors">
          {/* Main Grounded Answer */}
          <MarkdownRenderer content={message.content} />

          {/* Supporting Evidence Sources Drawer */}
          {sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-100 dark:border-gray-800/80">
              <button
                onClick={() => setShowSources(!showSources)}
                className="flex items-center space-x-2 text-[11px] font-semibold text-slate-500 hover:text-cyan-600 dark:text-gray-400 dark:hover:text-cyan-400 transition-colors uppercase tracking-wider"
              >
                <Sparkles className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                <span>Referenced Intelligence ({sources.length})</span>
                {showSources ? (
                  <ChevronUp className="w-3 h-3 text-slate-400 dark:text-gray-400" />
                ) : (
                  <ChevronDown className="w-3 h-3 text-slate-400 dark:text-gray-400" />
                )}
              </button>

              {showSources && (
                <div className="mt-2.5 grid grid-cols-1 sm:grid-cols-2 gap-2 animate-in fade-in duration-200">
                  {sources.map((src, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded-lg bg-slate-50 dark:bg-gray-900/70 border border-slate-200 dark:border-gray-800/80 flex items-start space-x-2 text-left"
                    >
                      <div className="mt-0.5 shrink-0">{renderSourceIcon(src.type)}</div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-semibold text-slate-800 dark:text-slate-200 truncate">
                            {src.name}
                          </span>
                          <span className="text-[9px] uppercase font-mono px-1 rounded bg-slate-200 dark:bg-gray-800 text-slate-600 dark:text-gray-400 ml-1">
                            {src.type}
                          </span>
                        </div>
                        {src.path && (
                          <div className="text-[10px] text-slate-500 dark:text-gray-400 font-mono truncate" title={src.path}>
                            {src.path}
                          </div>
                        )}
                        {src.detail && (
                          <div className="text-[10px] text-slate-500 dark:text-gray-400 line-clamp-1 mt-0.5">
                            {src.detail}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Contextual Follow-Up Suggestions */}
          {followUps.length > 0 && onSelectFollowUp && (
            <div className="mt-3.5 pt-3 border-t border-slate-100 dark:border-gray-800/80">
              <div className="text-[10px] uppercase font-semibold text-slate-400 dark:text-gray-400 tracking-wider mb-2">
                Suggested Follow-up
              </div>
              <div className="flex flex-wrap gap-1.5">
                {followUps.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectFollowUp(q)}
                    className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-cyan-50 hover:bg-cyan-100 dark:bg-cyan-950/40 dark:hover:bg-cyan-900/60 border border-cyan-200 dark:border-cyan-800/60 text-[11px] text-cyan-700 hover:text-cyan-800 dark:text-cyan-300 dark:hover:text-cyan-200 transition-all text-left shadow-sm"
                  >
                    <span>{q}</span>
                    <ArrowRight className="w-3 h-3 text-cyan-600 dark:text-cyan-400 shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <span className="text-[10px] text-slate-400 dark:text-gray-400 font-mono mt-1 ml-1 block">
          {formatTime(message.timestamp)} • Grounded with Qwen (Ollama)
        </span>
      </div>
    </div>
  );
};
