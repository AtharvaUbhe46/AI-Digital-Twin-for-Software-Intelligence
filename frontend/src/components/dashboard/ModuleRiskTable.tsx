import React, { useEffect, useState } from 'react';
import { ShieldAlert, ShieldCheck, AlertTriangle, AlertOctagon, Info } from 'lucide-react';
import { Project, SoftwareRisk } from '../../types';
import { apiService } from '../../services/api';

interface ModuleRiskTableProps {
  activeProject: Project | null;
}

const SEVERITY_BADGES: Record<string, { bg: string; text: string; icon: React.ComponentType<{ className?: string }> }> = {
  CRITICAL: { bg: 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/60 dark:border-red-700/60 dark:text-red-300', text: '', icon: AlertOctagon },
  HIGH: { bg: 'bg-orange-50 text-orange-700 border border-orange-200 dark:bg-orange-950/60 dark:border-orange-700/60 dark:text-orange-300', text: '', icon: AlertTriangle },
  MEDIUM: { bg: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/60 dark:border-amber-700/60 dark:text-amber-300', text: '', icon: AlertTriangle },
  LOW: { bg: 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/60 dark:border-blue-700/60 dark:text-blue-300', text: '', icon: Info },
};

export const ModuleRiskTable: React.FC<ModuleRiskTableProps> = ({ activeProject }) => {
  const [risks, setRisks] = useState<SoftwareRisk[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeProject) {
      setRisks([]);
      return;
    }
    setLoading(true);
    apiService
      .getSoftwareRisks(activeProject.id, { status: 'OPEN' })
      .then(res => setRisks(res))
      .catch(() => setRisks([]))
      .finally(() => setLoading(false));
  }, [activeProject?.id]);

  return (
    <div className="rounded-xl border border-slate-200 dark:border-gray-800 bg-white dark:bg-[#111827]/80 p-5 shadow-sm dark:shadow-none backdrop-blur-md transition-colors">
      <div className="flex items-center justify-between border-b border-slate-100 dark:border-gray-800/80 pb-3.5 mb-4">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Detected Engineering Risks</h3>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-950 dark:text-cyan-400 dark:border-cyan-800">
          Engineering Rules Active
        </span>
      </div>

      {loading ? (
        <div className="space-y-2 py-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-12 bg-slate-100 dark:bg-gray-800/30 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : risks.length === 0 ? (
        <div className="p-6 rounded-xl bg-slate-50 dark:bg-gray-900/40 border border-slate-200 dark:border-gray-800/80 text-center space-y-2">
          <ShieldCheck className="w-8 h-8 text-emerald-500 dark:text-emerald-400 mx-auto" />
          <p className="text-sm font-semibold text-slate-800 dark:text-gray-200">No Open Risks Detected</p>
          <p className="text-xs text-slate-500 dark:text-gray-400 max-w-sm mx-auto">
            Repository activity, pull request cadence, issue resolution, and contributor distribution satisfy all engineering rule thresholds.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {risks.slice(0, 4).map(r => {
            const badge = SEVERITY_BADGES[r.severity] || SEVERITY_BADGES.LOW;
            const Icon = badge.icon;
            return (
              <div
                key={r.id}
                className="p-3 rounded-lg bg-slate-50 dark:bg-gray-900/50 border border-slate-200 dark:border-gray-800 hover:border-slate-300 dark:hover:border-gray-700 transition-colors flex items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-center space-x-2.5 min-w-0">
                  <div className={`p-1.5 rounded ${badge.bg} shrink-0`}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <div className="min-w-0 truncate">
                    <p className="font-semibold text-slate-800 dark:text-gray-200 truncate">{r.title}</p>
                    <p className="text-[11px] text-slate-500 dark:text-gray-400 font-mono truncate">{r.detection_rule}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${badge.bg}`}>
                    {r.severity}
                  </span>
                  {r.metric_value && (
                    <span className="text-[11px] font-mono text-slate-500 dark:text-gray-400 hidden sm:inline">
                      {r.metric_value}
                    </span>
                  )}
                </div>
              </div>
            );
          })}

          {risks.length > 4 && (
            <p className="text-center text-[11px] text-slate-500 dark:text-gray-400 pt-1">
              + {risks.length - 4} more risk(s) in Risk Detection view
            </p>
          )}
        </div>
      )}
    </div>
  );
};
