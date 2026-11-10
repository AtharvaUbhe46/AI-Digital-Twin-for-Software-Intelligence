import React, { useEffect, useState, useCallback } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  Activity, Award, RefreshCw, CheckCircle2,
  AlertTriangle, AlertCircle, ShieldAlert, Info, TrendingUp,
  ShieldCheck, Lightbulb, ArrowUpRight, Check, Sparkles, Layers,
  FileCheck, GitPullRequest, GitCommit, Users, Clock
} from 'lucide-react';
import { Project, SoftwareHealthSnapshot, HealthHistoryPoint, DigitalTwinCore, SoftwareRisk, HealthRecommendation } from '../types';
import { apiService } from '../services/api';
import { useTheme } from '../context/ThemeContext';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'HEALTHY':
      return {
        bg: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:border-emerald-500/30 dark:text-emerald-400',
        icon: <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />,
        label: 'HEALTHY',
      };
    case 'ATTENTION':
      return {
        bg: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30 dark:text-amber-400',
        icon: <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />,
        label: 'ATTENTION',
      };
    case 'DEGRADED':
      return {
        bg: 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-500/10 dark:border-orange-500/30 dark:text-orange-400',
        icon: <AlertTriangle className="w-4 h-4 text-orange-600 dark:text-orange-400" />,
        label: 'DEGRADED',
      };
    case 'CRITICAL':
      return {
        bg: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-400',
        icon: <ShieldAlert className="w-4 h-4 text-red-600 dark:text-red-400" />,
        label: 'CRITICAL',
      };
    default:
      return {
        bg: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-gray-500/10 dark:border-gray-500/30 dark:text-gray-400',
        icon: <Info className="w-4 h-4 text-slate-500 dark:text-gray-400" />,
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
      : 'bg-gray-400';

  return (
    <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-xl p-5 flex flex-col justify-between shadow-sm dark:shadow-none hover:border-slate-300 dark:hover:border-gray-700 transition-colors">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-slate-800 dark:text-gray-200 text-sm">{name}</h3>
          <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs border font-medium ${badge.bg}`}>
            {badge.icon}
            <span>{badge.label}</span>
          </span>
        </div>

        <div className="flex items-baseline space-x-2 mb-2">
          {score !== null ? (
            <>
              <span className="text-3xl font-extrabold text-slate-900 dark:text-white">{score.toFixed(1)}</span>
              <span className="text-xs text-slate-500 dark:text-gray-400">/100 (Weight: {(weight * 100).toFixed(0)}%)</span>
            </>
          ) : (
            <span className="text-sm font-semibold text-slate-400 dark:text-gray-400 italic">No score calculated</span>
          )}
        </div>

        <div className="h-1.5 w-full bg-slate-100 dark:bg-gray-800 rounded-full overflow-hidden mb-3">
          <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${scorePct}%` }} />
        </div>

        {/* Explainable bullets */}
        {explanation && explanation.length > 0 && (
          <ul className="space-y-1 mb-4">
            {explanation.map((item, idx) => (
              <li key={idx} className="text-xs text-slate-600 dark:text-gray-400 flex items-start space-x-1.5">
                <span className="text-cyan-600 dark:text-cyan-500 font-bold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Metric chips */}
      {metrics && metrics.has_data && (
        <div className="pt-3 border-t border-slate-100 dark:border-gray-800/80 flex flex-wrap gap-1.5 text-[11px] text-slate-600 dark:text-gray-400">
          {metrics.days_since_last_commit !== undefined && (
            <span className="px-2 py-0.5 bg-slate-50 dark:bg-gray-800/60 rounded border border-slate-200 dark:border-gray-700/50">
              Last commit: {metrics.days_since_last_commit}d ago
            </span>
          )}
          {metrics.stale_count !== undefined && (
            <span className={`px-2 py-0.5 rounded border ${metrics.stale_count > 0 ? 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950/30 dark:border-amber-800/40 dark:text-amber-300' : 'bg-slate-50 dark:bg-gray-800/60 border-slate-200 dark:border-gray-700/50'}`}>
              Stale items: {metrics.stale_count}
            </span>
          )}
          {metrics.closure_rate !== undefined && (
            <span className="px-2 py-0.5 bg-slate-50 dark:bg-gray-800/60 rounded border border-slate-200 dark:border-gray-700/50">
              Closure rate: {metrics.closure_rate}%
            </span>
          )}
          {metrics.merge_rate !== undefined && (
            <span className="px-2 py-0.5 bg-slate-50 dark:bg-gray-800/60 rounded border border-slate-200 dark:border-gray-700/50">
              Merge rate: {metrics.merge_rate}%
            </span>
          )}
          {metrics.top_contributor_percentage !== undefined && (
            <span className="px-2 py-0.5 bg-slate-50 dark:bg-gray-800/60 rounded border border-slate-200 dark:border-gray-700/50">
              Top author share: {metrics.top_contributor_percentage}%
            </span>
          )}
          {metrics.latest_release_tag && (
            <span className="px-2 py-0.5 bg-slate-50 dark:bg-gray-800/60 rounded border border-slate-200 dark:border-gray-700/50 font-mono">
              {metrics.latest_release_tag}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export const SoftwareHealthPage: React.FC<Props> = ({ activeProject, onOpenConnectModal }) => {
  const { isDark } = useTheme();
  const [snapshot, setSnapshot] = useState<SoftwareHealthSnapshot | null>(null);
  const [history, setHistory] = useState<HealthHistoryPoint[]>([]);
  const [twin, setTwin] = useState<DigitalTwinCore | null>(null);
  const [risks, setRisks] = useState<SoftwareRisk[]>([]);
  const [recommendations, setRecommendations] = useState<HealthRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (projectId: number) => {
    try {
      setLoading(true);
      setError(null);
      const [healthData, historyData, twinData, risksData, recsData] = await Promise.all([
        apiService.getSoftwareHealth(projectId),
        apiService.getHealthHistory(projectId, 30),
        apiService.getDigitalTwinCore(projectId).catch(() => null),
        apiService.getSoftwareRisks(projectId, { status: 'OPEN' }).catch(() => []),
        apiService.getHealthRecommendations(projectId).catch(() => []),
      ]);
      setSnapshot(healthData);
      setHistory(historyData);
      setTwin(twinData);
      setRisks(risksData);
      setRecommendations(recsData);
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
        <Activity className="w-12 h-12 text-slate-400 dark:text-gray-600" />
        <p className="text-slate-800 dark:text-gray-300 font-medium">No repository connected</p>
        <p className="text-slate-500 dark:text-gray-500 text-sm max-w-sm">
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
        <div className="h-8 bg-slate-200 dark:bg-gray-800/40 rounded w-64 animate-pulse" />
        <div className="h-40 bg-slate-200 dark:bg-gray-800/30 rounded-xl animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 bg-slate-200 dark:bg-gray-800/30 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !snapshot) {
    return (
      <div className="space-y-4">
        <div className="p-6 rounded-xl border border-red-200 dark:border-red-800/50 bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-300 flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-500 dark:text-red-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-red-800 dark:text-red-200">Unable to Load Software Health</h4>
            <p className="text-sm text-red-700/80 dark:text-red-300/80 mt-1">{error || 'No health snapshot found.'}</p>
            <button
              onClick={() => loadData(activeProject.id)}
              className="mt-3 px-3 py-1.5 bg-red-100 hover:bg-red-200 dark:bg-red-900/40 border border-red-300 dark:border-red-700/60 rounded text-xs text-red-800 dark:text-red-200 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const overallBadge = getStatusBadge(snapshot?.overall_status || 'UNKNOWN');
  const calculatedDate = snapshot?.calculated_at ? new Date(snapshot.calculated_at).toLocaleString() : 'Recently';

  // Freshness check: warn if twin is stale
  const isTwinStale = twin?.is_outdated || false;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Software Health</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-950/50 dark:border-cyan-800/40 dark:text-cyan-300">
              Health Engine
            </span>
          </div>
          <p className="text-sm text-slate-500 dark:text-gray-400 mt-1">
            Explainable engineering indicators for <span className="text-slate-800 dark:text-gray-200 font-medium">{activeProject.full_name}</span> · Calculated {calculatedDate}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleRecalculate}
            disabled={recalculating}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 dark:bg-gray-800 dark:border-gray-700 dark:hover:border-gray-600 text-slate-700 dark:text-gray-200 text-xs font-medium transition-colors disabled:opacity-50 shadow-sm dark:shadow-none"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 ${recalculating ? 'animate-spin' : ''}`} />
            <span>{recalculating ? 'Recalculating...' : 'Recalculate Health'}</span>
          </button>
        </div>
      </div>

      {/* Stale Digital Twin Warning Banner */}
      {isTwinStale && (
        <div className="p-3.5 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/40 rounded-xl flex items-center justify-between text-xs text-amber-800 dark:text-amber-300">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-500 dark:text-amber-400 shrink-0" />
            <span>
              Underlying Digital Twin was last synchronized {twin?.last_synced_at ? new Date(twin.last_synced_at).toLocaleString() : 'previously'}. Sync the Digital Twin to refresh live telemetry.
            </span>
          </div>
        </div>
      )}

      {/* Top Banner: Overall Score & Explainable Summary */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-xl p-6 shadow-sm dark:shadow-none transition-colors">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-center">
          {/* Main Score Dial */}
          <div className="lg:col-span-1 border-b lg:border-b-0 lg:border-r border-slate-100 dark:border-gray-800 pb-6 lg:pb-0 lg:pr-6 flex flex-col items-center justify-center text-center">
            <span className="text-xs font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider mb-2">Overall Health Index</span>
            <div className="text-6xl font-black text-slate-900 dark:text-white tracking-tight mb-2">
              {Number(snapshot.overall_score ?? 0).toFixed(1)}
            </div>
            <div className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold border ${overallBadge.bg}`}>
              {overallBadge.icon}
              <span>{overallBadge.label}</span>
            </div>
            <p className="text-[11px] text-slate-400 dark:text-gray-500 mt-2 font-mono">
              Twin Version: v{snapshot.twin_version || 1} · v{snapshot.calculation_version || '1.0'}
            </p>
          </div>

          {/* Explainable Reasons */}
          <div className="lg:col-span-3">
            <h3 className="text-xs font-semibold text-slate-700 dark:text-gray-300 uppercase tracking-wider mb-3 flex items-center space-x-1.5">
              <Award className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              <span>Diagnostic Explanations</span>
            </h3>
            <div className="space-y-2">
              {snapshot.explanations && snapshot.explanations.length > 0 ? (
                snapshot.explanations.map((exp, idx) => (
                  <div key={idx} className="flex items-start space-x-2 text-sm text-slate-700 dark:text-gray-300">
                    <span className="text-cyan-600 dark:text-cyan-400 font-bold shrink-0 mt-0.5">•</span>
                    <span>{exp}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500 dark:text-gray-500">All evaluated metrics are within standard operating parameters.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Historical Health Trend */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-xl p-5 shadow-sm dark:shadow-none transition-colors">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
            <h3 className="text-sm font-semibold text-slate-800 dark:text-gray-200">Health Index History</h3>
          </div>
          <span className="text-xs text-slate-500 dark:text-gray-500">{history?.length || 0} snapshot(s) recorded</span>
        </div>

        {Array.isArray(history) && history.length >= 2 ? (
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
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={isDark ? 0.3 : 0.25} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#1f2937' : '#e2e8f0'} />
              <XAxis dataKey="time" stroke={isDark ? '#64748b' : '#94a3b8'} tick={{ fill: isDark ? '#6b7280' : '#64748b', fontSize: 11 }} />
              <YAxis domain={[0, 100]} stroke={isDark ? '#64748b' : '#94a3b8'} tick={{ fill: isDark ? '#6b7280' : '#64748b', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: isDark ? '#111827' : '#ffffff',
                  border: isDark ? '1px solid #374151' : '1px solid #e2e8f0',
                  borderRadius: 8,
                  color: isDark ? '#f9fafb' : '#0f172a',
                  boxShadow: isDark ? '0 10px 15px -3px rgba(0, 0, 0, 0.4)' : '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
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
          <div className="h-36 flex flex-col items-center justify-center border border-dashed border-slate-200 dark:border-gray-800 rounded-lg text-center p-4">
            <Info className="w-6 h-6 text-slate-400 dark:text-gray-600 mb-1" />
            <p className="text-xs text-slate-600 dark:text-gray-400 font-medium">Initial Health Snapshot Persisted</p>
            <p className="text-[11px] text-slate-500 dark:text-gray-500 mt-0.5">
              Subsequent syncs and recalculations will draw a real-time historical trend line across versions.
            </p>
          </div>
        )}
      </div>

      {/* 6 Explainable Health Dimensions Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center space-x-2">
            <Layers className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
            <span>Evaluated Engineering Dimensions</span>
          </h2>
          <span className="text-xs text-slate-500 dark:text-gray-400">
            {snapshot.dimensions.length} Evaluated Metrics
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.isArray(snapshot.dimensions) && snapshot.dimensions.map((dim) => (
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

      {/* Open Engineering Risks Section */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-xl p-6 shadow-sm dark:shadow-none transition-colors">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-gray-800/80 pb-3.5 mb-4">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Detected Engineering Risks</h3>
          </div>
          <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-gray-800 text-slate-700 dark:text-gray-300">
            {risks.length} Active Findings
          </span>
        </div>

        {risks.length === 0 ? (
          <div className="p-6 rounded-xl bg-slate-50 dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800 text-center space-y-2">
            <ShieldCheck className="w-8 h-8 text-emerald-500 dark:text-emerald-400 mx-auto" />
            <p className="text-sm font-semibold text-slate-800 dark:text-gray-200">No Critical Risks Detected</p>
            <p className="text-xs text-slate-500 dark:text-gray-400 max-w-sm mx-auto">
              Current activity, issue closure cadence, and pull request workflows satisfy engineering reliability thresholds.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {risks.map((risk) => {
              const isHigh = risk.severity === 'CRITICAL' || risk.severity === 'HIGH';
              return (
                <div
                  key={risk.id}
                  className="p-4 rounded-xl bg-slate-50 dark:bg-gray-900/60 border border-slate-200 dark:border-gray-800 hover:border-slate-300 dark:hover:border-gray-700 transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span className="text-xs font-bold text-slate-900 dark:text-white leading-snug">
                        {risk.title}
                      </span>
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase shrink-0 ${
                          isHigh
                            ? 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:border-rose-800 dark:text-rose-300'
                            : 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:border-amber-800 dark:text-amber-300'
                        }`}
                      >
                        {risk.severity}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-gray-300 mb-2 leading-relaxed">
                      {risk.description}
                    </p>
                  </div>
                  <div className="pt-2 border-t border-slate-200 dark:border-gray-800 flex items-center justify-between text-[11px] text-slate-500 dark:text-gray-400 font-mono">
                    <span>Rule: {risk.detection_rule}</span>
                    {risk.metric_value && <span className="text-slate-800 dark:text-gray-200 font-semibold">{risk.metric_value}</span>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Actionable Recommendations Section */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-xl p-6 shadow-sm dark:shadow-none transition-colors">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-gray-800/80 pb-3.5 mb-4">
          <div className="flex items-center space-x-2">
            <Lightbulb className="w-4 h-4 text-amber-500" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Actionable Health Recommendations</h3>
          </div>
          <span className="text-xs text-slate-500 dark:text-gray-400">
            {recommendations.length} Prioritized Suggestion(s)
          </span>
        </div>

        <div className="space-y-3">
          {recommendations.map((rec) => (
            <div
              key={rec.id}
              className="p-4 rounded-xl bg-slate-50 dark:bg-gray-900/60 border border-slate-200 dark:border-gray-800 flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1 max-w-3xl">
                <div className="flex items-center space-x-2">
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase border ${
                      rec.priority === 'HIGH'
                        ? 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:border-rose-800 dark:text-rose-300'
                        : rec.priority === 'MEDIUM'
                        ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:border-amber-800 dark:text-amber-300'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:border-emerald-800 dark:text-emerald-300'
                    }`}
                  >
                    {rec.priority} Priority
                  </span>
                  <span className="text-xs font-bold text-slate-900 dark:text-white">
                    {rec.title}
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-gray-300 leading-relaxed">
                  {rec.description}
                </p>
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500 dark:text-gray-400 pt-1">
                  <span><strong>Evidence:</strong> {rec.evidence}</span>
                  <span>•</span>
                  <span><strong>Recommended Action:</strong> {rec.action}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
