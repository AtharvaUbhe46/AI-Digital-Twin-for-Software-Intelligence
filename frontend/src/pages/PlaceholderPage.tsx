import React from 'react';
import { NavItem } from '../components/common/Sidebar';
import { ArrowRight, Layers, ShieldCheck } from 'lucide-react';

interface PlaceholderPageProps {
  item: NavItem;
}

const PHASE_DESCRIPTIONS: Record<string, { summary: string; features: string[] }> = {
  'project-overview': {
    summary: 'Comprehensive repository metadata, commit histories, contributor matrices, and branch tracking.',
    features: ['GitHub API dynamic onboarding', 'Branch & PR lifecycle view', 'Contributor commit velocity heatmaps'],
  },
  'digital-twin': {
    summary: 'Autonomous in-memory state engine representing project AST, files, commits, and dependencies.',
    features: ['Real-time repo state synchronization', 'Dual memory & DB persistence', 'Historical version snapshots'],
  },
  'software-health': {
    summary: 'Deep-dive analysis into code quality metrics, CI test coverage, and health trend regression.',
    features: ['Deterministic health scoring algorithm', 'Defect density tracking', 'Test regression monitoring'],
  },
  'risk-analysis': {
    summary: 'Proactive detection of volatile components, high code-churn hotspots, and untested risk zones.',
    features: ['Module churn vs defect correlation', 'Coupling risk scoring', 'Explainable risk drivers'],
  },
  'knowledge-graph': {
    summary: 'Neo4j-backed graph visualizing Developer -> Commit -> File -> Module -> Issue relationships.',
    features: ['Interactive React Flow canvas', 'Transitive dependency tracing', 'Graph-based impact analysis'],
  },
  'architecture': {
    summary: 'Automated reverse-engineering of system components, dependency graphs, and coupling hotspots.',
    features: ['Circular dependency detector', 'Architecture hotspot visualizer', 'Layer violation warnings'],
  },
  'evolution': {
    summary: 'Chronological timeline of project state evolution, architectural shifts, and milestone releases.',
    features: ['Release milestone timeline', 'Architecture drift playback', 'Metric trajectory curves'],
  },
  'technical-debt': {
    summary: 'Automated identification and prioritization of code smells, complexity, and refactoring debt.',
    features: ['Debt hours estimator', 'Cyclomatic complexity hotspots', 'Refactoring priority queue'],
  },
  'ai-assistant': {
    summary: 'Conversational agent with RAG contextual retrieval of current Digital Twin state.',
    features: ['Natural language Q&A on codebase', 'LLM provider abstraction layer', 'Root-cause explanation engine'],
  },
  'simulation': {
    summary: 'What-if scenario modeling engine on a shadow copy of the Digital Twin state.',
    features: ['Variable perturbation sliders', 'Pre vs post simulation comparison', 'Health & risk outcome forecasting'],
  },
  'settings': {
    summary: 'Project configuration, API keys, GitHub tokens, database hooks, and telemetry toggles.',
    features: ['GitHub token management', 'Neo4j connection settings', 'Data retention & sync schedules'],
  },
};

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ item }) => {
  const Icon = item.icon;
  const info = PHASE_DESCRIPTIONS[item.id] || {
    summary: 'Modular component prepared for subsequent implementation phase.',
    features: ['Modular architecture scaffolded', 'Database schema ready', 'API contract defined'],
  };

  return (
    <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
      <div className="p-8 rounded-2xl border border-gray-800 bg-[#111827]/80 backdrop-blur-md">
        <div className="flex items-center space-x-4 mb-6">
          <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Icon className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl font-bold text-white">{item.name}</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800">
                {item.phase || 'Upcoming Phase'}
              </span>
            </div>
            <p className="text-xs text-gray-400 font-mono mt-0.5">
              AI Digital Twin System for Software Intelligence
            </p>
          </div>
        </div>

        <p className="text-sm text-gray-300 leading-relaxed mb-6">
          {info.summary}
        </p>

        <div className="border-t border-gray-800/80 pt-6">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center space-x-2">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>Planned Capabilities & Integration Points</span>
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {info.features.map((feature, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800/60 text-xs text-gray-200 flex items-start space-x-2"
              >
                <ArrowRight className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                <span>{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 p-4 rounded-xl bg-gray-900/40 border border-gray-800 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2 text-gray-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Foundation API schemas and database tables scaffolded in Phase 1.</span>
          </div>
          <span className="text-cyan-400 font-mono font-medium">Ready for activation</span>
        </div>
      </div>
    </div>
  );
};
