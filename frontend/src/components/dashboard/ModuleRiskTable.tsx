import React from 'react';
import { ShieldAlert, Info, Cpu } from 'lucide-react';
import { Project } from '../../types';

interface ModuleRiskTableProps {
  activeProject: Project | null;
}

export const ModuleRiskTable: React.FC<ModuleRiskTableProps> = ({ activeProject }) => {
  return (
    <div className="rounded-xl border border-gray-800 bg-[#111827]/80 p-5 backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-gray-800/80 pb-3.5 mb-4">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Component Risk & AST Hotspot Analysis</h3>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-gray-800 text-amber-400 border border-gray-700">
          Scheduled for Phase 4
        </span>
      </div>

      <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800 text-xs text-gray-300 space-y-3">
        <div className="flex items-start space-x-3">
          <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="font-semibold text-white text-sm">
              Code-Level Risk & Vulnerability Detection
            </div>
            <p className="text-gray-400 text-xs mt-1 leading-relaxed">
              Unlike high-level Git telemetry (commits, issues, PRs), granular component risk requires deep static analysis of the source code AST, cyclomatic complexity profiling, and CI test runner coverage reports.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="p-3 rounded-lg bg-gray-950/60 border border-gray-800/80">
            <div className="text-[10px] text-gray-500 uppercase font-mono">Primary Language</div>
            <div className="text-sm font-semibold text-cyan-300 font-mono mt-0.5">
              {activeProject?.language || 'Multi-language'}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-gray-950/60 border border-gray-800/80">
            <div className="text-[10px] text-gray-500 uppercase font-mono">Code Churn Engine</div>
            <div className="text-sm font-semibold text-white font-mono mt-0.5">
              Ready for Phase 4
            </div>
          </div>
          <div className="p-3 rounded-lg bg-gray-950/60 border border-gray-800/80">
            <div className="text-[10px] text-gray-500 uppercase font-mono">Test Coverage</div>
            <div className="text-sm font-semibold text-gray-400 font-mono mt-0.5">
              Requires CI Hook
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-[11px] text-gray-400 pt-1">
          <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span>
            Production integrity notice: Fabricated risk scores are prohibited. True risk scores will populate when the Phase 4 static analysis pipeline is activated.
          </span>
        </div>
      </div>
    </div>
  );
};
