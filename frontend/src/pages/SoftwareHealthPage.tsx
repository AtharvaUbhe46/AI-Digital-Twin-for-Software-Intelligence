import React, { useEffect, useState, useCallback } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  Activity, GitCommit, AlertCircle, GitPullRequest, Users,
  Clock, TrendingUp, Award, Tag, RefreshCw, CheckCircle2,
  AlertTriangle, ShieldAlert, Info
} from 'lucide-react';
import { Project, SoftwareHealthSnapshot, HealthHistoryPoint, DigitalTwinCore } from '../types';
import { apiService } from '../services/api';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'HEALTHY':
      return {
        bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
        icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
        label: 'HEALTHY',
      };
    case 'ATTENTION':
      return {
        bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
        icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
        label: 'ATTENTION',
      };
    case 'DEGRADED':
      return {
        bg: 'bg-orange-500/10 border-orange-500/30 text-orange-400',
        icon: <AlertTriangle className="w-4 h-4 text-orange-400" />,
        label: 'DEGRADED',
      };
    case 'CRITICAL':
      return {
        bg: 'bg-red-500/10 border-red-500/30 text-red-400',
        icon: <ShieldAlert className="w-4 h-4 text-red-400" />,
        label: 'CRITICAL',
      };
    default:
      return {
        bg: 'bg-gray-500/10 border-gray-500/30 text-gray-400',
        icon: <Info className="w-4 h-4 text-gray-400" />,
        label: 'INSUFFICIENT DATA',
      };
  }
};

const DimensionCard: React.FC<{
  dimension: string;
  name: string;
  score: number | null;
  weight: number;
  status: string;
  metrics?: Record<string, any>;
  explanation?: string[];
}> = ({ name, score, weight, status, metrics, explanation }) => {
  const badge = getStatusBadge(status);
  const scorePct = score !== null ? score : 0;
  const barColor =
    status === 'HEALTHY'
      ? 'bg-emerald-500'
      : status === 'ATTENTION'
      ? 'bg-amber-500'
      : status === 'DEGRADED'
      ? 'bg-orange-500'
      : status === 'CRITICAL'
      ? 'bg-red-500'
      : 'bg-gray-600';

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 flex flex-col justify-between hover:border-gray-700 transition-colors">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-gray-200 text-sm">{name}</h3>
          <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs border font-medium ${badge.bg}`}>
            {badge.icon}
            <span>{badge.label}</span>
          </span>
        </div>

        <div className="flex items-baseline space-x-2 mb-2">
          {score !== null ? (
            <>
              <span className="text-3xl font-extrabold text-white">{score.toFixed(1)}</span>
              <span className="text-xs text-gray-400">/100 (Weight: {(weight * 100).toFixed(0)}%)</span>
            </>
          ) : (
            <span className="text-sm font-semibold text-gray-400 italic">No score calculated</span>
          )}
        </div>

        <div className="h-1.5 w-full bg-gray-800 rounded-full overflow-hidden mb-3">
          <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${scorePct}%` }} />
        </div>

        {/* Explainable bullets */}
        {explanation && explanation.length > 0 && (
          <ul className="space-y-1 mb-4">
            {explanation.map((item, idx) => (
              <li key={idx} className="text-xs text-gray-400 flex items-start space-x-1.5">
                <span className="text-cyan-500 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Metric chips */}
      {metrics && metrics.has_data && (
        <div className="pt-3 border-t border-gray-800/80 flex flex-wrap gap-1.5 text-[11px] text-gray-400">
          {metrics.days_since_last_commit !== undefined && (
            <span className="px-2 py-0.5 bg-gray-800/60 rounded border border-gray-700/50">
              Last commit: {metrics.days_since_last_commit}d ago
            </span>
          )}
          {metrics.stale_count !== undefined && (
            <span className={`px-2 py-0.5 rounded border ${metrics.stale_count > 0 ? 'bg-amber-950/30 border-amber-800/40 text-amber-300' : 'bg-gray-800/60 border-gray-700/50'}`}>
              Stale items: {metrics.stale_count}
            </span>
          )}
          {metrics.closure_rate !== undefined && (
            <span className="px-2 py-0.5 bg-gray-800/60 rounded border border-gray-700/50">
              Closure rate: {metrics.closure_rate}%
            </span>
          )}
          {metrics.merge_rate !== undefined && (
            <span className="px-2 py-0.5 bg-gray-800/60 rounded border border-gray-700/50">
              Merge rate: {metrics.merge_rate}%
            </span>
          )}
          {metrics.top_contributor_percentage !== undefined && (
            <span className="px-2 py-0.5 bg-gray-800/60 rounded border border-gray-700/50">
              Top author share: {metrics.top_contributor_percentage}%
            </span>
          )}
          {metrics.latest_release_tag && (
            <span className="px-2 py-0.5 bg-gray-800/60 rounded border border-gray-700/50 font-mono">
              {metrics.latest_release_tag}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export const SoftwareHealthPage: React.FC<Props> = ({ activeProject, onOpenConnectModal }) => {
  const [snapshot, setSnapshot] = useState<SoftwareHealthSnapshot | null>(null);
  const [history, setHistory] = useState<HealthHistoryPoint[]>([]);
  const [twin, setTwin] = useState<DigitalTwinCore | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (projectId: number) => {
    try {
      setLoading(true);
      setError(null);
      const [healthData, historyData, twinData] = await Promise.all([
        apiService.getSoftwareHealth(projectId),
        apiService.getHealthHistory(projectId, 30),
        apiService.getDigitalTwinCore(projectId).catch(() => null),
      ]);
      setSnapshot(healthData);
      setHistory(historyData);
      setTwin(twinData);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load Software Health');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!activeProject) {
      setSnapshot(null);
      setHistory([]);
      setLoading(false);
      return;
    }
    loadData(activeProject.id);
  }, [activeProject?.id, loadData]);

  const handleRecalculate = async () => {
    if (!activeProject) return;
    try {
      setRecalculating(true);
      const updated = await apiService.recalculateHealth(activeProject.id);
      setSnapshot(updated);
      const updatedHistory = await apiService.getHealthHistory(activeProject.id, 30);
      setHistory(updatedHistory);
    } catch (err: any) {
      alert(`Recalculation error: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setRecalculating(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center h-80 space-y-3 text-center">
        <Activity className="w-12 h-12 text-gray-600" />
        <p className="text-gray-300 font-medium">No repository connected</p>
        <p className="text-gray-500 text-sm max-w-sm">
          Connect a GitHub repository to evaluate deterministic engineering health dimensions and calculate risk profiles.
        </p>
        <button
          onClick={onOpenConnectModal}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Connect Repository
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-800/40 rounded w-64 animate-pulse" />
        <div className="h-40 bg-gray-800/30 rounded-xl animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 bg-gray-800/30 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !snapshot) {
    return (
      <div className="space-y-4">
        <div className="p-6 rounded-xl border border-red-800/50 bg-red-950/20 text-red-300 flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-red-200">Unable to Load Software Health</h4>
            <p className="text-sm text-red-300/80 mt-1">{error || 'No health snapshot found.'}</p>
            <button
              onClick={() => loadData(activeProject.id)}
              className="mt-3 px-3 py-1.5 bg-red-900/40 border border-red-700/60 rounded text-xs text-red-200 hover:bg-red-800/50 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const overallBadge = getStatusBadge(snapshot.overall_status);
  const calculatedDate = new Date(snapshot.calculated_at).toLocaleString();

  // Freshness check: warn if twin is stale
  const isTwinStale = twin?.is_outdated || false;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Software Health</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950/50 border border-cyan-800/40 text-cyan-300">
              Phase 4 Engine
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Explainable engineering indicators for <span className="text-gray-200 font-medium">{activeProject.full_name}</span> · Calculated {calculatedDate}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleRecalculate}
            disabled={recalculating}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-gray-800 border border-gray-700 hover:border-gray-600 text-gray-200 text-xs font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${recalculating ? 'animate-spin' : ''}`} />
            <span>{recalculating ? 'Recalculating...' : 'Recalculate Health'}</span>
          </button>
        </div>
      </div>

      {/* Stale Digital Twin Warning Banner */}
      {isTwinStale && (
        <div className="p-3.5 bg-amber-950/30 border border-amber-800/40 rounded-xl flex items-center justify-between text-xs text-amber-300">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              Underlying Digital Twin was last synchronized {twin?.last_synced_at ? new Date(twin.last_synced_at).toLocaleString() : 'previously'}. Sync the Digital Twin to refresh live telemetry.
            </span>
          </div>
        </div>
      )}

      {/* Top Banner: Overall Score & Explainable Summary */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-center">
          {/* Main Score Dial */}
          <div className="lg:col-span-1 border-b lg:border-b-0 lg:border-r border-gray-800 pb-6 lg:pb-0 lg:pr-6 flex flex-col items-center justify-center text-center">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Overall Health Index</span>
            <div className="text-6xl font-black text-white tracking-tight mb-2">
              {snapshot.overall_score.toFixed(1)}
            </div>
            <div className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold border ${overallBadge.bg}`}>
              {overallBadge.icon}
              <span>{overallBadge.label}</span>
            </div>
            <p className="text-[11px] text-gray-500 mt-2">
              Twin Version: v{snapshot.twin_version || 1} · v{snapshot.calculation_version}
            </p>
          </div>

          {/* Explainable Reasons */}
          <div className="lg:col-span-3">
            <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3 flex items-center space-x-1.5">
              <Award className="w-4 h-4 text-cyan-400" />
              <span>Diagnostic Explanations</span>
            </h3>
            <div className="space-y-2">
              {snapshot.explanations && snapshot.explanations.length > 0 ? (
                snapshot.explanations.map((exp, idx) => (
                  <div key={idx} className="flex items-start space-x-2 text-sm text-gray-300">
                    <span className="text-cyan-400 font-bold shrink-0 mt-0.5">•</span>
                    <span>{exp}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">All evaluated metrics are within standard operating parameters.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Historical Health Trend */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-gray-200">Health Index History</h3>
          </div>
          <span className="text-xs text-gray-500">{history.length} snapshot(s) recorded</span>
        </div>

        {history.length >= 2 ? (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart
              data={history.map(h => ({
                time: new Date(h.calculated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                score: h.overall_score,
                version: `v${h.twin_version || 1}`,
              }))}
            >
              <defs>
                <linearGradient id="healthGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }}
                formatter={(val: any) => [`${val}/100`, 'Health Score']}
              />
              <Area
                type="monotone"
                dataKey="score"
                stroke="#06b6d4"
                fill="url(#healthGrad)"
                strokeWidth={2}
                dot={{ fill: '#06b6d4', r: 3 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-36 flex flex-col items-center justify-center border border-dashed border-gray-800 rounded-lg text-center p-4">
            <Info className="w-6 h-6 text-gray-600 mb-1" />
            <p className="text-xs text-gray-400 font-medium">Initial Health Snapshot Persisted</p>
            <p className="text-[11px] text-gray-500 mt-0.5">
              Subsequent syncs and recalculations will draw a real-time historical trend line across versions.
            </p>
          </div>
        )}
      </div>

      {/* 6 Explainable Health Dimensions Grid */}
      <div>
        <h2 className="text-base font-semibold text-white mb-3">Evaluated Engineering Dimensions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {snapshot.dimensions.map((dim) => (
            <DimensionCard
              key={dim.dimension}
              dimension={dim.dimension}
              name={dim.name}
              score={dim.score}
              weight={dim.weight}
              status={dim.status}
              metrics={dim.metrics}
              explanation={dim.explanation}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
