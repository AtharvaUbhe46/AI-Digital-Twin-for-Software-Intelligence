import React, { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { GitCommit, Users, Tag, Calendar, TrendingUp, GitMerge, Clock } from 'lucide-react';
import { Project, EvolutionData } from '../types';
import { apiService } from '../services/api';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

export const SoftwareEvolutionPage: React.FC<Props> = ({ activeProject, onOpenConnectModal }) => {
  const [data, setData] = useState<EvolutionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  if (loading) return <div className="space-y-4 animate-pulse">{[...Array(3)].map((_, i) => <div key={i} className="h-48 bg-gray-800/50 rounded-xl" />)}</div>;
  if (error || !data) return <div className="p-6 rounded-xl border border-red-800 bg-red-900/20 text-red-300">{error || 'Failed to load evolution data.'}</div>;

  const EVENT_ICONS: Record<string, React.ReactNode> = {
    project_start: <Clock className="w-3 h-3" />,
    release: <Tag className="w-3 h-3" />,
    sync: <GitCommit className="w-3 h-3" />,
  };

  const EVENT_COLORS: Record<string, string> = {
    project_start: 'bg-cyan-900 border-cyan-700 text-cyan-400',
    release: 'bg-emerald-900 border-emerald-700 text-emerald-400',
    sync: 'bg-violet-900 border-violet-700 text-violet-400',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Software Evolution</h1>
          <p className="text-sm text-gray-400 mt-1">{data.project_name} · Historical activity analysis</p>
        </div>
      </div>

      {/* Totals */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Total Commits', value: data.totals.total_commits, icon: <GitCommit className="w-4 h-4 text-cyan-400" />, color: 'bg-cyan-900/40' },
          { label: 'Total Releases', value: data.totals.total_releases, icon: <Tag className="w-4 h-4 text-emerald-400" />, color: 'bg-emerald-900/40' },
          { label: 'Merged PRs', value: data.totals.total_merged_prs, icon: <GitMerge className="w-4 h-4 text-violet-400" />, color: 'bg-violet-900/40' },
          { label: 'Contributors', value: data.totals.total_contributors, icon: <Users className="w-4 h-4 text-amber-400" />, color: 'bg-amber-900/40' },
        ].map((s, i) => (
          <div key={i} className="bg-[#111827] border border-gray-800 rounded-xl p-4 flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${s.color}`}>{s.icon}</div>
            <div>
              <p className="text-xl font-bold text-white">{s.value}</p>
              <p className="text-xs text-gray-400">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Monthly Activity Chart */}
      {data.monthly_activity.length > 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <span>Monthly Commit & PR Activity</span>
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data.monthly_activity}>
              <defs>
                <linearGradient id="commitsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="prsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="month" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
              <Area type="monotone" dataKey="commits" name="Commits" stroke="#06b6d4" fill="url(#commitsGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="merged_prs" name="Merged PRs" stroke="#8b5cf6" fill="url(#prsGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Contributor Growth */}
      {data.contributor_growth.length > 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
            <Users className="w-4 h-4 text-violet-400" />
            <span>Contributor Growth Over Time</span>
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data.contributor_growth}>
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

      {/* Timeline */}
      {data.timeline_events.length > 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-amber-400" />
            <span>Project Lifecycle Timeline</span>
          </h3>
          <div className="relative">
            <div className="absolute left-3 top-0 bottom-0 w-px bg-gray-700" />
            <div className="space-y-4 pl-8">
              {data.timeline_events.map((evt, i) => {
                const colorClass = EVENT_COLORS[evt.type] || 'bg-gray-800 border-gray-700 text-gray-400';
                const icon = EVENT_ICONS[evt.type] || <Calendar className="w-3 h-3" />;
                return (
                  <div key={i} className="relative">
                    <div className={`absolute -left-[26px] top-0.5 w-5 h-5 rounded-full border flex items-center justify-center ${colorClass}`}>
                      {icon}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-200 font-medium">{evt.label}</span>
                      {evt.date && (
                        <span className="text-xs text-gray-500">{new Date(evt.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                      )}
                    </div>
                    {(evt as any).name && (evt as any).name !== evt.label && (
                      <p className="text-xs text-gray-500 mt-0.5">{(evt as any).name}</p>
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
