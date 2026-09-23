import React, { useEffect, useState } from 'react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip
} from 'recharts';
import {
  Wrench, Clock, GitBranch, Bug, FileText, GitPullRequest,
  AlertTriangle, TrendingDown, CheckCircle, ChevronRight
} from 'lucide-react';
import { Project, TechnicalDebtData, DebtCategory, RefactoringCandidate } from '../types';
import { apiService } from '../services/api';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

const ICON_MAP: Record<string, React.ReactNode> = {
  bug: <Bug className="w-4 h-4" />,
  'git-pull-request': <GitPullRequest className="w-4 h-4" />,
  'git-branch': <GitBranch className="w-4 h-4" />,
  'refresh-cw': <Bug className="w-4 h-4" />,
  'file-text': <FileText className="w-4 h-4" />,
};

const PRIORITY_STYLES: Record<string, string> = {
  high: 'text-red-400 bg-red-900/30 border-red-800',
  medium: 'text-amber-400 bg-amber-900/30 border-amber-800',
  low: 'text-blue-400 bg-blue-900/30 border-blue-800',
};

const DEBT_COLORS = ['#ef4444', '#f97316', '#f59e0b', '#8b5cf6', '#06b6d4'];

const DebtCategoryCard: React.FC<{ cat: DebtCategory; index: number }> = ({ cat, index }) => {
  const pct = cat.score;
  const color = pct > 60 ? '#ef4444' : pct > 30 ? '#f59e0b' : '#10b981';
  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="text-gray-400">{ICON_MAP[cat.icon] || <Wrench className="w-4 h-4" />}</div>
          <span className="text-sm font-semibold text-gray-200">{cat.category}</span>
        </div>
        <span className="text-lg font-black" style={{ color }}>{pct.toFixed(0)}</span>
      </div>
      <div className="h-1.5 bg-gray-700/60 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
      <p className="text-xs text-gray-400">{cat.description}</p>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{cat.items} items</span>
        <span className="text-amber-400 font-medium">~{cat.estimated_hours}h to resolve</span>
      </div>
    </div>
  );
};

const RefactoringCard: React.FC<{ cand: RefactoringCandidate }> = ({ cand }) => (
  <div className={`p-3.5 rounded-xl border ${PRIORITY_STYLES[cand.priority]}`}>
    <div className="flex items-center justify-between mb-1.5">
      <span className="text-sm font-semibold">{cand.area}</span>
      <span className="text-[10px] uppercase font-bold tracking-wide px-1.5 py-0.5 rounded border">{cand.priority}</span>
    </div>
    <p className="text-xs text-gray-300">{cand.description}</p>
    <div className="flex items-center space-x-1 mt-2 text-xs text-gray-500">
      <Clock className="w-3 h-3" />
      <span>Estimated effort: <span className="text-gray-300 font-medium">{cand.effort}</span></span>
    </div>
  </div>
);

export const TechnicalDebtPage: React.FC<Props> = ({ activeProject, onOpenConnectModal }) => {
  const [data, setData] = useState<TechnicalDebtData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeProject) { setLoading(false); return; }
    setLoading(true);
    apiService.getTechnicalDebt(activeProject.id)
      .then(d => { setData(d); setError(null); })
      .catch(e => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [activeProject?.id]);

  if (!activeProject) return (
    <div className="flex flex-col items-center justify-center h-64 space-y-3 text-center">
      <Wrench className="w-10 h-10 text-gray-600" />
      <p className="text-gray-400">No repository connected. <button onClick={onOpenConnectModal} className="text-cyan-400 underline">Connect one</button></p>
    </div>
  );

  if (loading) return <div className="space-y-4 animate-pulse">{[...Array(3)].map((_, i) => <div key={i} className="h-36 bg-gray-800/50 rounded-xl" />)}</div>;
  if (error || !data) return <div className="p-6 rounded-xl border border-red-800 bg-red-900/20 text-red-300">{error || 'Failed to load debt data.'}</div>;

  const debtColor = data.debt_level === 'high' ? '#ef4444' : data.debt_level === 'medium' ? '#f59e0b' : '#10b981';

  const radarData = data.debt_categories.map(cat => ({
    subject: cat.category.replace(' (Fix Rate)', '').replace(' Proliferation', ''),
    score: cat.score,
    fullMark: 100,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Technical Debt</h1>
          <p className="text-sm text-gray-400 mt-1">{activeProject.full_name} · Debt signal analysis</p>
        </div>
        <div className="text-right px-4 py-2.5 rounded-xl bg-gray-800/60 border border-gray-700">
          <p className="text-xs text-gray-400">Debt Score</p>
          <p className="text-3xl font-black" style={{ color: debtColor }}>{data.overall_debt_score.toFixed(1)}</p>
          <p className="text-xs uppercase font-bold" style={{ color: debtColor }}>{data.debt_level} debt</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Estimated Debt Hours', value: `${data.total_estimated_debt_hours}h`, icon: <Clock className="w-4 h-4 text-red-400" />, color: 'bg-red-900/30' },
          { label: 'Fix Commits', value: `${data.metrics.fix_commits} (${data.metrics.fix_ratio_pct}%)`, icon: <Bug className="w-4 h-4 text-amber-400" />, color: 'bg-amber-900/30' },
          { label: 'Stale Issues', value: data.metrics.stale_issues, icon: <AlertTriangle className="w-4 h-4 text-orange-400" />, color: 'bg-orange-900/30' },
          { label: 'Extra Branches', value: data.metrics.non_default_branches, icon: <GitBranch className="w-4 h-4 text-violet-400" />, color: 'bg-violet-900/30' },
        ].map((s, i) => (
          <div key={i} className="bg-[#111827] border border-gray-800 rounded-xl p-4 flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${s.color}`}>{s.icon}</div>
            <div>
              <p className="text-sm font-bold text-white">{s.value}</p>
              <p className="text-xs text-gray-400">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Radar Chart */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Debt Radar</h3>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 10 }} />
              <Radar name="Debt Score" dataKey="score" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.2} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>

          {/* Commit Type Pie */}
          {data.commit_type_breakdown.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-300 mt-4 mb-3">Commit Type Mix</h3>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={data.commit_type_breakdown} dataKey="count" nameKey="type" cx="50%" cy="50%" outerRadius={60} label={({ type }) => type}>
                    {data.commit_type_breakdown.map((_, i) => (
                      <Cell key={i} fill={DEBT_COLORS[i % DEBT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
                </PieChart>
              </ResponsiveContainer>
            </>
          )}
        </div>

        {/* Debt Categories */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-sm font-semibold text-gray-300">Debt Category Breakdown</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.debt_categories.map((cat, i) => <DebtCategoryCard key={i} cat={cat} index={i} />)}
          </div>
        </div>
      </div>

      {/* Refactoring Queue */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
          <TrendingDown className="w-4 h-4 text-cyan-400" />
          <span>Refactoring Priority Queue</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.refactoring_candidates.map((cand, i) => <RefactoringCard key={i} cand={cand} />)}
        </div>
      </div>
    </div>
  );
};
