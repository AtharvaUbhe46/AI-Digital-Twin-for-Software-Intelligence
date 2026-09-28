import React, { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell
} from 'recharts';
import {
  GitCommit, Users, Tag, Calendar, TrendingUp, GitMerge, Clock,
  GitPullRequest, AlertCircle, Activity, Zap
} from 'lucide-react';
import { Project, EvolutionData } from '../types';
import { apiService } from '../services/api';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

const COLORS = ['#06b6d4', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

// Velocity gauge component
const VelocityGauge: React.FC<{ score: number; rating: string }> = ({ score, rating }) => {
  const color = rating === 'High' ? '#10b981' : rating === 'Moderate' ? '#f59e0b' : '#6b7280';
  const circumference = 2 * Math.PI * 40;
  const dashOffset = circumference - (score / 100) * circumference;
  return (
    <div className="flex flex-col items-center justify-center">
      <svg width="110" height="110" viewBox="0 0 110 110">
        <circle cx="55" cy="55" r="40" fill="none" stroke="#1f2937" strokeWidth="10" />
        <circle
          cx="55" cy="55" r="40" fill="none"
          stroke={color} strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform="rotate(-90 55 55)"
          style={{ transition: 'stroke-dashoffset 1s ease' }}
        />
        <text x="55" y="51" textAnchor="middle" fill="white" fontSize="20" fontWeight="bold">
          {score.toFixed(0)}
        </text>
        <text x="55" y="67" textAnchor="middle" fill={color} fontSize="10">
          {rating}
        </text>
      </svg>
      <p className="text-xs text-gray-400 mt-1">Velocity Score</p>
    </div>
  );
};

export const SoftwareEvolutionPage: React.FC<Props> = ({ activeProject, onOpenConnectModal }) => {
  const [data, setData] = useState<EvolutionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTimeTab, setActiveTimeTab] = useState<'weekly' | 'monthly'>('monthly');

  useEffect(() => {
    if (!activeProject) { setLoading(false); return; }
    setLoading(true);
    apiService.getEvolution(activeProject.id)
      .then(d => { setData(d); setError(null); })
      .catch(e => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [activeProject?.id]);

  if (!activeProject) return (
    <div className="flex flex-col items-center justify-center h-64 space-y-3 text-center">
      <TrendingUp className="w-10 h-10 text-gray-600" />
      <p className="text-gray-400">No repository connected. <button onClick={onOpenConnectModal} className="text-cyan-400 underline">Connect one</button></p>
    </div>
  );

  if (loading) return (
    <div className="space-y-4 animate-pulse">
      {[...Array(4)].map((_, i) => <div key={i} className="h-48 bg-gray-800/50 rounded-xl" />)}
    </div>
  );
  if (error || !data) return (
    <div className="p-6 rounded-xl border border-red-800 bg-red-900/20 text-red-300">
      {error || 'Failed to load evolution data.'}
    </div>
  );

  // Normalise monthly_activity: backend returns date_label + commits + prs
  const monthlyChartData = (data.monthly_activity || []).map((m: any) => ({
    month: m.date_label || m.month || m.period || '',
    commits: m.commits || 0,
    merged_prs: m.prs || m.merged_prs || 0,
    issues: m.issues || 0,
    contributors: m.contributors || 0,
  }));

  const contributorGrowth = (data.contributor_growth || []).map((g: any) => ({
    month: g.month || g.date_label || '',
    new_contributors: g.new_contributors || 0,
    total_contributors: g.total_contributors || 0,
  }));

  // Timeline events
  const timelineEvents = (data.timeline_events || []).slice(0, 15);

  // Velocity from raw data if available
  const velocity = (data as any).velocity_indicator;

  const EVENT_COLORS: Record<string, string> = {
    commit: 'bg-cyan-900 border-cyan-700 text-cyan-400',
    release: 'bg-emerald-900 border-emerald-700 text-emerald-400',
    pr_merge: 'bg-violet-900 border-violet-700 text-violet-400',
    pr_open: 'bg-blue-900 border-blue-700 text-blue-400',
    pr_close: 'bg-gray-800 border-gray-700 text-gray-400',
    issue_open: 'bg-amber-900 border-amber-700 text-amber-400',
    issue_close: 'bg-rose-900 border-rose-700 text-rose-400',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Software Evolution</h1>
          <p className="text-sm text-gray-400 mt-1">{data.project_name} · Historical activity analysis</p>
        </div>
        <div className="px-3 py-1.5 rounded-lg bg-emerald-900/30 border border-emerald-700/50 text-emerald-400 text-xs font-semibold">
          Phase 6 Active
        </div>
      </div>

      {/* Top Stats + Velocity Gauge */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Stats */}
        <div className="lg:col-span-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Total Commits', value: data.totals?.total_commits ?? 0, icon: <GitCommit className="w-4 h-4 text-cyan-400" />, color: 'bg-cyan-900/40 border-cyan-800/40' },
            { label: 'Total Releases', value: data.totals?.total_releases ?? 0, icon: <Tag className="w-4 h-4 text-emerald-400" />, color: 'bg-emerald-900/40 border-emerald-800/40' },
            { label: 'Merged PRs', value: data.totals?.total_merged_prs ?? 0, icon: <GitMerge className="w-4 h-4 text-violet-400" />, color: 'bg-violet-900/40 border-violet-800/40' },
            { label: 'Contributors', value: data.totals?.total_contributors ?? 0, icon: <Users className="w-4 h-4 text-amber-400" />, color: 'bg-amber-900/40 border-amber-800/40' },
          ].map((s, i) => (
            <div key={i} className={`bg-[#111827] border rounded-xl p-4 flex items-center space-x-3 ${s.color}`}>
              <div className={`p-2 rounded-lg ${s.color}`}>{s.icon}</div>
              <div>
                <p className="text-xl font-bold text-white">{s.value.toLocaleString()}</p>
                <p className="text-xs text-gray-400">{s.label}</p>
              </div>
            </div>
          ))}
          {/* Open metrics row */}
          {[
            { label: 'Open Issues', value: (data as any).totals?.open_issues ?? 0, icon: <AlertCircle className="w-4 h-4 text-rose-400" />, color: 'bg-rose-900/40 border-rose-800/40' },
            { label: 'Open PRs', value: (data as any).totals?.open_prs ?? 0, icon: <GitPullRequest className="w-4 h-4 text-blue-400" />, color: 'bg-blue-900/40 border-blue-800/40' },
            { label: 'Recent (30d)', value: (velocity?.evidence?.recent_commits_30d) ?? '—', icon: <Activity className="w-4 h-4 text-cyan-400" />, color: 'bg-cyan-900/30 border-cyan-800/30' },
            { label: 'Merged PRs 30d', value: (velocity?.evidence?.merged_prs_30d) ?? '—', icon: <Zap className="w-4 h-4 text-yellow-400" />, color: 'bg-yellow-900/30 border-yellow-800/30' },
          ].map((s, i) => (
            <div key={i} className={`bg-[#111827] border rounded-xl p-4 flex items-center space-x-3 ${s.color}`}>
              <div className={`p-2 rounded-lg ${s.color}`}>{s.icon}</div>
              <div>
                <p className="text-xl font-bold text-white">{typeof s.value === 'number' ? s.value.toLocaleString() : s.value}</p>
                <p className="text-xs text-gray-400">{s.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Velocity Gauge */}
        {velocity && (
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 flex flex-col items-center justify-center space-y-2">
            <VelocityGauge score={velocity.score} rating={velocity.rating} />
            <p className="text-[10px] text-gray-500 text-center leading-tight px-2">{velocity.interpretation?.slice(0, 80)}…</p>
          </div>
        )}
      </div>

      {/* Monthly Activity Chart */}
      {monthlyChartData.length > 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center space-x-2">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <span>Commit & PR Activity Over Time</span>
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={monthlyChartData}>
              <defs>
                <linearGradient id="commitsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="prsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="issuesGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="month" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
              <Area type="monotone" dataKey="commits" name="Commits" stroke="#06b6d4" fill="url(#commitsGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="merged_prs" name="Merged PRs" stroke="#8b5cf6" fill="url(#prsGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="issues" name="Issues" stroke="#f59e0b" fill="url(#issuesGrad)" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Contributor Growth */}
        {contributorGrowth.length > 0 && (
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
              <Users className="w-4 h-4 text-violet-400" />
              <span>Contributor Growth</span>
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={contributorGrowth}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="month" tick={{ fill: '#6b7280', fontSize: 10 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
                <Line type="monotone" dataKey="total_contributors" name="Total Contributors" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="new_contributors" name="New Contributors" stroke="#06b6d4" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Release Milestones */}
        {data.release_milestones && data.release_milestones.length > 0 && (
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
              <Tag className="w-4 h-4 text-emerald-400" />
              <span>Release Milestones</span>
            </h3>
            <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
              {data.release_milestones.slice(0, 12).map((r: any, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-gray-800/40 border border-gray-700/40">
                  <div className="flex items-center space-x-2">
                    <Tag className="w-3 h-3 text-emerald-400 shrink-0" />
                    <span className="text-xs text-gray-200 font-mono">{r.tag || r.label}</span>
                    {r.is_prerelease && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-amber-900/50 border border-amber-700/50 text-amber-400">pre</span>
                    )}
                  </div>
                  {r.date && (
                    <span className="text-[11px] text-gray-500">
                      {new Date(r.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' })}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Timeline */}
      {timelineEvents.length > 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-amber-400" />
            <span>Recent Activity Timeline (30d)</span>
          </h3>
          <div className="relative">
            <div className="absolute left-3 top-0 bottom-0 w-px bg-gray-700" />
            <div className="space-y-3 pl-8">
              {timelineEvents.map((evt: any, i) => {
                const colorClass = EVENT_COLORS[evt.type] || 'bg-gray-800 border-gray-700 text-gray-400';
                return (
                  <div key={i} className="relative">
                    <div className={`absolute -left-[26px] top-0.5 w-5 h-5 rounded-full border flex items-center justify-center text-[9px] font-bold ${colorClass}`}>
                      {evt.type === 'commit' ? '●' : evt.type === 'release' ? '◆' : '▶'}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-200 font-medium truncate max-w-[70%]">{evt.label}</span>
                      {evt.date && (
                        <span className="text-[11px] text-gray-500 shrink-0 ml-2">
                          {new Date(evt.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                        </span>
                      )}
                    </div>
                    {evt.actor_login && (
                      <p className="text-[10px] text-gray-500 mt-0.5">by @{evt.actor_login}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
