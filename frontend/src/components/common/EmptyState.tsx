import React from 'react';
import { GitBranch, Plus, Sparkles, Activity, ShieldCheck, Cpu } from 'lucide-react';

interface EmptyStateProps {
  onConnectClick: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ onConnectClick }) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] max-w-2xl mx-auto text-center px-4 py-12">
      <div className="relative mb-6">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-2xl shadow-cyan-500/20 border border-cyan-400/30">
          <Cpu className="w-10 h-10 text-white animate-pulse" />
        </div>
        <div className="absolute -bottom-2 -right-2 p-1.5 rounded-lg bg-gray-900 border border-gray-700 text-cyan-400">
          <Sparkles className="w-4 h-4" />
        </div>
      </div>

      <h2 className="text-2xl font-extrabold text-white tracking-tight">
        No Repository Connected
      </h2>
      <p className="mt-3 text-sm text-gray-400 leading-relaxed max-w-lg">
        The AI Digital Twin needs a live GitHub repository to construct its virtual project representation, calculate the repository health index, track activity velocity, and predict risks.
      </p>

      {/* Action Button */}
      <div className="mt-8">
        <button
          onClick={onConnectClick}
          className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-sm font-semibold text-white shadow-xl shadow-cyan-500/25 transition transform hover:-translate-y-0.5 flex items-center space-x-2.5 mx-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Connect GitHub Repository</span>
        </button>
      </div>

      {/* Feature Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-12 w-full text-left">
        <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
          <Activity className="w-4 h-4 text-cyan-400 mb-2" />
          <div className="font-semibold text-white">Live Telemetry</div>
          <div className="text-gray-400 mt-1">Extract real commits, active contributors, PRs, and issues directly via GitHub REST API.</div>
        </div>
        <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
          <ShieldCheck className="w-4 h-4 text-emerald-400 mb-2" />
          <div className="font-semibold text-white">Health Index</div>
          <div className="text-gray-400 mt-1">Transparent, deterministic scoring combining commit recency, PR velocity, and issue closure rates.</div>
        </div>
        <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
          <GitBranch className="w-4 h-4 text-purple-400 mb-2" />
          <div className="font-semibold text-white">Project Switching</div>
          <div className="text-gray-400 mt-1">Connect multiple repositories and switch between them with strict data isolation.</div>
        </div>
      </div>
    </div>
  );
};
