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
  Sparkles,
  Info,
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
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    text: 'text-emerald-700 dark:text-emerald-400',
    border: 'border-emerald-200 dark:border-emerald-800/80',
    dot: 'bg-emerald-500 dark:bg-emerald-400',
    label: 'ACTIVE',
  },
  SUCCESS: {
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    text: 'text-emerald-700 dark:text-emerald-400',
    border: 'border-emerald-200 dark:border-emerald-800/80',
    dot: 'bg-emerald-500 dark:bg-emerald-400',
    label: 'SUCCESS',
  },
  IDLE: {
    bg: 'bg-slate-100 dark:bg-gray-800/60',
    text: 'text-slate-700 dark:text-gray-300',
    border: 'border-slate-200 dark:border-gray-700',
    dot: 'bg-slate-500 dark:bg-gray-400',
    label: 'IDLE',
  },
  SYNCING: {
    bg: 'bg-cyan-50 dark:bg-cyan-950/40',
    text: 'text-cyan-700 dark:text-cyan-400',
    border: 'border-cyan-200 dark:border-cyan-800/80',
    dot: 'bg-cyan-500 dark:bg-cyan-400 animate-pulse',
    label: 'SYNCING',
  },
  OUTDATED: {
    bg: 'bg-amber-50 dark:bg-amber-950/40',
    text: 'text-amber-700 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800/80',
    dot: 'bg-amber-500 dark:bg-amber-400',
    label: 'OUTDATED',
  },
  PARTIAL_SUCCESS: {
    bg: 'bg-amber-50 dark:bg-amber-950/40',
    text: 'text-amber-700 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800/80',
    dot: 'bg-amber-500 dark:bg-amber-400',
    label: 'PARTIAL SUCCESS',
  },
  FAILED: {
    bg: 'bg-red-50 dark:bg-red-950/40',
    text: 'text-red-700 dark:text-red-400',
    border: 'border-red-200 dark:border-red-800/80',
    dot: 'bg-red-500 dark:bg-red-400',
    label: 'FAILED',
  },
  ERROR: {
    bg: 'bg-red-50 dark:bg-red-950/40',
    text: 'text-red-700 dark:text-red-400',
    border: 'border-red-200 dark:border-red-800/80',
    dot: 'bg-red-500 dark:bg-red-400',
    label: 'FAILED',
  },
  NOT_INITIALIZED: {
    bg: 'bg-slate-100 dark:bg-gray-900/60',
    text: 'text-slate-600 dark:text-gray-400',
    border: 'border-slate-200 dark:border-gray-800',
    dot: 'bg-slate-400 dark:bg-gray-500',
    label: 'NOT INITIALIZED',
  },
  INITIALIZING: {
    bg: 'bg-purple-50 dark:bg-purple-950/40',
    text: 'text-purple-700 dark:text-purple-400',
    border: 'border-purple-200 dark:border-purple-800/80',
    dot: 'bg-purple-500 dark:bg-purple-400 animate-pulse',
    label: 'INITIALIZING',
  },
};

const CHANGE_TYPE_STYLES: Record<string, { bg: string; text: string }> = {
  CREATED: { bg: 'bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800/80', text: 'text-emerald-700 dark:text-emerald-400' },
  UPDATED: { bg: 'bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800/80', text: 'text-blue-700 dark:text-blue-400' },
  STATE_CHANGED: { bg: 'bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800/80', text: 'text-amber-700 dark:text-amber-400' },
  DELETED: { bg: 'bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800/80', text: 'text-red-700 dark:text-red-400' },
};

/** Accessible Info Tooltip component */
const InfoTooltip: React.FC<{ text: string }> = ({ text }) => {
  const [show, setShow] = useState(false);
  return (
    <div className="relative inline-flex items-center ml-1.5 align-middle">
      <button
        type="button"
        onClick={() => setShow(prev => !prev)}
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        aria-label="Information"
        className="text-slate-400 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors focus:outline-none cursor-pointer"
      >
        <Info className="w-3.5 h-3.5" />
      </button>
      {show && (
        <div className="absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-slate-900/95 dark:bg-gray-900/95 backdrop-blur-md text-white text-[11px] leading-relaxed rounded-xl shadow-xl border border-slate-700/80 pointer-events-none transition-all">
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900 dark:border-t-gray-900" />
        </div>
      )}
    </div>
  );
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
        apiService.getDigitalTwinChanges(projectId, 50),
        apiService.getDigitalTwinEvents(projectId, 50),
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
    setError(null);
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
      <div className="flex flex-col items-center justify-center h-80 space-y-4 text-center border border-slate-200 dark:border-gray-800/80 bg-white dark:bg-gray-950/40 rounded-2xl p-8 shadow-sm">
        <Activity className="w-12 h-12 text-slate-400 dark:text-gray-600" />
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-gray-200">No Repository Connected</h2>
          <p className="text-sm text-slate-500 dark:text-gray-400 mt-1 max-w-md">
            Connect a GitHub repository to initialize its AI Digital Twin, observe its evolving state, and detect changes.
          </p>
        </div>
        <button
          onClick={onOpenConnectModal}
          className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 dark:bg-cyan-500 dark:hover:bg-cyan-400 text-white dark:text-gray-950 font-semibold text-sm transition-all shadow-lg shadow-cyan-500/20 cursor-pointer"
        >
          Connect Repository
        </button>
      </div>
    );
  }

  if (isLoading && !fullState) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-28 bg-slate-200 dark:bg-gray-900/60 border border-slate-300 dark:border-gray-800 rounded-2xl" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-slate-200 dark:bg-gray-900/60 border border-slate-300 dark:border-gray-800 rounded-xl" />
          ))}
        </div>
        <div className="h-72 bg-slate-200 dark:bg-gray-900/60 border border-slate-300 dark:border-gray-800 rounded-2xl" />
      </div>
    );
  }

  if (error && !fullState) {
    return (
      <div className="p-6 rounded-2xl border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-300 space-y-3">
        <div className="flex items-center space-x-2 font-bold text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>Digital Twin Core Error</span>
        </div>
        <p className="text-sm text-red-600/90 dark:text-red-300/90">{error}</p>
        <button
          onClick={() => loadTwinData(activeProject.id)}
          className="px-4 py-2 bg-red-100 dark:bg-red-900/40 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-200 rounded-xl text-xs font-semibold hover:bg-red-200 dark:hover:bg-red-900/60 cursor-pointer"
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

  // Data Coverage calculation
  const dataCoverageScore = fullState?.data_coverage !== undefined && fullState?.data_coverage !== null
    ? fullState.data_coverage
    : (twin?.fidelity_score ?? null);

  const coverageColor = dataCoverageScore !== null
    ? dataCoverageScore >= 80 ? '#10b981' : dataCoverageScore >= 50 ? '#06b6d4' : '#f59e0b'
    : '#94a3b8';

  // Digital Twin Health Score
  const twinHealthScore = fullState?.health_score !== undefined && fullState?.health_score !== null
    ? fullState.health_score
    : (twin?.health_score ?? null);

  const healthColor = twinHealthScore !== null
    ? twinHealthScore >= 80 ? '#10b981' : twinHealthScore >= 50 ? '#06b6d4' : '#f59e0b'
    : '#94a3b8';

  const totalCollectedRecords = Object.values(fullState?.entity_counts || {}).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      {/* ── Top Header & Lifecycle Banner ─────────────────────────────────── */}
      <div className="bg-white dark:bg-[#0f172a]/90 border border-slate-200 dark:border-gray-800/90 rounded-2xl p-6 shadow-sm dark:shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-3 flex-wrap gap-y-2">
              <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">Digital Twin Core</h1>
              <div className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold border ${statusConfig.bg} ${statusConfig.border} ${statusConfig.text}`}>
                <span className={`w-2 h-2 rounded-full ${statusConfig.dot}`} />
                <span>{statusConfig.label}</span>
              </div>
              <div className="px-3 py-1 rounded-full text-xs font-bold bg-cyan-50 dark:bg-cyan-950/60 border border-cyan-200 dark:border-cyan-800/80 text-cyan-700 dark:text-cyan-300">
                Digital Twin Version: v{twin?.current_version || 1}
              </div>
            </div>
            <div className="flex items-center space-x-3 text-xs text-slate-500 dark:text-gray-400">
              <span className="font-mono text-slate-700 dark:text-gray-300">{repo?.full_name}</span>
              <span>•</span>
              <span className="flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-slate-400 dark:text-gray-500" />
                <span>Last Synced: {stalenessDisplay}</span>
              </span>
              <span>•</span>
              <a
                href={repo?.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 text-cyan-600 dark:text-cyan-400 hover:underline"
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
              <span>{isSyncing ? 'Synchronizing Digital Twin...' : 'Sync Digital Twin'}</span>
            </button>
          </div>
        </div>

        {/* Sync Feedback Toast */}
        {syncFeedback && (
          <div className="mt-4 p-3 rounded-xl bg-cyan-50 dark:bg-cyan-950/40 border border-cyan-200 dark:border-cyan-800/70 text-cyan-700 dark:text-cyan-300 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-4 h-4 text-cyan-600 dark:text-cyan-400 shrink-0" />
              <span>{syncFeedback}</span>
            </div>
            <button onClick={() => setSyncFeedback(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-white cursor-pointer">✕</button>
          </div>
        )}

        {twin?.status === 'OUTDATED' && (
          <div className="mt-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/70 text-amber-700 dark:text-amber-300 text-xs flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-500 dark:text-amber-400 shrink-0" />
            <span>Digital Twin state is outdated (over {twin.stale_threshold_minutes} minutes without synchronization). Click <strong>Sync Digital Twin</strong> to pull latest changes.</span>
          </div>
        )}

        {twin?.status === 'PARTIAL_SUCCESS' && (
          <div className="mt-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/70 text-amber-700 dark:text-amber-300 text-xs flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-500 dark:text-amber-400 shrink-0" />
            <span>Partial synchronization completed: some categories were successfully synced while others returned warnings. Prior data has been safely preserved.</span>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/70 text-red-700 dark:text-red-300 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-500 dark:text-red-400 shrink-0" />
            <span>Sync Error: {error}</span>
          </div>
        )}
      </div>

      {/* ── Key Telemetry Cards with Information Tooltips ─────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Metric 1: Collected Repository Records */}
        <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-5 relative overflow-hidden shadow-sm dark:shadow-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <span className="text-xs font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider">Collected Repository Records</span>
              <InfoTooltip text="The total number of repository records currently collected and stored in the Digital Twin, including supported commits, contributors, issues, pull requests, branches, and other entities." />
            </div>
            <Database className="w-4 h-4 text-cyan-600 dark:text-cyan-400 shrink-0" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-slate-900 dark:text-white">
              {totalCollectedRecords.toLocaleString()}
            </span>
            <span className="text-xs text-slate-500 dark:text-gray-500 font-medium">records</span>
          </div>
          <p className="text-xs text-slate-500 dark:text-gray-400 mt-1">Commits, PRs, issues, contributors</p>
        </div>

        {/* Metric 2: Digital Twin Version */}
        <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-5 relative overflow-hidden shadow-sm dark:shadow-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <span className="text-xs font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider">Digital Twin Version</span>
              <InfoTooltip text="The current version of the digital representation of your GitHub repository. A new version is created when a valid new snapshot is successfully recorded." />
            </div>
            <History className="w-4 h-4 text-purple-600 dark:text-purple-400 shrink-0" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-purple-600 dark:text-purple-400">v{twin?.current_version || 1}</span>
            <span className="text-xs text-slate-500 dark:text-gray-500 font-medium">({snapshots.length} snapshot{snapshots.length === 1 ? '' : 's'})</span>
          </div>
          <p className="text-xs text-slate-500 dark:text-gray-400 mt-1">Immutable state checkpoints</p>
        </div>

        {/* Metric 3: Data Coverage */}
        <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-5 relative overflow-hidden shadow-sm dark:shadow-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <span className="text-xs font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider">Data Coverage</span>
              <InfoTooltip text="Indicates how much of the expected repository data has been successfully collected and validated. This measures data completeness, not software quality." />
            </div>
            <Shield className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black" style={{ color: coverageColor }}>
              {dataCoverageScore !== null ? `${dataCoverageScore}%` : 'Unavailable'}
            </span>
            <span className="text-xs text-slate-500 dark:text-gray-500 font-medium">coverage</span>
          </div>
          <p className="text-xs text-slate-500 dark:text-gray-400 mt-1">Validated entity completeness</p>
        </div>

        {/* Metric 4: Digital Twin Health Score */}
        <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-5 relative overflow-hidden shadow-sm dark:shadow-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <span className="text-xs font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider">Digital Twin Health Score</span>
              <InfoTooltip text="An indicator of the operational health and reliability of the Digital Twin, based on synchronization status, data consistency, snapshot availability, and other documented factors. It is not the same as source-code quality." />
            </div>
            <TrendingUp className="w-4 h-4 text-cyan-600 dark:text-cyan-400 shrink-0" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black" style={{ color: healthColor }}>
              {twinHealthScore !== null ? twinHealthScore.toFixed(1) : 'Unavailable'}
            </span>
            {twinHealthScore !== null && <span className="text-xs text-slate-500 dark:text-gray-500 font-medium">/100</span>}
          </div>
          <p className="text-xs text-slate-500 dark:text-gray-400 mt-1">Operational sync health</p>
        </div>
      </div>

      {/* ── Navigation Tabs ──────────────────────────────────────────────── */}
      <div className="flex items-center space-x-2 border-b border-slate-200 dark:border-gray-800 pb-1 overflow-x-auto">
        {[
          { id: 'overview', label: 'Current State & Structure', icon: <Layers className="w-4 h-4" /> },
          { id: 'comparison', label: 'Compare Snapshots', icon: <GitCompare className="w-4 h-4" /> },
          { id: 'changes', label: `Repository Changes (${changes.length})`, icon: <Sparkles className="w-4 h-4" /> },
          { id: 'timeline', label: `Activity Timeline (${events.length})`, icon: <Activity className="w-4 h-4" /> },
          { id: 'snapshots', label: `Historical Snapshots (${snapshots.length})`, icon: <History className="w-4 h-4" /> },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as TabMode)}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
              activeTab === tab.id
                ? 'bg-cyan-50 dark:bg-cyan-950/70 border border-cyan-200 dark:border-cyan-700/80 text-cyan-700 dark:text-cyan-300 shadow-sm'
                : 'text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-gray-200 hover:bg-slate-100 dark:hover:bg-gray-800/50 border border-transparent'
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
          <div className="lg:col-span-2 bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-6 space-y-6 shadow-sm dark:shadow-md">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-gray-800 pb-4">
              <div className="flex items-center space-x-2">
                <FolderTree className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
                <h3 className="text-base font-bold text-slate-900 dark:text-white">Collected Repository Records</h3>
              </div>
              <span className="text-xs font-medium text-slate-500 dark:text-gray-400">Structured Entity Hierarchy</span>
            </div>

            {/* Tree Graph Representation */}
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-gray-950/70 border border-slate-200 dark:border-gray-800/80 space-y-4">
              <div className="flex items-center space-x-3 p-3 rounded-lg bg-white dark:bg-gray-900/80 border border-cyan-200 dark:border-cyan-800/40 shadow-xs">
                <Database className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-slate-900 dark:text-white">{repo?.full_name}</span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-50 dark:bg-cyan-950 border border-cyan-200 dark:border-cyan-800 text-cyan-700 dark:text-cyan-300">
                      Branch: {fullState?.current_branch || repo?.default_branch || 'main'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-gray-400 mt-0.5">{repo?.description || 'No description provided.'}</p>
                </div>
              </div>

              {/* Child Nodes */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-4 border-l-2 border-cyan-500/40 dark:border-cyan-900/60 ml-3">
                {[
                  { name: 'Commits', count: fullState?.entity_counts.commits || 0, icon: <GitCommit className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />, desc: 'Git commit records' },
                  { name: 'Contributors', count: fullState?.entity_counts.contributors || 0, icon: <Users className="w-4 h-4 text-violet-600 dark:text-violet-400" />, desc: 'Repository developers' },
                  { name: 'Issues', count: fullState?.entity_counts.issues || 0, icon: <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />, desc: 'Issue trackers' },
                  { name: 'Pull Requests', count: fullState?.entity_counts.pull_requests || 0, icon: <GitPullRequest className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />, desc: 'Code review pipelines' },
                  { name: 'Branches', count: fullState?.entity_counts.branches || 0, icon: <GitBranch className="w-4 h-4 text-pink-600 dark:text-pink-400" />, desc: 'Active branches' },
                  { name: 'Releases', count: fullState?.entity_counts.releases || 0, icon: <Tag className="w-4 h-4 text-blue-600 dark:text-blue-400" />, desc: 'Published tags' },
                  { name: 'Files & Tree', count: fullState?.entity_counts.files || 0, icon: <FileCode className="w-4 h-4 text-teal-600 dark:text-teal-400" />, desc: 'Indexed repository tree' },
                ].map((item, idx) => (
                  <div key={idx} className="flex items-center space-x-3 p-3 rounded-lg bg-white dark:bg-gray-900/50 border border-slate-200 dark:border-gray-800/80 hover:border-slate-300 dark:hover:border-gray-700 transition-colors">
                    {item.icon}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-700 dark:text-gray-300">{item.name}</span>
                        <span className="text-xs font-mono font-bold text-slate-900 dark:text-white">{item.count.toLocaleString()}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-gray-500 truncate">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Latest Commit & Release Telemetry */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800/80">
                <span className="text-xs font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider flex items-center space-x-1.5 mb-2">
                  <GitCommit className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                  <span>Latest Commit</span>
                </span>
                {fullState?.latest_commit ? (
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-slate-900 dark:text-white line-clamp-2">{fullState.latest_commit.message}</p>
                    <div className="flex items-center space-x-2 text-[11px] text-slate-500 dark:text-gray-400 pt-1">
                      <span className="font-mono text-cyan-600 dark:text-cyan-400">{fullState.latest_commit.sha.substring(0, 7)}</span>
                      <span>•</span>
                      <span>{fullState.latest_commit.author}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 dark:text-gray-500">No commits recorded.</p>
                )}
              </div>

              <div className="p-4 rounded-xl bg-slate-50 dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800/80">
                <span className="text-xs font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider flex items-center space-x-1.5 mb-2">
                  <Tag className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                  <span>Latest Release</span>
                </span>
                {fullState?.latest_release ? (
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-slate-900 dark:text-white">{fullState.latest_release.name || fullState.latest_release.tag}</p>
                    <div className="flex items-center space-x-2 text-[11px] text-slate-500 dark:text-gray-400 pt-1">
                      <span className="font-mono text-blue-600 dark:text-blue-400">{fullState.latest_release.tag}</span>
                      {fullState.latest_release.published_at && (
                        <>
                          <span>•</span>
                          <span>{new Date(fullState.latest_release.published_at).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 dark:text-gray-500">No published releases detected.</p>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Data Coverage & Health Score Details */}
          <div className="space-y-6">
            {/* Data Coverage Breakdown */}
            <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-6 space-y-4 shadow-sm dark:shadow-md">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-gray-800 pb-3">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center space-x-2">
                  <Shield className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <span>Data Coverage</span>
                  <InfoTooltip text="Indicates how much of the expected repository data has been successfully collected and validated. This measures data completeness, not software quality." />
                </h3>
                <span className="text-xs font-mono font-bold" style={{ color: coverageColor }}>
                  {dataCoverageScore !== null ? `${dataCoverageScore}%` : 'Unavailable'}
                </span>
              </div>

              <p className="text-[11px] text-slate-500 dark:text-gray-400">
                Formula: (Validated Categories / Total Applicable Categories) × 100
              </p>

              <div className="space-y-3">
                {(fullState?.data_coverage_components || fullState?.fidelity_components || []).map((comp: any, idx: number) => {
                  const isValid = comp.validated ?? comp.active;
                  const statusLabel = comp.status || (comp.active ? 'COLLECTED' : 'EMPTY');
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-600 dark:text-gray-400 flex items-center space-x-1.5">
                          <span>{comp.name}</span>
                        </span>
                        <div className="flex items-center space-x-2">
                          <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                            statusLabel === 'COLLECTED'
                              ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400'
                              : statusLabel === 'EMPTY'
                                ? 'bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-gray-400'
                                : 'bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400'
                          }`}>
                            {statusLabel}
                          </span>
                          <span className="font-mono font-semibold text-slate-800 dark:text-gray-200 text-[11px]">{comp.synced}</span>
                        </div>
                      </div>
                      <div className="h-1.5 bg-slate-100 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${
                            isValid ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-gray-700'
                          }`}
                          style={{ width: isValid ? '100%' : '0%' }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Digital Twin Health Score Breakdown */}
            <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-6 space-y-4 shadow-sm dark:shadow-md">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-gray-800 pb-3">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center space-x-2">
                  <TrendingUp className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                  <span>Digital Twin Health Score</span>
                  <InfoTooltip text="An indicator of the operational health and reliability of the Digital Twin, based on synchronization status, data consistency, snapshot availability, and other documented factors. It is not the same as source-code quality." />
                </h3>
                <span className="text-xs font-mono font-bold" style={{ color: healthColor }}>
                  {twinHealthScore !== null ? `${twinHealthScore.toFixed(1)}/100` : 'Unavailable'}
                </span>
              </div>

              {fullState?.health_breakdown?.components ? (
                <div className="space-y-3">
                  <div className="text-[11px] text-slate-500 dark:text-gray-400">
                    Classification: <strong className="text-slate-700 dark:text-gray-200">{fullState.health_breakdown.classification}</strong>
                  </div>
                  {fullState.health_breakdown.components.map((c, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-slate-50 dark:bg-gray-950/60 border border-slate-200 dark:border-gray-800/60 space-y-1 text-xs">
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-slate-800 dark:text-gray-200">{c.name}</span>
                        <span className="font-mono font-bold text-cyan-600 dark:text-cyan-400">{c.score} / {c.max_score}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-gray-400">{c.detail}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 dark:text-gray-500">Health calculation available after successful synchronization.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: Compare Snapshots ─────────────────────────────────────── */}
      {activeTab === 'comparison' && (
        <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-6 space-y-6 shadow-sm dark:shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-gray-800 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center space-x-2">
                <GitCompare className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
                <span>Compare Snapshots</span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-gray-400 mt-0.5">Compare actual repository states recorded between two historical snapshots.</p>
            </div>

            {/* Version Selectors */}
            {snapshots.length >= 2 ? (
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-slate-500 dark:text-gray-400 font-medium">Base:</span>
                  <select
                    value={selectedVFrom || ''}
                    onChange={e => setSelectedVFrom(Number(e.target.value))}
                    className="bg-slate-50 dark:bg-gray-900 border border-slate-300 dark:border-gray-700 text-slate-800 dark:text-gray-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
                  >
                    {snapshots.map(s => (
                      <option key={s.id} value={s.version}>Snapshot v{s.version} ({new Date(s.created_at).toLocaleDateString()})</option>
                    ))}
                  </select>
                </div>

                <ArrowRight className="w-4 h-4 text-slate-400 dark:text-gray-500" />

                <div className="flex items-center space-x-2">
                  <span className="text-xs text-slate-500 dark:text-gray-400 font-medium">Target:</span>
                  <select
                    value={selectedVTo || ''}
                    onChange={e => setSelectedVTo(Number(e.target.value))}
                    className="bg-slate-50 dark:bg-gray-900 border border-slate-300 dark:border-gray-700 text-slate-800 dark:text-gray-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
                  >
                    {snapshots.map(s => (
                      <option key={s.id} value={s.version}>Snapshot v{s.version} ({new Date(s.created_at).toLocaleDateString()})</option>
                    ))}
                  </select>
                </div>
              </div>
            ) : null}
          </div>

          {/* Comparison Results */}
          {snapshots.length < 2 ? (
            <div className="p-8 text-center text-slate-500 dark:text-gray-400 text-xs space-y-2">
              <History className="w-8 h-8 mx-auto text-slate-300 dark:text-gray-600" />
              <p className="font-semibold text-slate-700 dark:text-gray-300">At least two historical snapshots are required to compare states.</p>
              <p>Currently, {snapshots.length} snapshot is recorded. When repository changes occur and you synchronize, a new snapshot version will be created enabling comparison.</p>
            </div>
          ) : compareResult ? (
            <div className="space-y-6">
              {/* Snapshot Metadata Banner */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-gray-950/60 border border-slate-200 dark:border-gray-800 text-xs space-y-1">
                  <span className="font-bold text-slate-800 dark:text-gray-200">Base Snapshot: v{compareResult.v_from}</span>
                  <p className="text-slate-500 dark:text-gray-400">
                    Recorded: {compareResult.older_snapshot?.created_at ? new Date(compareResult.older_snapshot.created_at).toLocaleString() : 'N/A'}
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-gray-950/60 border border-slate-200 dark:border-gray-800 text-xs space-y-1">
                  <span className="font-bold text-slate-800 dark:text-gray-200">Target Snapshot: v{compareResult.v_to}</span>
                  <p className="text-slate-500 dark:text-gray-400">
                    Recorded: {compareResult.newer_snapshot?.created_at ? new Date(compareResult.newer_snapshot.created_at).toLocaleString() : 'N/A'}
                  </p>
                </div>
              </div>

              {/* Summary Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 text-center">
                  <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">+{compareResult.added.length}</div>
                  <div className="text-xs text-emerald-700 dark:text-emerald-300/80 font-medium mt-0.5">Added Entities</div>
                </div>
                <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800/60 text-center">
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{compareResult.updated.length}</div>
                  <div className="text-xs text-blue-700 dark:text-blue-300/80 font-medium mt-0.5">Modified Entities</div>
                </div>
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800/60 text-center">
                  <div className="text-2xl font-bold text-red-600 dark:text-red-400">-{compareResult.removed.length}</div>
                  <div className="text-xs text-red-700 dark:text-red-300/80 font-medium mt-0.5">Removed Entities</div>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800 text-center">
                  <div className="text-2xl font-bold text-slate-700 dark:text-gray-300">{compareResult.unchanged_count ?? compareResult.summary.unchanged_count ?? 0}</div>
                  <div className="text-xs text-slate-500 dark:text-gray-400 font-medium mt-0.5">Unchanged Entities</div>
                </div>
              </div>

              {/* Entity Delta Breakdown */}
              {compareResult.summary.entity_count_diffs && (
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800/80 space-y-3">
                  <h4 className="text-xs font-semibold text-slate-700 dark:text-gray-300 uppercase tracking-wider">Entity Delta Breakdown</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {Object.entries(compareResult.summary.entity_count_diffs).map(([key, diff]) => (
                      <div key={key} className="flex justify-between items-center p-2 rounded-lg bg-white dark:bg-gray-900/60 text-xs shadow-2xs">
                        <span className="text-slate-600 dark:text-gray-400 capitalize">{key}</span>
                        <span className={`font-mono font-bold ${diff > 0 ? 'text-emerald-600 dark:text-emerald-400' : diff < 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-400 dark:text-gray-500'}`}>
                          {diff > 0 ? `+${diff}` : diff}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Detailed Diffs */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-slate-700 dark:text-gray-300 uppercase tracking-wider">Granular Change Records</h4>
                {compareResult.added.length === 0 && compareResult.updated.length === 0 && compareResult.removed.length === 0 ? (
                  <p className="text-xs text-slate-400 dark:text-gray-500 italic">No discrete entity differences recorded between these versions.</p>
                ) : (
                  <div className="space-y-2">
                    {[...compareResult.added, ...compareResult.updated, ...compareResult.removed].map((item, i) => (
                      <div key={i} className="flex items-center space-x-3 p-3 rounded-xl bg-slate-50 dark:bg-gray-950/60 border border-slate-200 dark:border-gray-800/80 text-xs">
                        <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                          item.change_type === 'created' || item.change_type === 'added'
                            ? 'bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400'
                            : item.change_type === 'deleted' || item.change_type === 'removed'
                              ? 'bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400'
                              : 'bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400'
                        }`}>
                          {item.change_type.toUpperCase()}
                        </span>
                        <span className="font-mono text-slate-500 dark:text-gray-400 uppercase text-[10px] w-20">{item.entity_type}</span>
                        <span className="text-slate-800 dark:text-gray-200 flex-1">{item.summary}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-400 dark:text-gray-500 text-xs">
              Select two snapshot versions above to compare states.
            </div>
          )}
        </div>
      )}

      {/* ── TAB 3: Repository Changes ──────────────────────────────────────── */}
      {activeTab === 'changes' && (
        <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-6 space-y-4 shadow-sm dark:shadow-md">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-gray-800 pb-3">
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              <span>Repository Changes</span>
            </h3>
            <span className="text-xs text-slate-500 dark:text-gray-400">Total detected: {changes.length}</span>
          </div>

          {changes.length === 0 ? (
            <div className="p-8 text-center text-slate-400 dark:text-gray-500 text-xs space-y-2">
              <CheckCircle className="w-8 h-8 mx-auto text-slate-300 dark:text-gray-600" />
              <p>No repository changes detected yet.</p>
              <p className="text-slate-500 dark:text-gray-600">When the GitHub repository updates and you synchronize, change records will appear here.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {changes.map((chg) => {
                const style = CHANGE_TYPE_STYLES[chg.change_type] || { bg: 'bg-slate-100 dark:bg-gray-900 border border-slate-200 dark:border-gray-800', text: 'text-slate-600 dark:text-gray-400' };
                return (
                  <div
                    key={chg.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl bg-slate-50 dark:bg-gray-950/60 border border-slate-200 dark:border-gray-800/80 hover:border-slate-300 dark:hover:border-gray-700 transition-colors gap-2"
                  >
                    <div className="flex items-center space-x-3">
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${style.bg} ${style.text}`}>
                        {chg.change_type}
                      </span>
                      <span className="font-mono text-[10px] text-slate-500 dark:text-gray-400 uppercase w-16">{chg.entity_type}</span>
                      <span className="text-xs font-medium text-slate-800 dark:text-gray-200">{chg.change_summary}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-gray-500 whitespace-nowrap pl-4 sm:pl-0">
                      {new Date(chg.detected_at).toLocaleString()}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 4: Activity Timeline ─────────────────────────────────────── */}
      {activeTab === 'timeline' && (
        <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-6 space-y-4 shadow-sm dark:shadow-md">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-gray-800 pb-3">
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center space-x-2">
              <Activity className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              <span>Activity Timeline</span>
            </h3>
            <span className="text-xs text-slate-500 dark:text-gray-400">Events: {events.length}</span>
          </div>

          {events.length === 0 ? (
            <div className="p-8 text-center text-slate-400 dark:text-gray-500 text-xs">No activity logged for this Digital Twin yet.</div>
          ) : (
            <div className="relative pl-6 border-l-2 border-slate-200 dark:border-gray-800/80 space-y-4 ml-2">
              {events.map((ev) => (
                <div key={ev.id} className="relative">
                  {/* Dot */}
                  <span className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-cyan-500 border-2 border-white dark:border-gray-950" />

                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-gray-950/70 border border-slate-200 dark:border-gray-800/80 hover:border-slate-300 dark:hover:border-gray-700 transition-colors space-y-1.5">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-slate-900 dark:text-white">{ev.title}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-200 dark:bg-gray-800 text-slate-700 dark:text-cyan-300">
                          {ev.event_type}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-500 dark:text-gray-500">
                        {new Date(ev.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {ev.description && (
                      <p className="text-xs text-slate-600 dark:text-gray-400">{ev.description}</p>
                    )}
                    {ev.actor_login && (
                      <div className="flex items-center space-x-2 pt-1 text-[11px] text-slate-500 dark:text-gray-500">
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

      {/* ── TAB 5: Historical Snapshots ───────────────────────────────────── */}
      {activeTab === 'snapshots' && (
        <div className="bg-white dark:bg-[#111827]/90 border border-slate-200 dark:border-gray-800/80 rounded-2xl p-6 space-y-4 shadow-sm dark:shadow-md">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-gray-800 pb-3">
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center space-x-2">
              <History className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              <span>Historical Snapshots</span>
            </h3>
            <span className="text-xs text-slate-500 dark:text-gray-400">{snapshots.length} versions recorded</span>
          </div>

          {snapshots.length === 0 ? (
            <div className="p-8 text-center text-slate-400 dark:text-gray-500 text-xs space-y-2">
              <History className="w-8 h-8 mx-auto text-slate-300 dark:text-gray-600" />
              <p>No historical snapshots recorded yet.</p>
              <p>Snapshots are generated automatically upon successful repository synchronization.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700 dark:text-gray-300">
                <thead className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-gray-400 bg-slate-50 dark:bg-gray-900/60 border-b border-slate-200 dark:border-gray-800">
                  <tr>
                    <th className="py-3 px-4">Version</th>
                    <th className="py-3 px-4">Creation Timestamp (UTC)</th>
                    <th className="py-3 px-4">Repository</th>
                    <th className="py-3 px-4">Collected Records</th>
                    <th className="py-3 px-4">Data Coverage</th>
                    <th className="py-3 px-4">Changes</th>
                    <th className="py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-gray-800/50">
                  {snapshots.map((s, idx) => {
                    const totalRecords = s.entity_counts ? Object.values(s.entity_counts).reduce((a, b) => a + b, 0) : 0;
                    const coverage = s.state_data?.data_coverage !== undefined ? s.state_data.data_coverage : null;
                    return (
                      <tr key={s.id} className="hover:bg-slate-50 dark:hover:bg-gray-900/30 transition-colors">
                        <td className="py-3.5 px-4 font-mono font-bold text-cyan-600 dark:text-cyan-400">
                          v{s.version}
                        </td>
                        <td className="py-3.5 px-4 text-slate-700 dark:text-gray-300">
                          {new Date(s.created_at).toUTCString()}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-600 dark:text-gray-300">
                          {repo?.full_name || 'Repository'}
                        </td>
                        <td className="py-3.5 px-4 font-bold text-slate-900 dark:text-white">
                          {totalRecords.toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 font-bold text-emerald-600 dark:text-emerald-400">
                          {coverage !== null ? `${coverage}%` : 'N/A'}
                        </td>
                        <td className="py-3.5 px-4 text-slate-700 dark:text-gray-300">
                          {s.change_count} change{s.change_count === 1 ? '' : 's'}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            idx === 0
                              ? 'bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400'
                              : 'bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-gray-400'
                          }`}>
                            {idx === 0 ? 'CURRENT' : 'HISTORICAL'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
