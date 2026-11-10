import React from 'react';
import { Server, Database, Github, ShieldCheck, AlertCircle } from 'lucide-react';
import { HealthResponse, Project } from '../../types';

interface SystemStatusBannerProps {
  health: HealthResponse | null;
  activeProject: Project | null;
  error?: string | null;
}

export const SystemStatusBanner: React.FC<SystemStatusBannerProps> = ({
  health,
  activeProject,
  error,
}) => {
  const isDbConnected = health?.database?.connected;
  const isGhConnected = health?.github?.connected;
  const isGhAuth = health?.github?.authenticated;

  const getResetCountdown = (): string | null => {
    if (health?.github?.reset_time_human) {
      return health.github.reset_time_human;
    }
    if (health?.github?.reset_timestamp) {
      const diffSec = Math.max(0, health.github.reset_timestamp - Math.floor(Date.now() / 1000));
      const mins = Math.floor(diffSec / 60);
      return mins > 0 ? `Resets in ${mins}m` : 'Resets in <1m';
    }
    return null;
  };
  const resetCountdown = getResetCountdown();

  return (
    <div className="rounded-xl border border-slate-200 dark:border-gray-800 bg-white dark:bg-[#101726]/80 p-5 shadow-sm dark:shadow-none backdrop-blur-md transition-colors">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Title & Live Status */}
        <div className="flex items-start space-x-3.5">
          <div className="p-2.5 rounded-lg bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30 text-cyan-600 dark:text-cyan-400 mt-0.5">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">Live Software Intelligence Core</h2>
              {activeProject?.status === 'syncing' ? (
                <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800 animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />
                  <span>Syncing: {activeProject.sync_stage || 'Collecting telemetry...'}</span>
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800">
                  Live Telemetry Active
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-gray-400 mt-0.5 font-mono">
              {activeProject ? (
                <>
                  Context: <span className="text-cyan-700 dark:text-cyan-300 font-semibold">{activeProject.full_name}</span> ({activeProject.visibility}) | Default: {activeProject.default_branch}
                </>
              ) : (
                'No repository currently connected. Connect a GitHub repository to activate Digital Twin telemetry.'
              )}
            </p>
          </div>
        </div>

        {/* Live Service Status Chips */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* FastAPI Core */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-gray-900/90 border border-slate-200 dark:border-gray-800 text-xs">
            <Server className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
            <div>
              <div className="text-[10px] text-slate-500 dark:text-gray-400 uppercase tracking-wider font-mono">FastAPI Core</div>
              <div className="font-semibold text-slate-900 dark:text-white flex items-center space-x-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${health ? 'bg-emerald-500 dark:bg-emerald-400' : 'bg-rose-500'}`} />
                <span>{health ? `v${health.version} (${health.environment})` : 'Offline'}</span>
              </div>
            </div>
          </div>

          {/* PostgreSQL Database */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-gray-900/90 border border-slate-200 dark:border-gray-800 text-xs">
            <Database className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <div>
              <div className="text-[10px] text-slate-500 dark:text-gray-400 uppercase tracking-wider font-mono">Database</div>
              <div className="font-semibold text-slate-900 dark:text-white flex items-center space-x-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${isDbConnected ? 'bg-emerald-500 dark:bg-emerald-400' : 'bg-amber-400'}`} />
                <span>
                  {isDbConnected
                    ? `${health?.database.status} (${health?.database.latency_ms}ms)`
                    : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>

          {/* GitHub REST API */}
          <div className="flex items-center space-x-2.5 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-gray-900/90 border border-slate-200 dark:border-gray-800 text-xs">
            <Github className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400 shrink-0" />
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="text-[10px] text-slate-500 dark:text-gray-400 uppercase tracking-wider font-mono">
                  GitHub API
                </span>
                <span
                  className={`px-1.5 py-0.2 rounded text-[9px] font-semibold uppercase tracking-wide border ${
                    isGhAuth
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/80 dark:text-emerald-300 dark:border-emerald-800'
                      : 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/80 dark:text-amber-300 dark:border-amber-800'
                  }`}
                >
                  {isGhAuth ? 'Authenticated' : 'Unauthenticated'}
                </span>
              </div>
              <div className="font-semibold text-slate-900 dark:text-white flex items-center space-x-1.5 font-mono">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isGhConnected ? 'bg-emerald-500 dark:bg-emerald-400' : 'bg-amber-400'
                  }`}
                />
                <span>
                  {(health?.github?.remaining_rate_limit ?? 60).toLocaleString()} /{' '}
                  {(health?.github?.limit ?? 60).toLocaleString()} quota
                </span>
                {resetCountdown && (
                  <span className="text-[10px] font-normal text-slate-400 dark:text-gray-500">
                    ({resetCountdown})
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-3.5 p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 text-rose-700 dark:text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500 dark:text-rose-400" />
          <span>Notice: {error}</span>
        </div>
      )}
    </div>
  );
};
