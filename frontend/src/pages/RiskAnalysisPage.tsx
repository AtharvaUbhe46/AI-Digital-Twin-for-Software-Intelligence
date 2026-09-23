import React, { useEffect, useState, useCallback } from 'react';
import {
  ShieldAlert, ShieldCheck, AlertTriangle, AlertOctagon,
  Info, RefreshCw, CheckCircle2, XCircle, ExternalLink,
  Filter, Eye, Check, X, ArrowUpDown
} from 'lucide-react';
import { Project, SoftwareRisk, RiskSummary } from '../types';
import { apiService } from '../services/api';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

const SEVERITY_CONFIG = {
  CRITICAL: {
    text: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-800/60',
    badge: 'bg-red-950/60 border border-red-700/60 text-red-300',
    icon: AlertOctagon,
    color: '#ef4444',
  },
  HIGH: {
    text: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-800/60',
    badge: 'bg-orange-950/60 border border-orange-700/60 text-orange-300',
    icon: AlertTriangle,
    color: '#f97316',
  },
  MEDIUM: {
    text: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-800/60',
    badge: 'bg-amber-950/60 border border-amber-700/60 text-amber-300',
    icon: AlertTriangle,
    color: '#f59e0b',
  },
  LOW: {
    text: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-800/60',
    badge: 'bg-blue-950/60 border border-blue-700/60 text-blue-300',
    icon: Info,
    color: '#3b82f6',
  },
};

export const RiskAnalysisPage: React.FC<Props> = ({ activeProject, onOpenConnectModal }) => {
  const [risks, setRisks] = useState<SoftwareRisk[]>([]);
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Sorting
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'severity' | 'newest' | 'oldest'>('severity');

  // Modal / Drawer Detail View
  const [selectedRisk, setSelectedRisk] = useState<SoftwareRisk | null>(null);
  const [transitionLoading, setTransitionLoading] = useState(false);

  const loadData = useCallback(async (projectId: number) => {
    try {
      setLoading(true);
      setError(null);
      const [risksData, summaryData] = await Promise.all([
        apiService.getSoftwareRisks(projectId),
        apiService.getRisksSummary(projectId),
      ]);
      setRisks(risksData);
      setSummary(summaryData);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load risks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!activeProject) {
      setRisks([]);
      setSummary(null);
      setLoading(false);
      return;
    }
    loadData(activeProject.id);
  }, [activeProject?.id, loadData]);

  const handleRecalculate = async () => {
    if (!activeProject) return;
    try {
      setRecalculating(true);
      const updatedRisks = await apiService.recalculateRisks(activeProject.id);
      setRisks(updatedRisks);
      const updatedSummary = await apiService.getRisksSummary(activeProject.id);
      setSummary(updatedSummary);
      if (selectedRisk) {
        const refreshed = updatedRisks.find(r => r.id === selectedRisk.id) || null;
        setSelectedRisk(refreshed);
      }
    } catch (err: any) {
      alert(`Recalculation error: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setRecalculating(false);
    }
  };

  const handleAcknowledge = async (riskId: number) => {
    if (!activeProject) return;
    try {
      setTransitionLoading(true);
      const updated = await apiService.acknowledgeRisk(activeProject.id, riskId);
      setRisks(prev => prev.map(r => (r.id === updated.id ? updated : r)));
      if (selectedRisk?.id === updated.id) setSelectedRisk(updated);
      const updatedSummary = await apiService.getRisksSummary(activeProject.id);
      setSummary(updatedSummary);
    } catch (err: any) {
      alert(`Acknowledgement error: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setTransitionLoading(false);
    }
  };

  const handleResolve = async (riskId: number) => {
    if (!activeProject) return;
    try {
      setTransitionLoading(true);
      const updated = await apiService.resolveRisk(activeProject.id, riskId);
      setRisks(prev => prev.map(r => (r.id === updated.id ? updated : r)));
      if (selectedRisk?.id === updated.id) setSelectedRisk(updated);
      const updatedSummary = await apiService.getRisksSummary(activeProject.id);
      setSummary(updatedSummary);
    } catch (err: any) {
      alert(`Resolution error: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setTransitionLoading(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center h-80 space-y-3 text-center">
        <ShieldAlert className="w-12 h-12 text-gray-600" />
        <p className="text-gray-300 font-medium">No repository connected</p>
        <p className="text-gray-500 text-sm max-w-sm">
          Connect a GitHub repository to evaluate deterministic engineering risk patterns.
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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-800/30 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-800/20 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-xl border border-red-800/50 bg-red-950/20 text-red-300">
        <h4 className="font-semibold text-red-200">Unable to Load Risks</h4>
        <p className="text-sm text-red-300/80 mt-1">{error}</p>
        <button
          onClick={() => loadData(activeProject.id)}
          className="mt-3 px-3 py-1.5 bg-red-900/40 border border-red-700/60 rounded text-xs text-red-200 hover:bg-red-800/50 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Filter and sort risks
  let filteredRisks = [...risks];
  if (statusFilter !== 'ALL') {
    filteredRisks = filteredRisks.filter(r => r.status === statusFilter);
  }
  if (severityFilter !== 'ALL') {
    filteredRisks = filteredRisks.filter(r => r.severity === severityFilter);
  }

  filteredRisks.sort((a, b) => {
    if (sortBy === 'severity') {
      const order: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
      return (order[b.severity] || 0) - (order[a.severity] || 0);
    }
    if (sortBy === 'newest') {
      return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime();
    }
    return new Date(a.detected_at).getTime() - new Date(b.detected_at).getTime();
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Risk Detection</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950/50 border border-cyan-800/40 text-cyan-300">
              Rule Engine
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Explainable engineering risk detection for <span className="text-gray-200 font-medium">{activeProject.full_name}</span>
          </p>
        </div>

        <button
          onClick={handleRecalculate}
          disabled={recalculating}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-gray-800 border border-gray-700 hover:border-gray-600 text-gray-200 text-xs font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${recalculating ? 'animate-spin' : ''}`} />
          <span>{recalculating ? 'Evaluating...' : 'Recalculate Risks'}</span>
        </button>
      </div>

      {/* Severity KPI Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map(sev => {
          const cfg = SEVERITY_CONFIG[sev];
          const Icon = cfg.icon;
          const count =
            sev === 'CRITICAL'
              ? summary?.critical_count || 0
              : sev === 'HIGH'
              ? summary?.high_count || 0
              : sev === 'MEDIUM'
              ? summary?.medium_count || 0
              : summary?.low_count || 0;

          const isSelected = severityFilter === sev;

          return (
            <button
              key={sev}
              onClick={() => setSeverityFilter(isSelected ? 'ALL' : sev)}
              className={`p-4 rounded-xl border text-left transition-all bg-[#111827] ${
                isSelected ? `${cfg.border} ring-1 ring-cyan-500` : 'border-gray-800 hover:border-gray-700'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400 font-semibold">{sev}</span>
                <Icon className={`w-4 h-4 ${cfg.text}`} />
              </div>
              <p className={`text-3xl font-extrabold ${cfg.text}`}>{count}</p>
              <p className="text-[11px] text-gray-500 mt-0.5">Active risk items</p>
            </button>
          );
        })}
      </div>

      {/* Filter and Control Bar */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="flex items-center space-x-1.5 text-gray-400 mr-2">
            <Filter className="w-3.5 h-3.5 text-cyan-400" />
            <span>Filters:</span>
          </div>

          {/* Status filter buttons */}
          {(['ALL', 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'] as const).map(st => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                statusFilter === st
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-800/80 text-gray-400 hover:text-gray-200'
              }`}
            >
              {st}
            </button>
          ))}

          {severityFilter !== 'ALL' && (
            <button
              onClick={() => setSeverityFilter('ALL')}
              className="ml-2 text-xs text-cyan-400 hover:underline flex items-center space-x-1"
            >
              <X className="w-3 h-3" />
              <span>Clear severity filter</span>
            </button>
          )}
        </div>

        {/* Sort selector */}
        <div className="flex items-center space-x-2 text-xs text-gray-400">
          <ArrowUpDown className="w-3.5 h-3.5 text-gray-500" />
          <span>Sort by:</span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value as any)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-200 text-xs focus:outline-none focus:border-cyan-500"
          >
            <option value="severity">Severity (High to Low)</option>
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
          </select>
        </div>
      </div>

      {/* Risk List / Table */}
      <div className="space-y-3">
        {filteredRisks.length === 0 ? (
          <div className="p-12 text-center bg-[#111827] border border-gray-800 rounded-xl">
            <ShieldCheck className="w-12 h-12 text-emerald-400 mx-auto mb-2" />
            <h3 className="text-base font-semibold text-gray-200">No matching risks found</h3>
            <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
              No risks currently match the active filters. Repository telemetry satisfies all evaluated rule thresholds.
            </p>
          </div>
        ) : (
          filteredRisks.map(risk => {
            const cfg = SEVERITY_CONFIG[risk.severity as keyof typeof SEVERITY_CONFIG] || SEVERITY_CONFIG.LOW;
            const Icon = cfg.icon;
            const isResolved = risk.status === 'RESOLVED';
            const isAck = risk.status === 'ACKNOWLEDGED';

            return (
              <div
                key={risk.id}
                className={`bg-[#111827] border rounded-xl p-4 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  isResolved ? 'border-gray-800/60 opacity-60' : `${cfg.border} hover:border-gray-600`
                }`}
              >
                <div className="flex items-start space-x-3 flex-1 min-w-0">
                  <div className={`p-2 rounded-lg ${cfg.bg} shrink-0 mt-0.5`}>
                    <Icon className={`w-4 h-4 ${cfg.text}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center space-x-2 flex-wrap gap-y-1 mb-1">
                      <h4 className="text-sm font-semibold text-white truncate">{risk.title}</h4>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide ${cfg.badge}`}>
                        {risk.severity}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                          isResolved
                            ? 'bg-gray-800 text-gray-400 border border-gray-700'
                            : isAck
                            ? 'bg-blue-950/50 text-blue-300 border border-blue-800/40'
                            : 'bg-amber-950/50 text-amber-300 border border-amber-800/40'
                        }`}
                      >
                        {risk.status}
                      </span>
                    </div>

                    <p className="text-xs text-gray-400 leading-relaxed line-clamp-2">{risk.description}</p>

                    <div className="flex items-center space-x-4 mt-2 text-[11px] text-gray-500">
                      <span>Rule: <code className="text-gray-400">{risk.detection_rule}</code></span>
                      {risk.metric_value && (
                        <span>Value: <strong className={cfg.text}>{risk.metric_value}</strong></span>
                      )}
                      <span>Detected: {new Date(risk.detected_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0 self-end md:self-center">
                  <button
                    onClick={() => setSelectedRisk(risk)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 border border-gray-700 text-xs text-gray-300 transition-colors"
                  >
                    <Eye className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Details & Evidence</span>
                  </button>

                  {risk.status === 'OPEN' && (
                    <button
                      onClick={() => handleAcknowledge(risk.id)}
                      disabled={transitionLoading}
                      title="Mark as Acknowledged"
                      className="px-2.5 py-1.5 rounded-lg bg-blue-950/40 border border-blue-800/50 hover:bg-blue-900/50 text-blue-300 text-xs font-medium transition-colors"
                    >
                      Acknowledge
                    </button>
                  )}

                  {risk.status !== 'RESOLVED' && (
                    <button
                      onClick={() => handleResolve(risk.id)}
                      disabled={transitionLoading}
                      title="Mark as Resolved"
                      className="px-2.5 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/50 hover:bg-emerald-900/50 text-emerald-300 text-xs font-medium transition-colors"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Interactive Risk Detail Modal / Drawer */}
      {selectedRisk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-[#111827] border border-gray-700 rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto shadow-2xl p-6 space-y-5">
            {/* Modal Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-xl ${SEVERITY_CONFIG[selectedRisk.severity as keyof typeof SEVERITY_CONFIG]?.bg || 'bg-gray-800'}`}>
                  <ShieldAlert className={`w-5 h-5 ${SEVERITY_CONFIG[selectedRisk.severity as keyof typeof SEVERITY_CONFIG]?.text || 'text-cyan-400'}`} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">{selectedRisk.title}</h3>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${SEVERITY_CONFIG[selectedRisk.severity as keyof typeof SEVERITY_CONFIG]?.badge}`}>
                      {selectedRisk.severity}
                    </span>
                    <span className="text-xs text-gray-400 font-mono">{selectedRisk.risk_type}</span>
                    <span className="text-xs text-gray-500">· Status: <strong>{selectedRisk.status}</strong></span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedRisk(null)}
                className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Description */}
            <div className="p-3.5 bg-gray-900/60 rounded-xl border border-gray-800">
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Description</h4>
              <p className="text-sm text-gray-300 leading-relaxed">{selectedRisk.description}</p>
            </div>

            {/* Rule & Metric vs Threshold */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 bg-gray-900/40 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-500 uppercase font-semibold">Detection Rule</span>
                <p className="text-xs font-mono text-cyan-300 mt-1">{selectedRisk.detection_rule}</p>
              </div>
              <div className="p-3 bg-gray-900/40 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-500 uppercase font-semibold">Observed vs Threshold</span>
                <p className="text-xs font-semibold text-gray-200 mt-1">
                  Current: <span className="text-amber-400">{selectedRisk.metric_value || 'Triggered'}</span> · Config: {selectedRisk.threshold_value || 'Default'}
                </p>
              </div>
            </div>

            {/* Granular Evidence */}
            {selectedRisk.evidence && Object.keys(selectedRisk.evidence).length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Diagnostic Evidence</h4>
                <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-3 text-xs font-mono text-gray-300 space-y-1">
                  {Object.entries(selectedRisk.evidence).map(([k, v]) => (
                    <div key={k} className="flex justify-between py-0.5 border-b border-gray-800/50 last:border-0">
                      <span className="text-gray-400">{k}:</span>
                      <span className="text-cyan-300 font-semibold">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Affected Entities */}
            {selectedRisk.affected_entities && selectedRisk.affected_entities.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Affected Entities</h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {selectedRisk.affected_entities.map((ent, i) => (
                    <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-gray-900/50 border border-gray-800 text-xs">
                      <span className="text-gray-300">
                        {ent.type.toUpperCase()} #{ent.number || ent.id || ent.login || ent.tag}
                        {ent.title ? `: ${ent.title}` : ''}
                        {ent.age_days !== undefined ? ` (${ent.age_days}d old)` : ''}
                      </span>
                      {ent.url && (
                        <a
                          href={ent.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                        >
                          <span>View</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Timestamps */}
            <div className="text-[11px] text-gray-500 pt-3 border-t border-gray-800 flex flex-wrap gap-4">
              <span>Detected: {new Date(selectedRisk.detected_at).toLocaleString()}</span>
              {selectedRisk.acknowledged_at && (
                <span>Acknowledged: {new Date(selectedRisk.acknowledged_at).toLocaleString()}</span>
              )}
              {selectedRisk.resolved_at && (
                <span className="text-emerald-400">Resolved: {new Date(selectedRisk.resolved_at).toLocaleString()}</span>
              )}
            </div>

            {/* Actions Footer */}
            <div className="flex items-center justify-end space-x-2 pt-2">
              {selectedRisk.status === 'OPEN' && (
                <button
                  onClick={() => handleAcknowledge(selectedRisk.id)}
                  disabled={transitionLoading}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors"
                >
                  Acknowledge Risk
                </button>
              )}
              {selectedRisk.status !== 'RESOLVED' && (
                <button
                  onClick={() => handleResolve(selectedRisk.id)}
                  disabled={transitionLoading}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors"
                >
                  Mark as Resolved
                </button>
              )}
              <button
                onClick={() => setSelectedRisk(null)}
                className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
