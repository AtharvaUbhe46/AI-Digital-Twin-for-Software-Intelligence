import React, { useState, useRef, useEffect } from 'react';
import {
  Database,
  Server,
  RefreshCw,
  Github,
  ChevronDown,
  Plus,
  Check,
  Radio,
} from 'lucide-react';
import { HealthResponse, Project } from '../../types';

interface HeaderProps {
  health: HealthResponse | null;
  projects: Project[];
  activeProject: Project | null;
  isLoading: boolean;
  isSyncing: boolean;
  onSync: () => void;
  onSelectProject: (projectId: number) => void;
  onOpenConnectModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  projects,
  activeProject,
  isLoading,
  isSyncing,
  onSync,
  onSelectProject,
  onOpenConnectModal,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isDbConnected = health?.database?.connected;
  const isGhConnected = health?.github?.connected;

  // Format last synced text
  const getLastSyncedText = () => {
    if (!activeProject?.last_synced_at) return 'Not synced';
    const last = new Date(activeProject.last_synced_at);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - last.getTime()) / 1000);
    if (diffSec < 60) return 'Synced just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `Synced ${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    return `Synced ${diffHrs}h ago`;
  };

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-16 border-b border-gray-800 bg-[#0E131F]/95 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30 select-none">
      {/* Dynamic Repository Selector */}
      <div className="flex items-center space-x-3" ref={dropdownRef}>
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center space-x-2.5 px-3 py-1.5 rounded-xl bg-gray-900/90 border border-gray-700/80 hover:border-gray-600 text-xs text-white transition focus:outline-none"
          >
            <div className="p-1 rounded-md bg-gray-800 text-gray-300">
              <Github className="w-3.5 h-3.5" />
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="text-gray-400">Repository:</span>
              <span className="font-semibold text-cyan-300 font-mono">
                {activeProject ? activeProject.full_name : 'No Repository Connected'}
              </span>
            </div>
            <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* Repository Switching Dropdown */}
          {dropdownOpen && (
            <div className="absolute left-0 mt-2 w-72 rounded-xl bg-[#0F172A] border border-gray-700 shadow-2xl py-2 z-50 animate-fadeIn">
              <div className="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-800">
                Connected Repositories ({projects.length})
              </div>

              <div className="max-h-56 overflow-y-auto py-1">
                {projects.length === 0 ? (
                  <div className="px-3 py-3 text-xs text-gray-400 text-center">
                    No repositories connected yet.
                  </div>
                ) : (
                  projects.map((proj) => {
                    const isSelected = activeProject?.id === proj.id;
                    return (
                      <button
                        key={proj.id}
                        onClick={() => {
                          onSelectProject(proj.id);
                          setDropdownOpen(false);
                        }}
                        className={`w-full px-3 py-2 flex items-center justify-between text-xs text-left transition ${
                          isSelected
                            ? 'bg-cyan-500/15 text-cyan-300 font-semibold'
                            : 'text-gray-300 hover:bg-gray-800/80'
                        }`}
                      >
                        <div className="flex items-center space-x-2 truncate">
                          <Radio className={`w-3 h-3 shrink-0 ${isSelected ? 'text-cyan-400' : 'text-gray-500'}`} />
                          <span className="truncate font-mono">{proj.full_name}</span>
                        </div>
                        {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400 shrink-0 ml-2" />}
                      </button>
                    );
                  })
                )}
              </div>

              <div className="pt-1.5 border-t border-gray-800 px-2">
                <button
                  onClick={() => {
                    setDropdownOpen(false);
                    onOpenConnectModal();
                  }}
                  className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 text-xs font-semibold border border-cyan-500/30 transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Connect Repository</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Digital Twin State Badge */}
        {activeProject ? (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-950 text-cyan-400 border border-cyan-800">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span>Digital Twin Active</span>
          </span>
        ) : (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-800/90 text-gray-400 border border-gray-700">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
            <span>Digital Twin Not Connected</span>
          </span>
        )}
      </div>

      {/* Connectivity & Health Status Monitors */}
      <div className="flex items-center space-x-3.5">
        {/* FastAPI Pill */}
        <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-gray-900 border border-gray-800 text-xs">
          <Server className="w-3 h-3 text-gray-400" />
          <span className="text-gray-400">API:</span>
          <span
            className={`w-2 h-2 rounded-full ${
              health ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' : 'bg-rose-500'
            }`}
          />
          <span className={health ? 'text-emerald-400 font-medium' : 'text-rose-400 font-medium'}>
            {health ? 'Online' : 'Offline'}
          </span>
        </div>

        {/* PostgreSQL Pill */}
        <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-gray-900 border border-gray-800 text-xs">
          <Database className="w-3 h-3 text-gray-400" />
          <span className="text-gray-400">DB:</span>
          <span
            className={`w-2 h-2 rounded-full ${
              isDbConnected ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' : 'bg-amber-400'
            }`}
          />
          <span className={isDbConnected ? 'text-emerald-400 font-medium' : 'text-amber-400 font-medium'}>
            {isDbConnected ? `${health?.database?.latency_ms ?? 0}ms` : 'Disconnected'}
          </span>
        </div>

        {/* GitHub API Pill */}
        <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-gray-900 border border-gray-800 text-xs">
          <Github className="w-3 h-3 text-gray-400" />
          <span className="text-gray-400">GitHub:</span>
          <span
            className={`w-2 h-2 rounded-full ${
              isGhConnected ? 'bg-emerald-400' : 'bg-amber-400'
            }`}
          />
          <span className="text-gray-200 font-mono text-[11px]">
            {health?.github?.remaining_rate_limit ?? 60}/{health?.github?.limit ?? 60}
          </span>
        </div>

        {/* Last Synced indicator */}
        {activeProject && (
          <span className="hidden lg:inline-block text-[11px] text-gray-400 font-mono">
            {getLastSyncedText()}
          </span>
        )}

        {/* Real Sync / Refresh Button */}
        {activeProject ? (
          <button
            onClick={onSync}
            disabled={isSyncing || isLoading}
            title="Perform live GitHub re-synchronization"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-cyan-300 hover:text-white border border-gray-700 text-xs font-semibold transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>{isSyncing ? 'Syncing...' : 'Sync'}</span>
          </button>
        ) : (
          <button
            onClick={onOpenConnectModal}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-500/20 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Connect Repo</span>
          </button>
        )}
      </div>
    </header>
  );
};
