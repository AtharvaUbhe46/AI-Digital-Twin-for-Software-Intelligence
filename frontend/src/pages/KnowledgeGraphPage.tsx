import React, { useState, useEffect, useCallback } from 'react';
import {
  Share2,
  RefreshCw,
  Search,
  Filter,
  SlidersHorizontal,
  Layers,
  FileCode,
  Boxes,
  Code2,
  Package,
  Globe,
  FolderGit2,
} from 'lucide-react';
import {
  Project,
  KnowledgeGraphData,
  ArchitectureAnalysisStatus,
} from '../types';
import { apiService } from '../services/api';
import { InteractiveGraphCanvas } from '../components/architecture/InteractiveGraphCanvas';
import { NodeDetailsPanel } from '../components/architecture/NodeDetailsPanel';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

export const KnowledgeGraphPage: React.FC<Props> = ({
  activeProject,
  onOpenConnectModal,
}) => {
  const [graphData, setGraphData] = useState<KnowledgeGraphData | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<ArchitectureAnalysisStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Filters
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [selectedRel, setSelectedRel] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [direction, setDirection] = useState<'TB' | 'LR'>('TB');

  const loadGraph = useCallback(
    async (showLoading: boolean = true) => {
      if (!activeProject) return;
      if (showLoading) setIsLoading(true);
      try {
        const [graph, status] = await Promise.all([
          apiService.getKnowledgeGraph(activeProject.id, {
            node_type: selectedType === 'ALL' ? undefined : selectedType,
            relationship_type: selectedRel === 'ALL' ? undefined : selectedRel,
            search: searchTerm ? searchTerm : undefined,
            limit: 300,
          }),
          apiService.getArchitectureStatus(activeProject.id),
        ]);
        setGraphData(graph);
        setAnalysisStatus(status);
      } catch (err: any) {
        console.error('Failed to load knowledge graph:', err);
      } finally {
        if (showLoading) setIsLoading(false);
      }
    },
    [activeProject, selectedType, selectedRel, searchTerm]
  );

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const handleTriggerAnalysis = async () => {
    if (!activeProject) return;
    setIsAnalyzing(true);
    try {
      await apiService.triggerArchitectureAnalysis(activeProject.id, undefined, true);
      await loadGraph(true);
    } catch (err: any) {
      console.error('Analysis trigger failed:', err);
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
          Connect a software repository to generate and explore its AST Knowledge Graph.
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

  const nodeTypes = [
    { id: 'ALL', label: 'All Entities', icon: Layers },
    { id: 'file', label: 'Files', icon: FileCode },
    { id: 'class', label: 'Classes', icon: Boxes },
    { id: 'function', label: 'Functions', icon: Code2 },
    { id: 'package', label: 'Packages', icon: Package },
    { id: 'api_endpoint', label: 'Endpoints', icon: Globe },
  ];

  const relTypes = [
    { id: 'ALL', label: 'All Relations' },
    { id: 'IMPORTS', label: 'Imports' },
    { id: 'CALLS', label: 'Calls' },
    { id: 'EXTENDS', label: 'Inheritance' },
    { id: 'DEPENDS_ON', label: 'Depends On' },
    { id: 'ROUTES_TO', label: 'Routes To' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono font-semibold uppercase">
              Phase 5
            </span>
            <span className="text-xs text-gray-400 font-mono">AST-Driven Knowledge Graph</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1 flex items-center space-x-2">
            <span>Repository Knowledge Graph</span>
            <Share2 className="w-5 h-5 text-cyan-400" />
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Explores code entities, class inheritance, function calls, imports, and API routes for{' '}
            <span className="text-cyan-400 font-mono font-medium">{activeProject.full_name}</span>.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setDirection((prev) => (prev === 'TB' ? 'LR' : 'TB'))}
            className="px-3 py-2 bg-[#111827] hover:bg-gray-800 border border-gray-800 text-gray-300 rounded-xl text-xs font-medium transition-colors flex items-center space-x-1.5"
            title="Toggle Layout Direction (Top-to-Bottom / Left-to-Right)"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Layout: {direction === 'TB' ? 'Vertical' : 'Horizontal'}</span>
          </button>

          <button
            onClick={handleTriggerAnalysis}
            disabled={isAnalyzing}
            className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-semibold transition-all shadow-lg shadow-cyan-500/20 flex items-center space-x-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
            <span>{isAnalyzing ? 'Analyzing AST...' : 'Re-Analyze Code'}</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#111827] border border-gray-800 rounded-2xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg">
        {/* Search */}
        <div className="relative max-w-xs w-full">
          <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search classes, functions, files..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0B0F17] border border-gray-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>

        {/* Node Type Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          {nodeTypes.map((t) => {
            const Icon = t.icon;
            const isSelected = selectedType === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setSelectedType(t.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 ${
                  isSelected
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'bg-[#0B0F17] text-gray-400 hover:text-gray-200 border border-gray-800'
                }`}
              >
                <Icon className="w-3 h-3" />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>

        {/* Relationship Type Pills */}
        <div className="flex flex-wrap items-center gap-1">
          <Filter className="w-3 h-3 text-gray-400 mr-1" />
          {relTypes.map((r) => {
            const isSelected = selectedRel === r.id;
            return (
              <button
                key={r.id}
                onClick={() => setSelectedRel(r.id)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all ${
                  isSelected
                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                {r.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Interactive Canvas Area */}
      <div className="relative min-h-[580px] flex">
        {isLoading ? (
          <div className="w-full h-[580px] bg-[#0B0F17] border border-gray-800 rounded-2xl flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-gray-400 font-mono">
              Extracting AST relations & rendering graph...
            </span>
          </div>
        ) : (
          <div className="flex-1 relative flex">
            <InteractiveGraphCanvas
              nodes={graphData?.nodes || []}
              edges={graphData?.edges || []}
              selectedNodeId={selectedNodeId}
              onSelectNode={setSelectedNodeId}
              direction={direction}
            />

            {/* Floating Inspector Panel */}
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
        )}
      </div>

      {/* Summary Footer Bar */}
      {graphData && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-3 flex flex-wrap items-center justify-between text-xs text-gray-400 font-mono">
          <div className="flex items-center space-x-4">
            <span>
              Rendered Nodes: <strong className="text-white">{graphData.total_nodes}</strong>
            </span>
            <span>
              Rendered Edges: <strong className="text-cyan-400">{graphData.total_edges}</strong>
            </span>
            {analysisStatus && (
              <span>
                Status: <strong className="text-emerald-400">{analysisStatus.status}</strong>
              </span>
            )}
          </div>
          <div className="text-[11px] text-gray-400">
            Tip: Drag nodes, scroll to zoom, click any node to inspect parameters & AST callers
          </div>
        </div>
      )}
    </div>
  );
};
