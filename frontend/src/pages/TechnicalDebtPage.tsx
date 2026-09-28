import React, { useEffect, useState } from 'react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip
} from 'recharts';
import {
  Wrench, Clock, GitBranch, Bug, FileText, GitPullRequest,
  AlertTriangle, TrendingDown, CheckCircle, Shield, Info
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
const LEVEL_COLORS: Record<string, string> = { high: '#ef4444', medium: '#f59e0b', low: '#10b981' };

const DebtCategoryCard: React.FC<{ cat: DebtCategory; index: number }> = ({ cat }) => {
  const pct = Math.min(100, Math.max(0, cat.score));
  const color = pct > 60 ? '#ef4444' : pct > 30 ? '#f59e0b' : '#10b981';
  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 space-y-3 hover:border-gray-700 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="text-gray-400">{ICON_MAP[cat.icon] || <Wrench className="w-4 h-4" />}</div>
          <span className="text-sm font-semibold text-gray-200">{cat.category}</span>
        </div>
        <span className="text-lg font-black" style={{ color }}>{pct.toFixed(0)}</span>
      </div>
      <div className="h-1.5 bg-gray-700/60 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}99, ${color})` }}
        />
      </div>
      <p className="text-xs text-gray-400 leading-relaxed">{cat.description}</p>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{cat.items} items</span>
        {cat.estimated_hours > 0 && (
          <span className="text-amber-400 font-medium">~{cat.estimated_hours}h to resolve</span>
        )}
      </div>
    </div>
  );
};

const RefactoringCard: React.FC<{ cand: RefactoringCandidate }> = ({ cand }) => (
  <div className={`p-3.5 rounded-xl border ${PRIORITY_STYLES[cand.priority] || PRIORITY_STYLES.low}`}>
    <div className="flex items-center justify-between mb-1.5">
      <span className="text-sm font-semibold">{cand.area}</span>
      <span className="text-[10px] uppercase font-bold tracking-wide px-1.5 py-0.5 rounded border">
        {cand.priority}
      </span>
    </div>
    <p className="text-xs text-gray-300 leading-relaxed">{cand.description}</p>
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

  if (loading) return (
    <div className="space-y-4 animate-pulse">
      {[...Array(3)].map((_, i) => <div key={i} className="h-36 bg-gray-800/50 rounded-xl" />)}
    </div>
  );
  if (error || !data) return (
    <div className="p-6 rounded-xl border border-red-800 bg-red-900/20 text-red-300">
      {error || 'Failed to load technical debt data.'}
    </div>
  );

  const debtScore = data.overall_debt_score ?? (data as any).composite_score ?? 0;
  const debtLevel = data.debt_level ?? (data as any).level ?? 'low';
  const debtColor = LEVEL_COLORS[debtLevel] || '#10b981';

  const categories = data.debt_categories || [];
  const radarData = categories.map(cat => ({
    subject: cat.category.replace(' (Fix Rate)', '').replace(' Proliferation', '').replace(' Indicator', ''),
    score: cat.score,
    fullMark: 100,
  }));

  const commitBreakdown = data.commit_type_breakdown || [];
  const refactoringQueue = data.refactoring_candidates || [];
  const metrics = data.metrics || {} as any;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Technical Debt Intelligence</h1>
          <p className="text-sm text-gray-400 mt-1">{activeProject.full_name} · Heuristic debt signal analysis</p>
        </div>
        <div className="text-right px-4 py-2.5 rounded-xl bg-gray-800/60 border border-gray-700">
          <p className="text-xs text-gray-400">Debt Score</p>
          <p className="text-3xl font-black" style={{ color: debtColor }}>{debtScore.toFixed(1)}</p>
          <p className="text-xs uppercase font-bold" style={{ color: debtColor }}>{debtLevel} debt</p>
        </div>
      </div>

      {/* Methodology Notice */}
      <div className="flex items-start space-x-3 p-3.5 rounded-xl bg-blue-900/20 border border-blue-800/50">
        <Info className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
        <p className="text-xs text-blue-300 leading-relaxed">
          <span className="font-semibold">Heuristic Debt Indicators</span> — These scores are derived from observable repository metadata
          (issue ages, PR cycles, commit patterns, branch count). They are <em>not</em> direct measures of code quality or
          individual engineer performance. Use as investigative signals, not definitive assessments.
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Est. Remediation Hours', value: `${data.total_estimated_debt_hours ?? 0}h`, icon: <Clock className="w-4 h-4 text-red-400" />, color: 'bg-red-900/30 border-red-800/40' },
          { label: 'Fix Commits', value: `${metrics.fix_commits ?? 0} (${metrics.fix_ratio_pct?.toFixed(1) ?? 0}%)`, icon: <Bug className="w-4 h-4 text-amber-400" />, color: 'bg-amber-900/30 border-amber-800/40' },
          { label: 'Stale Issues (90d+)', value: metrics.stale_issues ?? 0, icon: <AlertTriangle className="w-4 h-4 text-orange-400" />, color: 'bg-orange-900/30 border-orange-800/40' },
          { label: 'Extra Branches', value: metrics.non_default_branches ?? 0, icon: <GitBranch className="w-4 h-4 text-violet-400" />, color: 'bg-violet-900/30 border-violet-800/40' },
        ].map((s, i) => (
          <div key={i} className={`bg-[#111827] border rounded-xl p-4 flex items-center space-x-3 ${s.color}`}>
            <div className={`p-2 rounded-lg ${s.color}`}>{s.icon}</div>
            <div>
              <p className="text-sm font-bold text-white">{s.value}</p>
              <p className="text-xs text-gray-400">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Radar + Commit Mix */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-300">Debt Radar</h3>
          {radarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#374151" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 9 }} />
                <Radar name="Debt Score" dataKey="score" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-40 text-gray-500 text-sm">No indicators yet</div>
          )}

          {commitBreakdown.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-300">Commit Type Mix</h3>
              <ResponsiveContainer width="100%" height={140}>
                <PieChart>
                  <Pie data={commitBreakdown} dataKey="count" nameKey="type" cx="50%" cy="50%" outerRadius={52} label={({ type, percentage }) => `${type} ${percentage}%`} labelLine={false}>
                    {commitBreakdown.map((_, i) => (
                      <Cell key={i} fill={DEBT_COLORS[i % DEBT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }} />
                </PieChart>
              </ResponsiveContainer>
            </>
          )}
        </div>

        {/* Debt Category Breakdown */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-sm font-semibold text-gray-300">Debt Category Breakdown</h3>
          {categories.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {categories.map((cat, i) => <DebtCategoryCard key={i} cat={cat} index={i} />)}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-32 text-gray-500 space-y-2">
              <Shield className="w-8 h-8" />
              <p className="text-sm">No debt categories detected. Sync the repository first.</p>
            </div>
          )}
        </div>
      </div>

      {/* Debt Indicator Bar Chart */}
      {radarData.length > 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
            <TrendingDown className="w-4 h-4 text-amber-400" />
            <span>Weighted Indicator Scores</span>
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={radarData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis type="category" dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 10 }} width={160} />
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f9fafb' }}
                formatter={(v: any) => [`${v.toFixed(1)} / 100`, 'Score']}
              />
              <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                {radarData.map((entry, i) => (
                  <Cell key={i} fill={entry.score > 60 ? '#ef4444' : entry.score > 30 ? '#f59e0b' : '#10b981'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Refactoring Queue */}
      {refactoringQueue.length > 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center space-x-2">
            <TrendingDown className="w-4 h-4 text-cyan-400" />
            <span>Refactoring Priority Queue</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {refactoringQueue.map((cand, i) => <RefactoringCard key={i} cand={cand} />)}
          </div>
        </div>
      )}
    </div>
  );
};
