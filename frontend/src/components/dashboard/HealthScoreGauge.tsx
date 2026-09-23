import React from 'react';
import { HeartPulse, Info, CheckCircle2 } from 'lucide-react';
import { HealthIndexDetails } from '../../types';

interface HealthScoreGaugeProps {
  score: number;
  healthIndex?: HealthIndexDetails;
}

export const HealthScoreGauge: React.FC<HealthScoreGaugeProps> = ({ score, healthIndex }) => {
  const getScoreColor = (val: number) => {
    if (val >= 80) return 'text-emerald-400';
    if (val >= 60) return 'text-cyan-400';
    if (val >= 40) return 'text-amber-400';
    return 'text-rose-400';
  };

  const getScoreRating = (val: number) => {
    if (val >= 80) return { label: 'HEALTHY', badge: 'bg-emerald-950 text-emerald-400 border-emerald-800' };
    if (val >= 60) return { label: 'ACTIVE', badge: 'bg-cyan-950 text-cyan-400 border-cyan-800' };
    if (val >= 40) return { label: 'MODERATE', badge: 'bg-amber-950 text-amber-400 border-amber-800' };
    return { label: 'AT RISK', badge: 'bg-rose-950 text-rose-400 border-rose-800' };
  };

  const rating = getScoreRating(score);

  return (
    <div className="rounded-xl border border-gray-800 bg-[#111827]/80 p-5 backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-gray-800/80 pb-3.5 mb-4">
        <div className="flex items-center space-x-2">
          <HeartPulse className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Repository Health Index</h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-400">Health Rating:</span>
          <span className={`px-2 py-0.5 rounded text-xs font-bold border font-mono ${rating.badge}`}>
            {rating.label}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
        {/* Score Gauge Visualizer */}
        <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-gray-900/60 border border-gray-800/80">
          <div className="relative flex items-center justify-center">
            <svg className="w-32 h-32 transform -rotate-90">
              <circle
                cx="64"
                cy="64"
                r="52"
                stroke="currentColor"
                strokeWidth="10"
                className="text-gray-800"
                fill="transparent"
              />
              <circle
                cx="64"
                cy="64"
                r="52"
                stroke="currentColor"
                strokeWidth="10"
                strokeDasharray={326}
                strokeDashoffset={326 - (326 * Math.min(100, Math.max(0, score))) / 100}
                className="text-cyan-400 transition-all duration-1000 ease-out"
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className={`text-3xl font-extrabold font-mono ${getScoreColor(score)}`}>
                {score.toFixed(1)}
              </span>
              <span className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">
                out of 100
              </span>
            </div>
          </div>
          <p className="text-xs text-center text-gray-300 mt-2 font-medium">Deterministic Score</p>
        </div>

        {/* Explainable Calculation Breakdown */}
        <div className="md:col-span-2 space-y-2.5">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span className="flex items-center space-x-1">
              <Info className="w-3.5 h-3.5 text-cyan-400" />
              <span>Measurable Health Indicators (Transparent Model)</span>
            </span>
            <span className="font-mono text-cyan-400 font-semibold">{score.toFixed(1)} / 100</span>
          </div>

          {healthIndex?.components ? (
            healthIndex.components.map((factor, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-2.5 rounded-lg bg-gray-900/50 border border-gray-800/60 text-xs"
              >
                <div className="flex items-center space-x-2 truncate mr-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  <span className="text-gray-200 font-medium truncate">{factor.name}</span>
                  <span className="text-[10px] text-gray-400 bg-gray-800 px-1.5 py-0.5 rounded font-mono shrink-0">
                    {factor.weight}
                  </span>
                </div>
                <div className="flex items-center space-x-2 shrink-0">
                  <span className="text-[11px] text-gray-400 hidden sm:inline">{factor.detail}</span>
                  <span className="font-mono font-semibold text-white">
                    {factor.score.toFixed(1)} <span className="text-gray-500 text-[10px]">/{factor.max_score}</span>
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-xs text-gray-400 italic p-3 text-center">
              Health breakdown will populate upon repository sync.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
