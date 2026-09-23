import React, { useEffect, useState, useCallback } from 'react';
import {
  Activity,
  Database,
  GitCommit,
  Users,
  AlertCircle,
  GitPullRequest,
  Tag,
  GitBranch,
  Layers,
  Shield,
  Zap,
  Clock,
  CheckCircle,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
  History,
  GitCompare,
  FolderTree,
  ArrowRight,
  TrendingUp,
  FileCode,
  Calendar,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import {
  Project,
  DigitalTwinFullState,
  DigitalTwinSnapshot,
  DigitalTwinChange,
  DigitalTwinEvent,
  DigitalTwinCompareResult,
  DigitalTwinSyncResult,
} from '../types';
import { apiService } from '../services/api';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
  onSync?: () => void;
  isSyncing?: boolean;
}

type TabMode = 'overview' | 'comparison' | 'changes' | 'timeline' | 'snapshots';

const STATUS_BADGES: Record<string, { bg: string; text: string; border: string; dot: string; label: string }> = {
  ACTIVE: {
    bg: 'bg-emerald-950/40',
    text: 'text-emerald-400',
    border: 'border-emerald-800/80',
    dot: 'bg-emerald-400',
    label: 'ACTIVE',
  },
  SYNCING: {
    bg: 'bg-cyan-950/40',
    text: 'text-cyan-400',
    border: 'border-cyan-800/80',
    dot: 'bg-cyan-400 animate-pulse',
    label: 'SYNCING',
  },
  OUTDATED: {
    bg: 'bg-amber-950/40',
    text: 'text-amber-400',
    border: 'border-amber-800/80',
    dot: 'bg-amber-400',
    label: 'OUTDATED',
  },
  ERROR: {
    bg: 'bg-red-950/40',
    text: 'text-red-400',
    border: 'border-red-800/80',
    dot: 'bg-red-400',
    label: 'ERROR',
  },
  NOT_INITIALIZED: {
    bg: 'bg-gray-900/60',
    text: 'text-gray-400',
    border: 'border-gray-800',
    dot: 'bg-gray-500',
    label: 'NOT INITIALIZED',
  },
  INITIALIZING: {
    bg: 'bg-purple-950/40',
    text: 'text-purple-400',
    border: 'border-purple-800/80',
    dot: 'bg-purple-400 animate-pulse',
    label: 'INITIALIZING',
  },
};

const CHANGE_TYPE_STYLES: Record<string, { bg: string; text: string }> = {
  CREATED: { bg: 'bg-emerald-950/60 border border-emerald-800/80', text: 'text-emerald-400' },
  UPDATED: { bg: 'bg-blue-950/60 border border-blue-800/80', text: 'text-blue-400' },
  STATE_CHANGED: { bg: 'bg-amber-950/60 border border-amber-800/80', text: 'text-amber-400' },
  DELETED: { bg: 'bg-red-950/60 border border-red-800/80', text: 'text-red-400' },
};

export const DigitalTwinPage: React.FC<Props> = ({
  activeProject,
  onOpenConnectModal,
}) => {
  const [fullState, setFullState] = useState<DigitalTwinFullState | null>(null);
  const [snapshots, setSnapshots] = useState<DigitalTwinSnapshot[]>([]);
  const [changes, setChanges] = useState<DigitalTwinChange[]>([]);
  const [events, setEvents] = useState<DigitalTwinEvent[]>([]);
  const [compareResult, setCompareResult] = useState<DigitalTwinCompareResult | null>(null);

  const [activeTab, setActiveTab] = useState<TabMode>('overview');
  const [selectedVFrom, setSelectedVFrom] = useState<number | undefined>();
  const [selectedVTo, setSelectedVTo] = useState<number | undefined>();

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load complete Digital Twin state for currently active project
  const loadTwinData = useCallback(async (projectId: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const [stateData, snaps, chgs, evts] = await Promise.all([
        apiService.getDigitalTwinFullState(projectId),
        apiService.getDigitalTwinSnapshots(projectId),
        apiService.getDigitalTwinChanges(projectId, 40),
        apiService.getDigitalTwinEvents(projectId, 40),
      ]);

      setFullState(stateData);
      setSnapshots(snaps);
      setChanges(chgs);
      setEvents(evts);

      // Set default comparison versions
      if (snaps.length >= 2) {
        setSelectedVFrom(snaps[1].version);
        setSelectedVTo(snaps[0].version);
      } else if (snaps.length === 1) {
        setSelectedVFrom(snaps[0].version);
        setSelectedVTo(snaps[0].version);
      }
    } catch (err: any) {
      console.error('Failed to load Digital Twin data:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load Digital Twin data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Isolate per activeProject.id
  useEffect(() => {
    if (!activeProject) {
      setFullState(null);
      setSnapshots([]);
      setChanges([]);
      setEvents([]);
      setIsLoading(false);
      return;
    }
    loadTwinData(activeProject.id);
  }, [activeProject?.id, loadTwinData]);

  // Handle version comparison trigger
  const runComparison = useCallback(async (projectId: number, from?: number, to?: number) => {
    try {
      const res = await apiService.compareDigitalTwinSnapshots(projectId, from, to);
      setCompareResult(res);
    } catch (err: any) {
      console.warn('Comparison failed:', err);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'comparison' && activeProject && selectedVFrom && selectedVTo) {
      runComparison(activeProject.id, selectedVFrom, selectedVTo);
    }
  }, [activeTab, activeProject, selectedVFrom, selectedVTo, runComparison]);

  // Handle manual twin sync
  const handleSync = async () => {
    if (!activeProject || isSyncing) return;
    setIsSyncing(true);
    setSyncFeedback(null);
    try {
      const syncRes: DigitalTwinSyncResult = await apiService.syncDigitalTwin(activeProject.id);
      setSyncFeedback(syncRes.message);
      await loadTwinData(activeProject.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Synchronization failed.');
    } finally {
      setIsSyncing(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center h-80 space-y-4 text-center border border-gray-800/80 bg-gray-950/40 rounded-2xl p-8">
        <Activity className="w-12 h-12 text-gray-600" />
        <div>
          <h2 className="text-xl font-bold text-gray-200">No Repository Connected</h2>
          <p className="text-sm text-gray-400 mt-1 max-w-md">
            Connect a GitHub repository to initialize its AI Digital Twin, observe its evolving state, and detect changes.
          </p>
        </div>
        <button
          onClick={onOpenConnectModal}
          className="px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-sm transition-all shadow-lg shadow-cyan-500/20"
        >
          Connect Repository
        </button>
      </div>
    );
  }

  if (isLoading && !fullState) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-28 bg-gray-900/60 border border-gray-800 rounded-2xl" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-900/60 border border-gray-800 rounded-xl" />
          ))}
        </div>
        <div className="h-72 bg-gray-900/60 border border-gray-800 rounded-2xl" />
      </div>
    );
  }

  if (error && !fullState) {
    return (
      <div className="p-6 rounded-2xl border border-red-900/60 bg-red-950/20 text-red-300 space-y-3">
        <div className="flex items-center space-x-2 font-bold text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>Digital Twin Core Error</span>
        </div>
        <p className="text-sm text-red-300/90">{error}</p>
        <button
          onClick={() => loadTwinData(activeProject.id)}
          className="px-4 py-2 bg-red-900/40 border border-red-700 text-red-200 rounded-xl text-xs font-semibold hover:bg-red-900/60"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const twin = fullState?.twin;
  const repo = fullState?.repository;
  const statusConfig = STATUS_BADGES[twin?.status || 'NOT_INITIALIZED'] || STATUS_BADGES.NOT_INITIALIZED;

  const stalenessDisplay = twin?.staleness_minutes !== undefined && twin?.staleness_minutes !== null
    ? twin.staleness_minutes < 60
      ? `${Math.round(twin.staleness_minutes)}m ago`
      : twin.staleness_minutes < 1440
        ? `${Math.round(twin.staleness_minutes / 60)}h ago`
        : `${Math.round(twin.staleness_minutes / 1440)}d ago`
    : 'Never synced';

  const fidelityColor = (twin?.fidelity_score ?? 0) >= 80 ? '#10b981' : (twin?.fidelity_score ?? 0) >= 50 ? '#06b6d4' : '#f59e0b';

  return (
    <div className="space-y-6">
      {/* ── Top Header & Lifecycle Banner ─────────────────────────────────── */}
      <div className="bg-[#0f172a]/90 border border-gray-800/90 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-3 flex-wrap gap-y-2">
              <h1 className="text-2xl font-black text-white tracking-tight">Digital Twin Core</h1>
              <div className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold border ${statusConfig.bg} ${statusConfig.border} ${statusConfig.text}`}>
                <span className={`w-2 h-2 rounded-full ${statusConfig.dot}`} />
                <span>{statusConfig.label}</span>
              </div>
              <div className="px-3 py-1 rounded-full text-xs font-bold bg-cyan-950/60 border border-cyan-800/80 text-cyan-300">
                Twin Version: v{twin?.current_version || 1}
              </div>
            </div>
            <div className="flex items-center space-x-3 text-xs text-gray-400">
              <span className="font-mono text-gray-300">{repo?.full_name}</span>
              <span>•</span>
              <span className="flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-gray-500" />
                <span>Last Synced: {stalenessDisplay}</span>
              </span>
              <span>•</span>
              <a
                href={repo?.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 text-cyan-400 hover:underline"
              >
                <span>GitHub Repository</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* Action Button */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handleSync}
              disabled={isSyncing}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-sm font-semibold shadow-lg shadow-cyan-900/30 disabled:opacity-50 transition-all cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>{isSyncing ? 'Synchronizing Twin...' : 'Sync Digital Twin'}</span>
            </button>
          </div>
        </div>

        {/* Sync Feedback Toast */}
        {syncFeedback && (
          <div className="mt-4 p-3 rounded-xl bg-cyan-950/40 border border-cyan-800/70 text-cyan-300 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-4 h-4 text-cyan-400 shrink-0" />
              <span>{syncFeedback}</span>
            </div>
            <button onClick={() => setSyncFeedback(null)} className="text-gray-400 hover:text-white">✕</button>
          </div>
        )}

        {twin?.status === 'OUTDATED' && (
          <div className="mt-4 p-3 rounded-xl bg-amber-950/40 border border-amber-800/70 text-amber-300 text-xs flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>Digital Twin state is outdated (over {twin.stale_threshold_minutes} minutes without synchronization). Press <strong>Sync Digital Twin</strong> to fetch latest changes.</span>
          </div>
        )}

        {twin?.error_message && (
          <div className="mt-4 p-3 rounded-xl bg-red-950/40 border border-red-800/70 text-red-300 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>Sync Error: {twin.error_message}</span>
          </div>
        )}
      </div>

      {/* ── Key Telemetry Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total Entities</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-white">
              {Object.values(fullState?.entity_counts || {}).reduce((a, b) => a + b, 0).toLocaleString()}
            </span>
            <span className="text-xs text-gray-500 font-medium">items</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">Commits, PRs, issues, contributors</p>
        </div>

        <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Twin Version</span>
            <History className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-purple-400">v{twin?.current_version || 1}</span>
            <span className="text-xs text-gray-500 font-medium">({snapshots.length} snapshots)</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">Immutable state checkpoints</p>
        </div>

        <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Twin Fidelity</span>
            <Shield className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black" style={{ color: fidelityColor }}>
              {twin?.fidelity_score ?? 0}%
            </span>
            <span className="text-xs text-gray-500 font-medium">fidelity</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">Representation completeness</p>
        </div>

        <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Health Index</span>
            <TrendingUp className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-cyan-300">{repo?.health_score?.toFixed(1) || '0.0'}</span>
            <span className="text-xs text-gray-500 font-medium">/100</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">Multi-pillar health velocity</p>
        </div>
      </div>

      {/* ── Navigation Tabs ──────────────────────────────────────────────── */}
      <div className="flex items-center space-x-2 border-b border-gray-800 pb-1 overflow-x-auto">
        {[
          { id: 'overview', label: 'Current State & Structure', icon: <Layers className="w-4 h-4" /> },
          { id: 'comparison', label: 'Version Comparison', icon: <GitCompare className="w-4 h-4" /> },
          { id: 'changes', label: `Detected Changes (${changes.length})`, icon: <Sparkles className="w-4 h-4" /> },
          { id: 'timeline', label: `Event Stream (${events.length})`, icon: <Activity className="w-4 h-4" /> },
          { id: 'snapshots', label: `Snapshot History (${snapshots.length})`, icon: <History className="w-4 h-4" /> },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as TabMode)}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
              activeTab === tab.id
                ? 'bg-cyan-950/70 border border-cyan-700/80 text-cyan-300 shadow-md shadow-cyan-950/50'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-transparent'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* ── TAB 1: Current State & Structure ──────────────────────────────── */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Visual Entity Hierarchy */}
          <div className="lg:col-span-2 bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <div className="flex items-center space-x-2">
                <FolderTree className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-white">Digital Twin Entity Model</h3>
              </div>
              <span className="text-xs font-medium text-gray-400">Phase 3 Normalized Domain</span>
            </div>

            {/* Tree Graph Representation */}
            <div className="p-4 rounded-xl bg-gray-950/70 border border-gray-800/80 space-y-4">
              <div className="flex items-center space-x-3 p-3 rounded-lg bg-gray-900/80 border border-cyan-800/40">
                <Database className="w-5 h-5 text-cyan-400" />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-white">{repo?.full_name}</span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300">
                      Branch: {fullState?.current_branch || repo?.default_branch || 'main'}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{repo?.description || 'No description provided.'}</p>
                </div>
              </div>

              {/* Child Nodes */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-4 border-l-2 border-cyan-900/60 ml-3">
                {[
                  { name: 'Commits', count: fullState?.entity_counts.commits || 0, icon: <GitCommit className="w-4 h-4 text-cyan-400" />, desc: 'Git commit history' },
                  { name: 'Contributors', count: fullState?.entity_counts.contributors || 0, icon: <Users className="w-4 h-4 text-violet-400" />, desc: 'Repository developers' },
                  { name: 'Issues', count: fullState?.entity_counts.issues || 0, icon: <AlertCircle className="w-4 h-4 text-amber-400" />, desc: 'Issue trackers' },
                  { name: 'Pull Requests', count: fullState?.entity_counts.pull_requests || 0, icon: <GitPullRequest className="w-4 h-4 text-emerald-400" />, desc: 'Code review pipelines' },
                  { name: 'Branches', count: fullState?.entity_counts.branches || 0, icon: <GitBranch className="w-4 h-4 text-pink-400" />, desc: 'Active branches' },
                  { name: 'Releases', count: fullState?.entity_counts.releases || 0, icon: <Tag className="w-4 h-4 text-blue-400" />, desc: 'Published tags' },
                  { name: 'Files & Tree', count: fullState?.entity_counts.files || 0, icon: <FileCode className="w-4 h-4 text-teal-400" />, desc: 'Indexed repository tree' },
                ].map((item, idx) => (
                  <div key={idx} className="flex items-center space-x-3 p-3 rounded-lg bg-gray-900/50 border border-gray-800/80 hover:border-gray-700 transition-colors">
                    {item.icon}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-gray-300">{item.name}</span>
                        <span className="text-xs font-mono font-bold text-white">{item.count.toLocaleString()}</span>
                      </div>
                      <p className="text-[11px] text-gray-500 truncate">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Latest Commit & Release Telemetry */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-gray-950/50 border border-gray-800/80">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center space-x-1.5 mb-2">
                  <GitCommit className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Latest Commit</span>
                </span>
                {fullState?.latest_commit ? (
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-white line-clamp-2">{fullState.latest_commit.message}</p>
                    <div className="flex items-center space-x-2 text-[11px] text-gray-400 pt-1">
                      <span className="font-mono text-cyan-400">{fullState.latest_commit.sha.substring(0, 7)}</span>
                      <span>•</span>
                      <span>{fullState.latest_commit.author}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-500">No commits recorded.</p>
                )}
              </div>

              <div className="p-4 rounded-xl bg-gray-950/50 border border-gray-800/80">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center space-x-1.5 mb-2">
                  <Tag className="w-3.5 h-3.5 text-blue-400" />
                  <span>Latest Release</span>
                </span>
                {fullState?.latest_release ? (
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-white">{fullState.latest_release.name || fullState.latest_release.tag}</p>
                    <div className="flex items-center space-x-2 text-[11px] text-gray-400 pt-1">
                      <span className="font-mono text-blue-400">{fullState.latest_release.tag}</span>
                      {fullState.latest_release.published_at && (
                        <>
                          <span>•</span>
                          <span>{new Date(fullState.latest_release.published_at).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-500">No published releases detected.</p>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Fidelity Pillars & Meta */}
          <div className="space-y-6">
            {/* Fidelity Pillars */}
            <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <Shield className="w-4 h-4 text-emerald-400" />
                  <span>Fidelity Pillars</span>
                </h3>
                <span className="text-xs font-mono font-bold" style={{ color: fidelityColor }}>
                  {twin?.fidelity_score ?? 0}%
                </span>
              </div>

              <div className="space-y-3">
                {fullState?.fidelity_components.map((comp, idx) => (
                  <div key={idx} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">{comp.name}</span>
                      <span className="font-mono font-semibold text-gray-200">{comp.synced}</span>
                    </div>
                    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${comp.active ? 'bg-cyan-500' : 'bg-gray-700'}`}
                        style={{ width: comp.active ? '100%' : '0%' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Repository Snapshot Summary */}
            <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-6 space-y-3">
              <h3 className="text-sm font-bold text-white border-b border-gray-800 pb-2">Repository Details</h3>
              <div className="space-y-2 text-xs">
                {[
                  { label: 'Default Branch', value: repo?.default_branch || 'main' },
                  { label: 'Primary Language', value: repo?.language || 'Not detected' },
                  { label: 'License', value: repo?.license || 'None' },
                  { label: 'GitHub Stars', value: repo?.stars?.toLocaleString() || '0' },
                  { label: 'GitHub Forks', value: repo?.forks?.toLocaleString() || '0' },
                  { label: 'Open Issues', value: repo?.open_issues?.toLocaleString() || '0' },
                  { label: 'Open PRs', value: repo?.open_prs?.toLocaleString() || '0' },
                ].map((row, i) => (
                  <div key={i} className="flex justify-between items-center py-1 border-b border-gray-800/40">
                    <span className="text-gray-400">{row.label}</span>
                    <span className="font-medium text-gray-200">{row.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: Version Comparison ─────────────────────────────────────── */}
      {activeTab === 'comparison' && (
        <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <GitCompare className="w-5 h-5 text-cyan-400" />
                <span>State Version Comparison</span>
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">Compare what changed between historical Digital Twin snapshots</p>
            </div>

            {/* Version Selectors */}
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-400 font-medium">Base:</span>
                <select
                  value={selectedVFrom || ''}
                  onChange={e => setSelectedVFrom(Number(e.target.value))}
                  className="bg-gray-900 border border-gray-700 text-gray-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
                >
                  {snapshots.map(s => (
                    <option key={s.id} value={s.version}>Snapshot v{s.version}</option>
                  ))}
                </select>
              </div>

              <ArrowRight className="w-4 h-4 text-gray-500" />

              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-400 font-medium">Target:</span>
                <select
                  value={selectedVTo || ''}
                  onChange={e => setSelectedVTo(Number(e.target.value))}
                  className="bg-gray-900 border border-gray-700 text-gray-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
                >
                  {snapshots.map(s => (
                    <option key={s.id} value={s.version}>Snapshot v{s.version}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Comparison Results */}
          {compareResult ? (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/60 text-center">
                  <div className="text-2xl font-bold text-emerald-400">+{compareResult.added.length}</div>
                  <div className="text-xs text-emerald-300/80 font-medium mt-0.5">Added Entities</div>
                </div>
                <div className="p-4 rounded-xl bg-blue-950/30 border border-blue-800/60 text-center">
                  <div className="text-2xl font-bold text-blue-400">{compareResult.updated.length}</div>
                  <div className="text-xs text-blue-300/80 font-medium mt-0.5">Updated Entities</div>
                </div>
                <div className="p-4 rounded-xl bg-red-950/30 border border-red-800/60 text-center">
                  <div className="text-2xl font-bold text-red-400">-{compareResult.removed.length}</div>
                  <div className="text-xs text-red-300/80 font-medium mt-0.5">Removed Entities</div>
                </div>
              </div>

              {/* Entity Count Changes Table */}
              {compareResult.summary.entity_count_diffs && (
                <div className="p-4 rounded-xl bg-gray-950/50 border border-gray-800/80 space-y-3">
                  <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Entity Delta Breakdown</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {Object.entries(compareResult.summary.entity_count_diffs).map(([key, diff]) => (
                      <div key={key} className="flex justify-between items-center p-2 rounded-lg bg-gray-900/60 text-xs">
                        <span className="text-gray-400 capitalize">{key}</span>
                        <span className={`font-mono font-bold ${diff > 0 ? 'text-emerald-400' : diff < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                          {diff > 0 ? `+${diff}` : diff}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Detailed Diffs */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Granular Change Records</h4>
                {compareResult.added.length === 0 && compareResult.updated.length === 0 && compareResult.removed.length === 0 ? (
                  <p className="text-xs text-gray-500 italic">No discrete entity differences recorded between these versions.</p>
                ) : (
                  <div className="space-y-2">
                    {[...compareResult.added, ...compareResult.updated, ...compareResult.removed].map((item, i) => (
                      <div key={i} className="flex items-center space-x-3 p-3 rounded-xl bg-gray-950/60 border border-gray-800/80 text-xs">
                        <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                          item.change_type === 'created' || item.change_type === 'added'
                            ? 'bg-emerald-950 border border-emerald-800 text-emerald-400'
                            : item.change_type === 'deleted' || item.change_type === 'removed'
                              ? 'bg-red-950 border border-red-800 text-red-400'
                              : 'bg-blue-950 border border-blue-800 text-blue-400'
                        }`}>
                          {item.change_type.toUpperCase()}
                        </span>
                        <span className="font-mono text-gray-400 uppercase text-[10px] w-20">{item.entity_type}</span>
                        <span className="text-gray-200 flex-1">{item.summary}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500 text-xs">
              Select two snapshot versions above to see a detailed comparison.
            </div>
          )}
        </div>
      )}

      {/* ── TAB 3: Detected Changes ──────────────────────────────────────── */}
      {activeTab === 'changes' && (
        <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-3">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-cyan-400" />
              <span>Change Detection Records</span>
            </h3>
            <span className="text-xs text-gray-400">Total detected: {changes.length}</span>
          </div>

          {changes.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-xs space-y-2">
              <CheckCircle className="w-8 h-8 mx-auto text-gray-600" />
              <p>No changes detected yet in the current snapshot.</p>
              <p className="text-gray-600">When the repository updates and you synchronize, change records will appear here.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {changes.map((chg) => {
                const style = CHANGE_TYPE_STYLES[chg.change_type] || { bg: 'bg-gray-900 border border-gray-800', text: 'text-gray-400' };
                return (
                  <div
                    key={chg.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl bg-gray-950/60 border border-gray-800/80 hover:border-gray-700 transition-colors gap-2"
                  >
                    <div className="flex items-center space-x-3">
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${style.bg} ${style.text}`}>
                        {chg.change_type}
                      </span>
                      <span className="font-mono text-[10px] text-gray-400 uppercase w-16">{chg.entity_type}</span>
                      <span className="text-xs font-medium text-gray-200">{chg.change_summary}</span>
                    </div>
                    <div className="text-[11px] text-gray-500 whitespace-nowrap pl-4 sm:pl-0">
                      {new Date(chg.detected_at).toLocaleString()}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 4: Event Timeline ────────────────────────────────────────── */}
      {activeTab === 'timeline' && (
        <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-3">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <Activity className="w-5 h-5 text-cyan-400" />
              <span>Digital Twin Event Stream</span>
            </h3>
            <span className="text-xs text-gray-400">Stream items: {events.length}</span>
          </div>

          {events.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-xs">No events logged for this Digital Twin yet.</div>
          ) : (
            <div className="relative pl-6 border-l-2 border-gray-800/80 space-y-4 ml-2">
              {events.map((ev) => (
                <div key={ev.id} className="relative">
                  {/* Dot */}
                  <span className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-cyan-500 border-2 border-gray-950" />

                  <div className="p-4 rounded-xl bg-gray-950/70 border border-gray-800/80 hover:border-gray-700 transition-colors space-y-1.5">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-white">{ev.title}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-gray-800 text-cyan-300">
                          {ev.event_type}
                        </span>
                      </div>
                      <span className="text-[11px] text-gray-500">
                        {new Date(ev.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {ev.description && (
                      <p className="text-xs text-gray-400">{ev.description}</p>
                    )}
                    {ev.actor_login && (
                      <div className="flex items-center space-x-2 pt-1 text-[11px] text-gray-500">
                        {ev.actor_avatar_url && (
                          <img src={ev.actor_avatar_url} alt={ev.actor_login} className="w-4 h-4 rounded-full" />
                        )}
                        <span>Actor: {ev.actor_login}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 5: Snapshot History ──────────────────────────────────────── */}
      {activeTab === 'snapshots' && (
        <div className="bg-[#111827]/90 border border-gray-800/80 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-3">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <History className="w-5 h-5 text-cyan-400" />
              <span>Digital Twin Snapshot Ledger</span>
            </h3>
            <span className="text-xs text-gray-400">{snapshots.length} versions recorded</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wider text-gray-400 bg-gray-900/60 border-b border-gray-800">
                <tr>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Source</th>
                  <th className="py-3 px-4">Changes</th>
                  <th className="py-3 px-4">Summary</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {snapshots.map((s, idx) => (
                  <tr key={s.id} className="hover:bg-gray-900/30 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-cyan-400">
                      v{s.version}
                    </td>
                    <td className="py-3.5 px-4 text-gray-300">
                      {new Date(s.created_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-gray-400 text-[11px]">
                      {s.source}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-white">
                      {s.change_count} change{s.change_count === 1 ? '' : 's'}
                    </td>
                    <td className="py-3.5 px-4 text-gray-300 max-w-xs truncate">
                      {s.summary || 'State snapshot checkpoint'}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        idx === 0
                          ? 'bg-emerald-950 border border-emerald-800 text-emerald-400'
                          : 'bg-gray-800 text-gray-400'
                      }`}>
                        {idx === 0 ? 'CURRENT' : 'HISTORICAL'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
