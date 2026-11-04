import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: string;
  isPositive?: boolean;
  icon: LucideIcon;
  color?: 'cyan' | 'emerald' | 'amber' | 'rose' | 'purple';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  change,
  isPositive,
  icon: Icon,
  color = 'cyan',
}) => {
  const iconBgMap = {
    cyan: 'bg-cyan-50 dark:bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
    emerald: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    amber: 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400',
    rose: 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400',
    purple: 'bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400',
  };

  return (
    <div
      className="rounded-xl p-5 bg-white dark:bg-gray-900/60 border border-slate-200 dark:border-gray-800 shadow-sm dark:shadow-none hover:border-slate-300 dark:hover:border-gray-700 transition-all"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 dark:text-gray-400 tracking-wide uppercase truncate mr-2">
          {title}
        </span>
        <div className={`p-2 rounded-lg shrink-0 ${iconBgMap[color]}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="mt-4 flex items-baseline justify-between gap-2">
        <div className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight font-mono truncate">
          {value}
        </div>
        {change && (
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full shrink-0 ${
              isPositive
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/80 dark:text-emerald-400 dark:border-emerald-800/60'
                : 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/80 dark:text-rose-400 dark:border-rose-800/60'
            }`}
          >
            {change}
          </span>
        )}
      </div>

      {subtitle && <p className="mt-2 text-xs text-slate-500 dark:text-gray-400 truncate">{subtitle}</p>}
    </div>
  );
};
