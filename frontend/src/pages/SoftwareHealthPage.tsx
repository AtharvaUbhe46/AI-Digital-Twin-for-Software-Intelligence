import React, { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import {
  Activity, GitCommit, AlertCircle, GitPullRequest, Users,
  Star, GitFork, Clock, TrendingUp, Award, Tag, RefreshCw
} from 'lucide-react';
import { Project, SoftwareHealthData, HealthIndexComponent } from '../types';
import { apiService } from '../services/api';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

const COLORS = ['#06b6d4', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#ec4899', '#84cc16'];

const StatBox: React.FC<{ label: string; value: string | number; sub?: string; icon: React.ReactNode; color: string }> = ({
  label, value, sub, icon, color
}) => (
  <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 flex items-start space-x-3">
    <div className={`p-2 rounded-lg ${color} shrink-0`}>{icon}</div>
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  </div>
);

const HealthBar: React.FC<{ component: HealthIndexComponent }> = ({ component }) => {
  const pct = (component.score / component.max_score) * 100;
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-gray-300 font-medium">{component.name}</span>
        <span className="text-sm font-bold text-white">{component.score}/{component.max_score}</span>
      </div>
      <div className="h-2 bg-gray-700/60 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-gray-500 mt-1">{component.detail}</p>
    </div>
  );
};

export const SoftwareHealthPage: React.FC<Props> = ({ activeProject, onOpenConnectModal }) => {
  const [data, setData] = useState<SoftwareHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeProject) { setLoading(false); return; }
    setLoading(true);
    apiService.getSoftwareHealth(activeProject.id)
      .then(d => { setData(d); setError(null); })
      .catch(e => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [activeProject?.id]);

  if (!activeProject) return (
    <div className="flex flex-col items-center justify-center h-64 space-y-3 text-center">
      <Activity className="w-10 h-10 text-gray-600" />
      <p className="text-gray-400">No repository connected. <button onClick={onOpenConnectModal} className="text-cyan-400 underline">Connect one</button></p>
    </div>
  );

  if (loading) return (
    <div className="space-y-4 animate-pulse">
      {[...Array(3)].map((_, i) => <div key={i} className="h-32 bg-gray-800/50 rounded-xl" />)}
    </div>
  );

  if (error || !data) return (
    <div className="p-6 rounded-xl border border-red-800 bg-red-900/20 text-red-300">{error || 'Failed to load health data.'}</div>
  );

  const healthScore = data.health_score;
  const healthColor = healthScore >= 75 ? 'text-emerald-400' : healthScore >= 50 ? 'text-amber-400' : 'text-red-400';
  const healthRing = healthScore >= 75 ? '#10b981' : healthScore >= 50 ? '#f59e0b' : '#ef4444';

  const m = data.metrics;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Software Health</h1>
          <p className="text-sm text-gray-400 mt-1">{activeProject.full_name} · Real-time analysis</p>
        </div>
        <div className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gray-800/60 border border-gray-700">
          <div className={`text-4xl font-black ${healthColor}`}>{healthScore.toFixed(1)}</div>
          <div className="text-gray-400 text-xs">/100<br/>Health Score</div>
        </div>
      </div>

      {/* Stat Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatBox label="Total Commits" value={m.total_commits} sub={`${m.recent_commits_30d} this month`} icon={<GitCommit className="w-4 h-4 text-cyan-400" />} color="bg-cyan-900/40" />
        <StatBox label="Open Issues" value={m.open_issues} sub={`${m.closed_issues} closed`} icon={<AlertCircle className="w-4 h-4 text-amber-400" />} color="bg-amber-900/40" />
        <StatBox label="PR Merge Rate" value={`${m.pr_merge_rate_pct}%`} sub={`${m.merged_prs}/${m.total_prs} merged`} icon={<GitPullRequest className="w-4 h-4 text-violet-400" />} color="bg-violet-900/40" />
        <StatBox label="Contributors" value={m.total_contributors} sub={`${m.stars} stars · ${m.forks} forks`} icon={<Users className="w-4 h-4 text-emerald-400" />} color="bg-emerald-900/40" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Health Index Breakdown */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
            <Award className="w-4 h-4 text-cyan-400" />
            <span>Health Index Breakdown</span>
          </h3>
          {data.health_index?.components?.map((c, i) => <HealthBar key={i} component={c} />) || (
            <p className="text-gray-500 text-sm">Sync the project to compute index.</p>
          )}
          {data.health_index?.formula && (
            <p className="text-xs text-gray-600 border-t border-gray-800 pt-3 mt-2">{data.health_index.formula}</p>
          )}
        </div>

        {/* Weekly Commit Activity */}
        <div className="lg:col-span-2 bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <span>Commit Activity (Last 8 Weeks)</span>
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data.weekly_commits}>
              <defs>
                <linearGradient id="commitGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="week" tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
              <Area type="monotone" dataKey="commits" stroke="#06b6d4" fill="url(#commitGrad)" strokeWidth={2} dot={{ fill: '#06b6d4', r: 3 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Commit Distribution by Author */}
        {data.commit_distribution.length > 0 && (
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
              <GitCommit className="w-4 h-4 text-violet-400" />
              <span>Commits by Author</span>
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={data.commit_distribution} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }} />
                <YAxis type="category" dataKey="author" tick={{ fill: '#9ca3af', fontSize: 11 }} width={80} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
                <Bar dataKey="commits" radius={4}>
                  {data.commit_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Issue Labels */}
        {data.top_issue_labels.length > 0 && (
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <span>Top Issue Labels</span>
            </h3>
            <div className="space-y-2">
              {data.top_issue_labels.map((lbl, i) => {
                const max = data.top_issue_labels[0].count;
                return (
                  <div key={i} className="flex items-center space-x-3">
                    <span className="text-xs text-gray-400 w-28 truncate">{lbl.label}</span>
                    <div className="flex-1 h-2 bg-gray-700/60 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${(lbl.count / max) * 100}%`, background: COLORS[i % COLORS.length] }} />
                    </div>
                    <span className="text-xs text-gray-300 w-6 text-right">{lbl.count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Releases */}
      {data.release_timeline.length > 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
            <Tag className="w-4 h-4 text-emerald-400" />
            <span>Release History</span>
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.release_timeline.map((r, i) => (
              <a
                key={i}
                href={r.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 hover:border-cyan-600 transition-colors text-xs text-gray-300"
              >
                <Tag className="w-3 h-3 text-emerald-400" />
                <span className="font-mono">{r.tag}</span>
                {r.is_prerelease && <span className="px-1.5 rounded bg-amber-900/50 text-amber-400 text-[10px]">pre</span>}
                {r.date && <span className="text-gray-500">{new Date(r.date).toLocaleDateString()}</span>}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Avg times */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 text-center">
          <Clock className="w-5 h-5 text-cyan-400 mx-auto mb-1" />
          <p className="text-2xl font-bold text-white">{m.avg_issue_resolution_hours > 0 ? `${m.avg_issue_resolution_hours}h` : 'N/A'}</p>
          <p className="text-xs text-gray-400">Avg. Issue Resolution Time</p>
        </div>
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 text-center">
          <GitPullRequest className="w-5 h-5 text-violet-400 mx-auto mb-1" />
          <p className="text-2xl font-bold text-white">{m.avg_pr_merge_hours > 0 ? `${m.avg_pr_merge_hours}h` : 'N/A'}</p>
          <p className="text-xs text-gray-400">Avg. PR Merge Time</p>
        </div>
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 text-center">
          <RefreshCw className="w-5 h-5 text-emerald-400 mx-auto mb-1" />
          <p className="text-2xl font-bold text-white">{m.recent_commits_30d}</p>
          <p className="text-xs text-gray-400">Commits (Last 30 Days)</p>
        </div>
      </div>
    </div>
  );
};
