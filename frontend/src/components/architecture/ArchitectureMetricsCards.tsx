import React from 'react';
import {
  FileCode,
  Boxes,
  Code2,
  Share2,
  RotateCcw,
  Flame,
  CheckCircle2,
} from 'lucide-react';
import { ArchitectureMetrics } from '../../types';

interface Props {
  metrics: ArchitectureMetrics;
}

export const ArchitectureMetricsCards: React.FC<Props> = ({ metrics }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {/* 1. Analyzed Files & Modules */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-2xl p-4 flex flex-col justify-between hover:border-slate-300 dark:hover:border-gray-700 transition-colors shadow-sm dark:shadow-lg">
        <div className="flex items-center justify-between text-slate-500 dark:text-gray-400">
          <span className="text-xs font-semibold uppercase tracking-wider">Source Inventory</span>
          <FileCode className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
        </div>
        <div className="mt-3">
          <div className="text-2xl font-black text-slate-900 dark:text-white font-mono">{metrics.total_files}</div>
          <p className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
            Files across <span className="text-cyan-600 dark:text-cyan-400 font-semibold">{metrics.total_modules}</span> modules
          </p>
        </div>
      </div>

      {/* 2. Classes & Functions */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-2xl p-4 flex flex-col justify-between hover:border-slate-300 dark:hover:border-gray-700 transition-colors shadow-sm dark:shadow-lg">
        <div className="flex items-center justify-between text-slate-500 dark:text-gray-400">
          <span className="text-xs font-semibold uppercase tracking-wider">AST Entities</span>
          <Boxes className="w-4 h-4 text-purple-600 dark:text-purple-400" />
        </div>
        <div className="mt-3">
          <div className="text-2xl font-black text-slate-900 dark:text-white font-mono">
            {metrics.total_classes + metrics.total_functions}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
            <span className="text-purple-600 dark:text-purple-400 font-semibold">{metrics.total_classes}</span> classes,{' '}
            <span className="text-blue-600 dark:text-blue-400 font-semibold">{metrics.total_functions}</span> functions
          </p>
        </div>
      </div>

      {/* 3. Dependencies */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-2xl p-4 flex flex-col justify-between hover:border-slate-300 dark:hover:border-gray-700 transition-colors shadow-sm dark:shadow-lg">
        <div className="flex items-center justify-between text-slate-500 dark:text-gray-400">
          <span className="text-xs font-semibold uppercase tracking-wider">Total Connections</span>
          <Share2 className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="mt-3">
          <div className="text-2xl font-black text-slate-900 dark:text-white font-mono">{metrics.total_dependencies}</div>
          <p className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
            <span className="text-cyan-600 dark:text-cyan-400">{metrics.internal_dependencies}</span> internal,{' '}
            <span className="text-amber-600 dark:text-amber-400">{metrics.external_dependencies}</span> packages
          </p>
        </div>
      </div>

      {/* 4. Circular Dependencies */}
      <div className={`border rounded-2xl p-4 flex flex-col justify-between transition-colors shadow-sm dark:shadow-lg ${
        metrics.circular_dependencies > 0
          ? 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/80'
          : 'bg-white dark:bg-[#111827] border-slate-200 dark:border-gray-800'
      }`}>
        <div className="flex items-center justify-between text-slate-500 dark:text-gray-400">
          <span className="text-xs font-semibold uppercase tracking-wider">Circular Deps</span>
          <RotateCcw className={`w-4 h-4 ${metrics.circular_dependencies > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`} />
        </div>
        <div className="mt-3">
          <div className={`text-2xl font-black font-mono ${metrics.circular_dependencies > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
            {metrics.circular_dependencies}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
            {metrics.circular_dependencies > 0 ? (
              <span className="text-amber-600 dark:text-amber-300 font-medium">Cycles detected</span>
            ) : (
              <span className="text-emerald-600 dark:text-emerald-400 font-medium flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3 inline mr-1" />
                Acyclic graph
              </span>
            )}
          </p>
        </div>
      </div>

      {/* 5. Hotspots & Bottlenecks */}
      <div className={`border rounded-2xl p-4 flex flex-col justify-between transition-colors shadow-sm dark:shadow-lg ${
        metrics.architecture_hotspots > 0
          ? 'bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-800/80'
          : 'bg-white dark:bg-[#111827] border-slate-200 dark:border-gray-800'
      }`}>
        <div className="flex items-center justify-between text-slate-500 dark:text-gray-400">
          <span className="text-xs font-semibold uppercase tracking-wider">Coupling Hotspots</span>
          <Flame className={`w-4 h-4 ${metrics.architecture_hotspots > 0 ? 'text-orange-600 dark:text-orange-400' : 'text-slate-400 dark:text-gray-400'}`} />
        </div>
        <div className="mt-3">
          <div className={`text-2xl font-black font-mono ${metrics.architecture_hotspots > 0 ? 'text-orange-600 dark:text-orange-400' : 'text-slate-700 dark:text-gray-300'}`}>
            {metrics.architecture_hotspots}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-gray-400 mt-0.5">
            High fan-out / fan-in modules
          </p>
        </div>
      </div>
    </div>
  );
};
