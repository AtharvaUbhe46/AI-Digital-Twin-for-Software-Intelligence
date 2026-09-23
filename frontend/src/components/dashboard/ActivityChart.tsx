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

interface ActivityChartProps {
  timeline: TimelineDataPoint[];
}

export const ActivityChart: React.FC<ActivityChartProps> = ({ timeline }) => {
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
    <div className="rounded-xl border border-gray-800 bg-[#111827]/80 p-5 backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-gray-800/80 pb-3.5 mb-4">
        <div className="flex items-center space-x-2">
          <TrendingUp className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Repository Activity & Velocity Trend</h3>
        </div>
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
            <span className="text-gray-300">Commits</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
            <span className="text-gray-300">Pull Requests</span>
          </div>
          <div className="hidden sm:flex items-center space-x-1 text-gray-500 font-mono text-[11px]">
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
                <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="colorPRs" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#C084FC" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#C084FC" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
            <XAxis dataKey="date" stroke="#64748B" tickLine={false} textAnchor="middle" fontSize={11} />
            <YAxis stroke="#64748B" tickLine={false} fontSize={11} allowDecimals={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0F172A',
                borderColor: '#1E293B',
                borderRadius: '0.5rem',
                fontSize: '12px',
                color: '#F8FAFC',
              }}
            />
            <Area
              type="monotone"
              dataKey="commits"
              name="Commits"
              stroke="#38BDF8"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#colorCommits)"
            />
            <Area
              type="monotone"
              dataKey="pull_requests"
              name="Pull Requests"
              stroke="#C084FC"
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
