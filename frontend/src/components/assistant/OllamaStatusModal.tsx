import React, { useState } from 'react';
import {
  X,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Terminal,
  RefreshCw,
  Copy,
  Check,
} from 'lucide-react';
import { OllamaStatus } from '../../types';

interface OllamaStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  status: OllamaStatus | null;
  onRefreshStatus: () => Promise<void>;
}

export const OllamaStatusModal: React.FC<OllamaStatusModalProps> = ({
  isOpen,
  onClose,
  status,
  onRefreshStatus,
}) => {
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await onRefreshStatus();
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleCopy = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCmd(cmd);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const isConnected = status?.connected === true;
  const isModelReady = status?.model_available === true;
  const configuredModel = status?.model || 'qwen/qwen3.8-27b';
  const baseUrl = status?.base_url || 'https://api.groq.com';
  const isGroq = status?.provider === 'groq' || !baseUrl.includes('localhost');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 dark:bg-black/75 backdrop-blur-sm animate-in fade-in">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-[#0F1420] border border-slate-200 dark:border-gray-800 shadow-2xl overflow-hidden flex flex-col transition-colors">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-gray-800 bg-slate-50 dark:bg-gray-900/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                {isGroq ? 'Groq Cloud LPU Inference' : 'Local Ollama & Qwen Engine'}
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-gray-400 font-mono">
                {isGroq ? 'Ultra-Fast Groq Cloud Accelerated LLM' : 'Software Intelligence Local LLM Provider'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto max-h-[75vh]">
          {/* Status Overview Card */}
          <div
            className={`p-4 rounded-xl border flex items-start space-x-3 ${
              isConnected && isModelReady
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950/20 dark:border-emerald-500/40 dark:text-emerald-300'
                : isConnected && !isModelReady
                ? 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/20 dark:border-amber-500/40 dark:text-amber-300'
                : 'bg-rose-50 border-rose-200 text-rose-800 dark:bg-rose-950/20 dark:border-rose-500/40 dark:text-rose-300'
            }`}
          >
            {isConnected && isModelReady ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            )}
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-xs text-slate-900 dark:text-white flex items-center justify-between">
                <span>
                  {isConnected && isModelReady
                    ? `${isGroq ? 'Groq LPU' : 'Ollama'} is Active & Ready`
                    : isConnected && !isModelReady
                    ? `Connected — Model '${configuredModel}' Initializing`
                    : `${isGroq ? 'Groq API' : 'Ollama'} is Offline or Unreachable`}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-200/80 dark:bg-black/40 border border-current">
                  {isConnected ? 'ONLINE' : 'OFFLINE'}
                </span>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-gray-300 mt-1 leading-relaxed">
                {isConnected && isModelReady
                  ? `Natural language Q&A is generating grounded software intelligence answers using ${isGroq ? 'Groq LPU acceleration' : 'local Qwen'} with model ${configuredModel}.`
                  : isConnected && !isModelReady
                  ? `Connected at ${baseUrl}, but model '${configuredModel}' is not ready.`
                  : `Cannot connect to AI provider at ${baseUrl}. Please check your connection or credentials.`}
              </p>
            </div>
          </div>

          {/* Config Details */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-gray-900/60 border border-slate-200 dark:border-gray-800">
              <span className="text-[10px] uppercase font-mono text-slate-400 dark:text-gray-400 block mb-0.5">
                AI Provider Endpoint
              </span>
              <span className="font-mono text-cyan-700 dark:text-cyan-400 text-xs truncate block">{baseUrl}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-gray-900/60 border border-slate-200 dark:border-gray-800">
              <span className="text-[10px] uppercase font-mono text-slate-400 dark:text-gray-400 block mb-0.5">
                Active Model
              </span>
              <span className="font-mono text-cyan-700 dark:text-cyan-400 text-xs truncate block">{configuredModel}</span>
            </div>
          </div>

          {/* Step-by-Step Setup Guide */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-600 dark:text-gray-300 uppercase tracking-wider flex items-center space-x-2">
              <Terminal className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
              <span>Ollama + Qwen Setup Instructions</span>
            </h4>

            {/* Step 1 */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-900 dark:text-white">1. Install Ollama</span>
                <a
                  href="https://ollama.com"
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan-600 hover:text-cyan-700 dark:text-cyan-400 dark:hover:text-cyan-300 text-[11px] flex items-center space-x-1"
                >
                  <span>Download Ollama</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-gray-400">
                Download and install the official Ollama runtime for Windows/macOS/Linux.
              </p>
            </div>

            {/* Step 2 */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800 space-y-2">
              <div className="text-xs font-medium text-slate-900 dark:text-white">
                2. Pull the Qwen Model
              </div>
              <p className="text-[11px] text-slate-500 dark:text-gray-400">
                Open your terminal and run the following command to download the configured model:
              </p>
              <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 font-mono text-xs text-cyan-300">
                <code>ollama run {configuredModel}</code>
                <button
                  onClick={() => handleCopy(`ollama run ${configuredModel}`)}
                  className="text-gray-400 hover:text-white transition-colors"
                  title="Copy command"
                >
                  {copiedCmd === `ollama run ${configuredModel}` ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            </div>

            {/* Step 3 */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800 space-y-2">
              <div className="text-xs font-medium text-slate-900 dark:text-white">
                3. Verify / Start Service
              </div>
              <p className="text-[11px] text-slate-500 dark:text-gray-400">
                Ollama runs automatically in your system tray or can be started directly:
              </p>
              <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 font-mono text-xs text-cyan-300">
                <code>ollama serve</code>
                <button
                  onClick={() => handleCopy('ollama serve')}
                  className="text-gray-400 hover:text-white transition-colors"
                  title="Copy command"
                >
                  {copiedCmd === 'ollama serve' ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 dark:border-gray-800 bg-slate-50 dark:bg-gray-900/80">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 dark:bg-gray-800 dark:hover:bg-gray-700 text-xs font-medium text-slate-700 dark:text-gray-200 border border-slate-200 dark:border-gray-700 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Checking...' : 'Check Connection'}</span>
          </button>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium shadow-md transition-all"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
