import React, { useState, useEffect, useCallback } from 'react';
import {
  Network,
  RefreshCw,
  Layers,
  RotateCcw,
  Package,
  Flame,
  ShieldAlert,
  AlertTriangle,
  FolderGit2,
  GitFork,
  ArrowRight,
} from 'lucide-react';
import {
  Project,
  ArchitectureOverviewData,
  ArchitectureMetrics,
  CircularDependenciesData,
  DependencyAnalysisData,
  KnowledgeGraphData,
} from '../types';
import { apiService } from '../services/api';
import { ArchitectureMetricsCards } from '../components/architecture/ArchitectureMetricsCards';
import { InteractiveGraphCanvas } from '../components/architecture/InteractiveGraphCanvas';
import { DependencyMatrixTable } from '../components/architecture/DependencyMatrixTable';
import { CircularDependencyViewer } from '../components/architecture/CircularDependencyViewer';
import { NodeDetailsPanel } from '../components/architecture/NodeDetailsPanel';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

export const ArchitecturePage: React.FC<Props> = ({
  activeProject,
  onOpenConnectModal,
}) => {
  const [overview, setOverview] = useState<ArchitectureOverviewData | null>(null);
  const [metrics, setMetrics] = useState<ArchitectureMetrics | null>(null);
  const [cyclesData, setCyclesData] = useState<CircularDependenciesData | null>(null);
  const [depsData, setDepsData] = useState<DependencyAnalysisData | null>(null);
  const [moduleGraph, setModuleGraph] = useState<KnowledgeGraphData | null>(null);

  const [activeTab, setActiveTab] = useState<'graph' | 'matrix' | 'cycles' | 'hotspots'>('graph');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const loadData = useCallback(async (showLoading: boolean = true) => {
    if (!activeProject) return;
    if (showLoading) setIsLoading(true);
    try {
      const [over, met, cyc, dep, graph] = await Promise.all([
        apiService.getArchitectureOverview(activeProject.id),
        apiService.getArchitectureMetrics(activeProject.id),
        apiService.getCircularDependencies(activeProject.id),
        apiService.getDependencyAnalysis(activeProject.id),
        apiService.getKnowledgeGraph(activeProject.id, {
          node_type: 'file', // Module/file level graph
          limit: 150,
        }),
      ]);

      setOverview(over);
      setMetrics(met);
      setCyclesData(cyc);
      setDepsData(dep);
      setModuleGraph(graph);
    } catch (err: any) {
      console.error('Failed to load architecture data:', err);
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, [activeProject]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleTriggerAnalysis = async () => {
    if (!activeProject) return;
    setIsAnalyzing(true);
    try {
      await apiService.triggerArchitectureAnalysis(activeProject.id, undefined, true);
      await loadData(true);
    } catch (err: any) {
      console.error('Failed to trigger analysis:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="bg-[#111827] border border-gray-800 rounded-2xl p-12 text-center space-y-4 max-w-xl mx-auto mt-12">
        <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mx-auto">
          <FolderGit2 className="w-6 h-6 text-cyan-400" />
        </div>
        <h2 className="text-xl font-bold text-white">No Connected Repository</h2>
        <p className="text-xs text-gray-400">
          Connect a software repository to visualize its architecture and module dependency relationships.
        </p>
        <button
          onClick={onOpenConnectModal}
          className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-cyan-500/20"
        >
          Connect Repository
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono font-semibold uppercase">
              Phase 5
            </span>
            <span className="text-xs text-gray-400 font-mono">Architecture & Coupling Intelligence</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1 flex items-center space-x-2">
            <span>Software Architecture & Dependencies</span>
            <Network className="w-5 h-5 text-cyan-400" />
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Module-level coupling (Ca/Ce), architectural bottlenecks, package usage, and circular dependencies for{' '}
            <span className="text-cyan-400 font-mono font-medium">{activeProject.full_name}</span>.
          </p>
        </div>

        <button
          onClick={handleTriggerAnalysis}
          disabled={isAnalyzing}
          className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-semibold transition-all shadow-lg shadow-cyan-500/20 flex items-center space-x-2 disabled:opacity-50 self-start md:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
          <span>{isAnalyzing ? 'Analyzing Architecture...' : 'Re-Evaluate Architecture'}</span>
        </button>
      </div>

      {/* KPI Metrics Cards */}
      {metrics && <ArchitectureMetricsCards metrics={metrics} />}

      {/* Tab Navigation */}
      <div className="flex items-center space-x-2 bg-[#111827] p-1.5 rounded-xl border border-gray-800 w-fit">
        <button
          onClick={() => setActiveTab('graph')}
          className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 ${
            activeTab === 'graph'
              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-sm'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <Network className="w-3.5 h-3.5" />
          <span>File Dependency Graph</span>
        </button>
        <button
          onClick={() => setActiveTab('matrix')}
          className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 ${
            activeTab === 'matrix'
              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-sm'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Coupling & Packages</span>
        </button>
        <button
          onClick={() => setActiveTab('cycles')}
          className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 ${
            activeTab === 'cycles'
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 shadow-sm'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Circular Dependencies ({cyclesData?.total_cycles || 0})</span>
        </button>
        <button
          onClick={() => setActiveTab('hotspots')}
          className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 ${
            activeTab === 'hotspots'
              ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40 shadow-sm'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <Flame className="w-3.5 h-3.5" />
          <span>Bottlenecks & Hotspots ({(overview?.bottlenecks.length || 0) + (overview?.hotspots.length || 0)})</span>
        </button>
      </div>

      {/* Main View Area */}
      {isLoading ? (
        <div className="w-full h-96 bg-[#111827] border border-gray-800 rounded-2xl flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-gray-400 font-mono">Evaluating software architecture...</span>
        </div>
      ) : activeTab === 'graph' ? (
        <div className="relative min-h-[580px] flex">
          <div className="flex-1 relative flex">
            <InteractiveGraphCanvas
              nodes={moduleGraph?.nodes || []}
              edges={moduleGraph?.edges || []}
              selectedNodeId={selectedNodeId}
              onSelectNode={setSelectedNodeId}
              direction="TB"
            />
            {selectedNodeId && (
              <div className="absolute right-4 top-4 z-20">
                <NodeDetailsPanel
                  projectId={activeProject.id}
                  nodeId={selectedNodeId}
                  onClose={() => setSelectedNodeId(null)}
                  onSelectNode={setSelectedNodeId}
                />
              </div>
            )}
          </div>
        </div>
      ) : activeTab === 'matrix' ? (
        <DependencyMatrixTable
          modules={overview?.modules || []}
          packages={depsData?.packages || []}
        />
      ) : activeTab === 'cycles' ? (
        <CircularDependencyViewer
          cycles={cyclesData?.cycles || []}
          onSelectNode={(nodeId) => {
            setSelectedNodeId(nodeId);
            setActiveTab('graph');
          }}
        />
      ) : activeTab === 'hotspots' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Bottlenecks (High Fan-In) */}
          <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-5 h-5 text-rose-400" />
              <h3 className="font-bold text-base text-white">
                Architectural Bottlenecks ({overview?.bottlenecks.length || 0})
              </h3>
            </div>
            <p className="text-xs text-gray-400">
              Modules with exceptionally high fan-in (afferent coupling). Changes to these modules have a large blast radius.
            </p>
            {(!overview?.bottlenecks || overview.bottlenecks.length === 0) ? (
              <p className="text-xs text-gray-400 italic">No critical bottlenecks identified.</p>
            ) : (
              <div className="space-y-3">
                {overview.bottlenecks.map((b, idx) => (
                  <div key={idx} className="bg-[#0B0F17] border border-rose-500/20 rounded-xl p-4 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-rose-300 font-mono">{b.module}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded border border-rose-500/30 bg-rose-500/10 text-rose-400 font-mono uppercase font-bold">
                        {b.severity}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">{b.reason}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Hotspots (High Fan-Out) */}
          <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <div className="flex items-center space-x-2">
              <Flame className="w-5 h-5 text-orange-400" />
              <h3 className="font-bold text-base text-white">
                Coupling Hotspots ({overview?.hotspots.length || 0})
              </h3>
            </div>
            <p className="text-xs text-gray-400">
              Modules with high fan-out (efferent coupling) or high instability. These modules depend on many components and are fragile.
            </p>
            {(!overview?.hotspots || overview.hotspots.length === 0) ? (
              <p className="text-xs text-gray-400 italic">No high-instability hotspots identified.</p>
            ) : (
              <div className="space-y-3">
                {overview.hotspots.map((h, idx) => (
                  <div key={idx} className="bg-[#0B0F17] border border-orange-500/20 rounded-xl p-4 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-orange-300 font-mono">{h.module}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded border border-orange-500/30 bg-orange-500/10 text-orange-400 font-mono uppercase font-bold">
                        {h.severity}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">{h.reason}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};
