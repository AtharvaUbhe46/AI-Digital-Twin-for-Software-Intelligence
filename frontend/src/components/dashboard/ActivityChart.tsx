import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { TrendingUp, Calendar } from 'lucide-react';
import { TimelineDataPoint } from '../../types';
import { useTheme } from '../../context/ThemeContext';

interface ActivityChartProps {
  timeline: TimelineDataPoint[];
}

export const ActivityChart: React.FC<ActivityChartProps> = ({ timeline }) => {
  const { isDark } = useTheme();

  const chartData = timeline && timeline.length > 0 ? timeline : [
    { date: 'Day 1', commits: 0, pull_requests: 0 },
    { date: 'Day 2', commits: 0, pull_requests: 0 },
    { date: 'Day 3', commits: 0, pull_requests: 0 },
    { date: 'Day 4', commits: 0, pull_requests: 0 },
    { date: 'Day 5', commits: 0, pull_requests: 0 },
    { date: 'Day 6', commits: 0, pull_requests: 0 },
    { date: 'Day 7', commits: 0, pull_requests: 0 },
  ];

  return (
    <div className="rounded-xl border border-slate-200 dark:border-gray-800 bg-white dark:bg-[#111827]/80 p-5 shadow-sm dark:shadow-none backdrop-blur-md transition-colors">
      <div className="flex items-center justify-between border-b border-slate-100 dark:border-gray-800/80 pb-3.5 mb-4">
        <div className="flex items-center space-x-2">
          <TrendingUp className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Repository Activity & Velocity Trend</h3>
        </div>
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" />
            <span className="text-slate-600 dark:text-gray-300 font-medium">Commits</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
            <span className="text-slate-600 dark:text-gray-300 font-medium">Pull Requests</span>
          </div>
          <div className="hidden sm:flex items-center space-x-1 text-slate-400 dark:text-gray-500 font-mono text-[11px]">
            <Calendar className="w-3 h-3" />
            <span>Recent 7 Days</span>
          </div>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCommits" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0EA5E9" stopOpacity={isDark ? 0.4 : 0.25} />
                <stop offset="95%" stopColor="#0EA5E9" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="colorPRs" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#A855F7" stopOpacity={isDark ? 0.35 : 0.2} />
                <stop offset="95%" stopColor="#A855F7" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#1F2937' : '#E2E8F0'} vertical={false} />
            <XAxis
              dataKey="date"
              stroke={isDark ? '#64748B' : '#94A3B8'}
              tick={{ fill: isDark ? '#94A3B8' : '#64748B' }}
              tickLine={false}
              textAnchor="middle"
              fontSize={11}
            />
            <YAxis
              stroke={isDark ? '#64748B' : '#94A3B8'}
              tick={{ fill: isDark ? '#94A3B8' : '#64748B' }}
              tickLine={false}
              fontSize={11}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: isDark ? '#0F172A' : '#FFFFFF',
                borderColor: isDark ? '#1E293B' : '#E2E8F0',
                borderRadius: '0.5rem',
                fontSize: '12px',
                color: isDark ? '#F8FAFC' : '#0F172A',
                boxShadow: isDark ? '0 10px 15px -3px rgba(0, 0, 0, 0.4)' : '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
              itemStyle={{
                color: isDark ? '#E2E8F0' : '#1E293B',
              }}
              labelStyle={{
                color: isDark ? '#94A3B8' : '#64748B',
                fontWeight: 600,
              }}
            />
            <Area
              type="monotone"
              dataKey="commits"
              name="Commits"
              stroke="#0EA5E9"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#colorCommits)"
            />
            <Area
              type="monotone"
              dataKey="pull_requests"
              name="Pull Requests"
              stroke="#A855F7"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorPRs)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
