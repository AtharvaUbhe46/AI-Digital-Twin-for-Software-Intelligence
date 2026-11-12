import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Share2,
  RefreshCw,
  Search,
  Layers,
  FileCode,
  Boxes,
  Code2,
  Package,
  Globe,
  SlidersHorizontal,
  AlertCircle,
} from 'lucide-react';
import { Project, KnowledgeGraphData, ArchitectureAnalysisStatus } from '../types';
import { apiService } from '../services/api';
import { InteractiveGraphCanvas } from '../components/architecture/InteractiveGraphCanvas';
import { NodeDetailsPanel } from '../components/architecture/NodeDetailsPanel';

interface KnowledgeGraphPageProps {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

// Client-side cache to enable instant tab switching and eliminate redundant network round-trips
const graphMemoryCache = new Map<string, KnowledgeGraphData>();

export const KnowledgeGraphPage: React.FC<KnowledgeGraphPageProps> = ({
  activeProject,
  onOpenConnectModal,
}) => {
  const [graphData, setGraphData] = useState<KnowledgeGraphData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisStatus, setAnalysisStatus] = useState<ArchitectureAnalysisStatus | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Filters & State
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [direction, setDirection] = useState<'TB' | 'LR'>('TB');

  // Debounce search input to avoid repeated API requests while typing
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm.trim());
    }, 280);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const cacheKey = useMemo(() => {
    if (!activeProject) return '';
    return `${activeProject.id}_${selectedType}_${debouncedSearch}`;
  }, [activeProject, selectedType, debouncedSearch]);

  const fetchGraph = useCallback(async (projectId: number, bypassCache: boolean = false) => {
    const key = `${projectId}_${selectedType}_${debouncedSearch}`;
    if (!bypassCache && graphMemoryCache.has(key)) {
      setGraphData(graphMemoryCache.get(key)!);
      setIsLoading(false);
      setFetchError(null);
      return;
    }

    setIsLoading(true);
    setFetchError(null);
    try {
      const data = await apiService.getKnowledgeGraph(projectId, {
        node_type: selectedType === 'ALL' ? undefined : selectedType,
        search: debouncedSearch || undefined,
        limit: 250,
      });
      graphMemoryCache.set(key, data);
      setGraphData(data);
    } catch (err: any) {
      console.error('Failed to load knowledge graph:', err);
      setFetchError(err?.response?.data?.detail || err?.message || 'Failed to load knowledge graph data');
    } finally {
      setIsLoading(false);
    }
  }, [selectedType, debouncedSearch]);

  useEffect(() => {
    if (activeProject) {
      fetchGraph(activeProject.id);
    }
  }, [activeProject, fetchGraph]);

  const handleTriggerAnalysis = async () => {
    if (!activeProject) return;
    setIsAnalyzing(true);
    try {
      const status = await apiService.triggerArchitectureAnalysis(activeProject.id);
      setAnalysisStatus(status);
      // Invalidate cache for this project on re-analysis
      for (const k of Array.from(graphMemoryCache.keys())) {
        if (k.startsWith(`${activeProject.id}_`)) {
          graphMemoryCache.delete(k);
        }
      }
      await fetchGraph(activeProject.id, true);
    } catch (err: any) {
      alert(`Analysis error: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] max-w-xl mx-auto text-center px-4 space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30 flex items-center justify-center text-cyan-600 dark:text-cyan-400 shadow-xl shadow-cyan-500/10">
          <Share2 className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">Repository Knowledge Graph</h2>
          <p className="text-xs text-slate-500 dark:text-gray-400 leading-relaxed">
            Connect a GitHub repository to visualize AST code entities, modules, classes, methods, endpoints, and
            transitive import dependencies.
          </p>
        </div>
        <button
          onClick={onOpenConnectModal}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold shadow-lg shadow-cyan-600/20 transition-all"
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
    { id: 'api_endpoint', label: 'API Endpoints', icon: Globe },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-950 dark:text-cyan-400 dark:border-cyan-800 font-mono font-semibold uppercase">
              Graph Engine
            </span>
            <span className="text-xs text-slate-500 dark:text-gray-400 font-mono">AST-Driven Knowledge Graph</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight mt-1 flex items-center space-x-2">
            <span>Repository Knowledge Graph</span>
            <Share2 className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
          </h1>
          <p className="text-xs text-slate-500 dark:text-gray-400 mt-0.5">
            Explores code entities, class inheritance, function calls, imports, and API routes for{' '}
            <span className="text-cyan-600 dark:text-cyan-400 font-mono font-medium">{activeProject.full_name}</span>.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setDirection((prev) => (prev === 'TB' ? 'LR' : 'TB'))}
            className="px-3 py-2 bg-white hover:bg-slate-100 dark:bg-[#111827] dark:hover:bg-gray-800 border border-slate-200 dark:border-gray-800 text-slate-700 dark:text-gray-300 rounded-xl text-xs font-medium transition-colors flex items-center space-x-1.5 shadow-sm dark:shadow-none"
            title="Toggle Layout Direction (Top-to-Bottom / Left-to-Right)"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Layout: {direction === 'TB' ? 'Vertical' : 'Horizontal'}</span>
          </button>

          <button
            onClick={handleTriggerAnalysis}
            disabled={isAnalyzing}
            className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-semibold transition-all shadow-md shadow-cyan-500/20 flex items-center space-x-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
            <span>{isAnalyzing ? 'Analyzing AST...' : 'Re-Analyze Code'}</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-2xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm dark:shadow-lg transition-colors">
        {/* Search */}
        <div className="relative max-w-sm w-full">
          <Search className="w-3.5 h-3.5 text-slate-400 dark:text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search classes, functions, endpoints, files..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-gray-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-900 dark:text-gray-200 placeholder-slate-400 dark:placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors"
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
                    ? 'bg-cyan-50 text-cyan-700 border border-cyan-300 shadow-sm dark:bg-cyan-500/20 dark:text-cyan-300 dark:border-cyan-500/40'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-600 dark:bg-[#0B0F17] dark:text-gray-400 dark:hover:text-gray-200 border border-slate-200 dark:border-gray-800'
                }`}
              >
                <Icon className="w-3 h-3" />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Interactive Canvas Area */}
      <div className="relative min-h-[580px] flex">
        {isLoading && !graphData ? (
          <div className="w-full h-[580px] bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-gray-800 rounded-2xl flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-slate-500 dark:text-gray-400 font-mono">
              Extracting AST relations & rendering graph...
            </span>
          </div>
        ) : fetchError ? (
          <div className="w-full h-[580px] bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-gray-800 rounded-2xl flex flex-col items-center justify-center p-6 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 flex items-center justify-center text-rose-500">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-gray-200">Unable to Load Knowledge Graph</h4>
            <p className="text-xs text-slate-500 dark:text-gray-400 max-w-md">{fetchError}</p>
            <button
              onClick={() => activeProject && fetchGraph(activeProject.id, true)}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
            >
              Retry
            </button>
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
        <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-xl p-3 flex flex-wrap items-center justify-between text-xs text-slate-600 dark:text-gray-400 font-mono shadow-sm dark:shadow-none transition-colors">
          <div className="flex items-center space-x-4">
            <span>
              Rendered Nodes: <strong className="text-slate-900 dark:text-white">{graphData.total_nodes}</strong>
            </span>
            <span>
              Rendered Edges: <strong className="text-cyan-600 dark:text-cyan-400">{graphData.total_edges}</strong>
            </span>
            {analysisStatus && (
              <span>
                Status: <strong className="text-emerald-600 dark:text-emerald-400">{analysisStatus.status}</strong>
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-400 dark:text-gray-400">
            Tip: Drag nodes, scroll to zoom, click any node to inspect parameters & AST callers
          </div>
        </div>
      )}
    </div>
  );
};
