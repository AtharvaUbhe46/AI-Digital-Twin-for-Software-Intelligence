import React from 'react';
import {
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  FileCode,
} from 'lucide-react';
import { CircularDependency } from '../../types';

interface Props {
  cycles: CircularDependency[];
  onSelectNode?: (nodeId: string) => void;
}

export const CircularDependencyViewer: React.FC<Props> = ({ cycles, onSelectNode }) => {
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-500/10 border-red-500/30 text-red-400';
      case 'HIGH':
        return 'bg-orange-500/10 border-orange-500/30 text-orange-400';
      case 'MEDIUM':
        return 'bg-amber-500/10 border-amber-500/30 text-amber-400';
      default:
        return 'bg-blue-500/10 border-blue-500/30 text-blue-400';
    }
  };

  if (cycles.length === 0) {
    return (
      <div className="bg-[#111827] border border-gray-800 rounded-2xl p-8 flex flex-col items-center justify-center text-center space-y-3">
        <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
          <CheckCircle2 className="w-6 h-6 text-emerald-400" />
        </div>
        <div>
          <h3 className="text-base font-bold text-white">Acyclic Architecture Confirmed</h3>
          <p className="text-xs text-gray-400 max-w-md mt-1">
            Zero circular dependencies detected across analyzed project files and modules.
            Modules follow clear hierarchical dependency directions.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <RotateCcw className="w-5 h-5 text-amber-400" />
          <h3 className="font-bold text-base text-white">
            Detected Circular Dependencies ({cycles.length})
          </h3>
        </div>
        <span className="text-xs text-amber-400/90 font-mono bg-amber-950/40 px-3 py-1 rounded-full border border-amber-800/60">
          Tight Coupling Risk
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {cycles.map((cycle, idx) => (
          <div
            key={cycle.cycle_id || idx}
            className="bg-[#111827] border border-gray-800 hover:border-gray-700 transition-colors rounded-2xl p-5 space-y-4 shadow-lg"
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <span className={`text-[10px] px-2 py-0.5 rounded-full border font-mono font-bold uppercase ${getSeverityBadge(cycle.severity)}`}>
                  {cycle.severity} SEVERITY
                </span>
                <span className="text-xs text-gray-400 font-mono">
                  Cycle #{idx + 1} ({cycle.length} Entities)
                </span>
              </div>
              <span className="text-xs text-gray-400 font-mono">ID: {cycle.cycle_id}</span>
            </div>

            {/* Visual Cycle Path Flow */}
            <div className="bg-[#0B0F17] border border-gray-800/80 rounded-xl p-3.5 overflow-x-auto">
              <div className="flex items-center space-x-2 min-w-max">
                {cycle.path.map((step, sIdx) => {
                  const isEnd = sIdx === cycle.path.length - 1;
                  const label = step.replace('file:', '').replace('mod:', '');
                  const basename = label.split('/').pop() || label;

                  return (
                    <React.Fragment key={sIdx}>
                      <button
                        onClick={() => onSelectNode && onSelectNode(step)}
                        className={`px-3 py-1.5 rounded-lg border text-xs font-mono transition-all flex items-center space-x-1.5 ${
                          isEnd
                            ? 'bg-amber-500/10 border-amber-500/40 text-amber-300 font-bold'
                            : 'bg-gray-800/70 hover:bg-gray-700 border-gray-700 text-gray-200 hover:text-cyan-400'
                        }`}
                        title={label}
                      >
                        <FileCode className="w-3 h-3 opacity-60" />
                        <span>{basename}</span>
                      </button>
                      {!isEnd && (
                        <ArrowRight className="w-4 h-4 text-amber-500/80 shrink-0 animate-pulse" />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>

            {/* Explanation */}
            <p className="text-xs text-gray-400 leading-relaxed">
              {cycle.explanation}
            </p>

            {/* Affected files summary */}
            <div className="text-[11px] text-gray-400 flex flex-wrap items-center gap-1.5 pt-1">
              <span className="font-semibold text-gray-400">Affected Files:</span>
              {cycle.affected_files.map((file, fIdx) => (
                <span
                  key={fIdx}
                  className="bg-gray-800/90 text-gray-300 px-2 py-0.5 rounded font-mono border border-gray-700/50"
                >
                  {file}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
