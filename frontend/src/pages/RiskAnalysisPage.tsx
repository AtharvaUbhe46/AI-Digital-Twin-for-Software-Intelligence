import React, { useEffect, useState } from 'react';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import {
  ShieldAlert, ShieldCheck, AlertTriangle, AlertOctagon,
  Info, TrendingDown, Users, GitCommit, GitPullRequest,
  AlertCircle, ChevronRight, ExternalLink
} from 'lucide-react';
import { Project, RiskAnalysisData, RiskItem } from '../types';
import { apiService } from '../services/api';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

const SEVERITY_COLORS = {
  critical: { text: 'text-red-400', bg: 'bg-red-900/30', border: 'border-red-800', badge: 'bg-red-900/60 text-red-300', icon: AlertOctagon, dot: '#ef4444' },
  high: { text: 'text-orange-400', bg: 'bg-orange-900/20', border: 'border-orange-800', badge: 'bg-orange-900/60 text-orange-300', icon: AlertTriangle, dot: '#f97316' },
  medium: { text: 'text-amber-400', bg: 'bg-amber-900/20', border: 'border-amber-800', badge: 'bg-amber-900/60 text-amber-300', icon: AlertCircle, dot: '#f59e0b' },
  low: { text: 'text-blue-400', bg: 'bg-blue-900/20', border: 'border-blue-800', badge: 'bg-blue-900/60 text-blue-300', icon: Info, dot: '#3b82f6' },
};

const RISK_LEVEL_COLORS = { critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#10b981' };

const RiskCard: React.FC<{ risk: RiskItem }> = ({ risk }) => {
  const styles = SEVERITY_COLORS[risk.severity];
  const Icon = styles.icon;
  return (
    <div className={`p-4 rounded-xl border ${styles.border} ${styles.bg} space-y-2`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start space-x-2">
          <Icon className={`w-4 h-4 ${styles.text} shrink-0 mt-0.5`} />
          <div>
            <h4 className={`text-sm font-semibold ${styles.text}`}>{risk.title}</h4>
            <span className="text-xs text-gray-500">{risk.category} · {risk.affected_area}</span>
          </div>
        </div>
        <span className={`shrink-0 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${styles.badge}`}>
          {risk.severity}
        </span>
      </div>
      <p className="text-xs text-gray-300 leading-relaxed">{risk.description}</p>
      <div className="flex items-center space-x-1.5 text-xs text-gray-500 bg-gray-900/50 rounded-lg px-3 py-2">
        <ChevronRight className="w-3 h-3 text-cyan-500" />
        <span className="text-gray-300">{risk.recommendation}</span>
      </div>
      <div className="flex items-center space-x-2 text-xs">
        <span className="text-gray-500">Signal:</span>
        <span className={`font-mono font-semibold ${styles.text}`}>{risk.signal_value}</span>
      </div>
    </div>
  );
};

export const RiskAnalysisPage: React.FC<Props> = ({ activeProject, onOpenConnectModal }) => {
  const [data, setData] = useState<RiskAnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');

  useEffect(() => {
    if (!activeProject) { setLoading(false); return; }
    setLoading(true);
    apiService.getRiskAnalysis(activeProject.id)
      .then(d => { setData(d); setError(null); })
      .catch(e => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [activeProject?.id]);

  if (!activeProject) return (
    <div className="flex flex-col items-center justify-center h-64 space-y-3 text-center">
      <ShieldAlert className="w-10 h-10 text-gray-600" />
      <p className="text-gray-400">No repository connected. <button onClick={onOpenConnectModal} className="text-cyan-400 underline">Connect one</button></p>
    </div>
  );

  if (loading) return <div className="space-y-4 animate-pulse">{[...Array(4)].map((_, i) => <div key={i} className="h-28 bg-gray-800/50 rounded-xl" />)}</div>;
  if (error || !data) return <div className="p-6 rounded-xl border border-red-800 bg-red-900/20 text-red-300">{error || 'Failed to load risk analysis.'}</div>;

  const riskColor = RISK_LEVEL_COLORS[data.overall_risk_level];
  const filtered = filter === 'all' ? data.risks : data.risks.filter(r => r.severity === filter);

  const severityPieData = [
    { name: 'Critical', value: data.severity_summary.critical, fill: '#ef4444' },
    { name: 'High', value: data.severity_summary.high, fill: '#f97316' },
    { name: 'Medium', value: data.severity_summary.medium, fill: '#f59e0b' },
    { name: 'Low', value: data.severity_summary.low, fill: '#3b82f6' },
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Risk Detection</h1>
          <p className="text-sm text-gray-400 mt-1">{activeProject.full_name} · Pattern-based risk signals</p>
        </div>
        <div className="flex items-center space-x-3 px-4 py-2.5 rounded-xl bg-gray-800/60 border border-gray-700">
          {data.risk_count === 0
            ? <ShieldCheck className="w-5 h-5 text-emerald-400" />
            : <ShieldAlert className="w-5 h-5" style={{ color: riskColor }} />}
          <div>
            <p className="text-xs text-gray-400">Overall Risk</p>
            <p className="font-bold uppercase text-sm" style={{ color: riskColor }}>{data.overall_risk_level}</p>
          </div>
        </div>
      </div>

      {/* Summary Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(['critical', 'high', 'medium', 'low'] as const).map(sev => {
          const styles = SEVERITY_COLORS[sev];
          const count = data.severity_summary[sev];
          return (
            <button
              key={sev}
              onClick={() => setFilter(filter === sev ? 'all' : sev)}
              className={`p-4 rounded-xl border text-left transition-all ${styles.border} ${styles.bg} ${filter === sev ? 'ring-2 ring-offset-1 ring-offset-[#0b0f17]' : ''}`}
              style={{ '--tw-ring-color': styles.dot } as any}
            >
              <p className="text-xs text-gray-400 uppercase tracking-wide">{sev}</p>
              <p className={`text-3xl font-black ${styles.text}`}>{count}</p>
              <p className="text-xs text-gray-500">{count === 1 ? 'risk' : 'risks'}</p>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Charts */}
        <div className="space-y-4">
          {/* Severity Pie */}
          {severityPieData.length > 0 && (
            <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Risk Distribution</h3>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={severityPieData} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={4} dataKey="value">
                    {severityPieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Issue Trend */}
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">Issue Trend (8 Weeks)</h3>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={data.issue_trend} barGap={2}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="week" tick={{ fill: '#6b7280', fontSize: 10 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
                <Bar dataKey="opened" name="Opened" fill="#f59e0b" radius={3} />
                <Bar dataKey="closed" name="Closed" fill="#10b981" radius={3} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Contributor concentration */}
          {data.contributor_concentration.length > 0 && (
            <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Contributor Concentration</h3>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={data.contributor_concentration} cx="50%" cy="50%" outerRadius={60} dataKey="value" nameKey="name" label={({ name }) => name}>
                    {data.contributor_concentration.map((_, i) => (
                      <Cell key={i} fill={['#06b6d4', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#3b82f6'][i % 6]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Risk Cards */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-300">
              {filtered.length} Risk{filtered.length !== 1 ? 's' : ''} {filter !== 'all' && `(${filter})`}
            </h3>
            {filter !== 'all' && (
              <button onClick={() => setFilter('all')} className="text-xs text-cyan-400 hover:underline">Clear filter</button>
            )}
          </div>
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-2 text-center bg-[#111827] border border-gray-800 rounded-xl">
              <ShieldCheck className="w-10 h-10 text-emerald-500" />
              <p className="text-gray-300 font-medium">No {filter !== 'all' ? filter : ''} risks detected</p>
              <p className="text-xs text-gray-500">All signals look healthy for this repository.</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[650px] overflow-y-auto pr-1">
              {filtered.map(risk => <RiskCard key={risk.id} risk={risk} />)}
            </div>
          )}
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 grid grid-cols-2 md:grid-cols-5 gap-3 text-center">
        {[
          { label: 'Commits', val: data.metadata.total_commits, icon: <GitCommit className="w-4 h-4 text-cyan-400 mx-auto mb-1" /> },
          { label: 'Contributors', val: data.metadata.total_contributors, icon: <Users className="w-4 h-4 text-violet-400 mx-auto mb-1" /> },
          { label: 'Issues', val: data.metadata.total_issues, icon: <AlertCircle className="w-4 h-4 text-amber-400 mx-auto mb-1" /> },
          { label: 'PRs', val: data.metadata.total_prs, icon: <GitPullRequest className="w-4 h-4 text-emerald-400 mx-auto mb-1" /> },
          { label: 'Health Score', val: `${data.metadata.health_score}/100`, icon: <TrendingDown className="w-4 h-4 text-blue-400 mx-auto mb-1" /> },
        ].map((m, i) => (
          <div key={i}>
            {m.icon}
            <p className="text-lg font-bold text-white">{m.val}</p>
            <p className="text-xs text-gray-500">{m.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
