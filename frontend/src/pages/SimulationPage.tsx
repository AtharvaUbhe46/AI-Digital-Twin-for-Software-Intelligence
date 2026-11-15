import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Sliders,
  Play,
  RotateCcw,
  Save,
  Trash2,
  GitBranch,
  ShieldAlert,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Layers,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Cpu,
  Clock,
  Code,
  Network,
  Users,
  FolderGit2,
  Activity,
  Zap,
  Info,
  Scale,
  X,
  ExternalLink,
  ChevronRight,
  FileCode,
  Check,
  RefreshCw
} from 'lucide-react';
import {
  Project,
  SimulationBaselineData,
  SimulationParameterMeta,
  SimulationParameterInput,
  SimulationCreatePayload,
  SimulationResult,
  SimulationSummary,
  SimulationCompareData,
  AffectedModuleItem
} from '../types';
import { apiService } from '../services/api';

interface SimulationPageProps {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
}

interface ScenarioPreset {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  params: Record<string, number>;
}

const PRESETS: ScenarioPreset[] = [
  {
    id: 'latency-spike',
    name: 'API Latency Surge & Queue Saturation',
    category: 'performance',
    description: 'Models a 4x spike in endpoint latency to simulate heavy traffic load or database connection pool contention.',
    icon: Zap,
    params: {
      api_latency: 180,
      open_issues: 15,
    },
  },
  {
    id: 'refactoring-clean',
    name: 'Clean Architecture & Modular Refactoring',
    category: 'architecture',
    description: 'Simulates refactoring complex modules, decoupling cross-service imports, and increasing automated test coverage.',
    icon: Code,
    params: {
      module_complexity: 4.5,
      coupling_degree: 0.9,
      code_quality_index: 85,
    },
  },
  {
    id: 'dependency-bloat',
    name: 'Third-Party Dependency Expansion',
    category: 'dependencies',
    description: 'Evaluates the security attack surface and build overhead of adding multiple third-party libraries.',
    icon: Layers,
    params: {
      dependency_count: 22,
    },
  },
  {
    id: 'team-downsizing',
    name: 'Team Downsizing & Knowledge Silos',
    category: 'team',
    description: 'Evaluates project resilience and issue resolution slowdown when key developers rotate off the team.',
    icon: Users,
    params: {
      active_contributors: 1,
      issue_resolution_rate: 35,
      open_issues: 25,
    },
  },
  {
    id: 'sprint-acceleration',
    name: 'High-Velocity Feature Sprint',
    category: 'activity',
    description: 'Models a rapid release sprint with tripled commit cadence and elevated open PR review load.',
    icon: Activity,
    params: {
      commits_per_week: 16,
      open_prs: 10,
    },
  },
];

export const SimulationPage: React.FC<SimulationPageProps> = ({
  activeProject,
  onOpenConnectModal,
}) => {
  // State
  const [baseline, setBaseline] = useState<SimulationBaselineData | null>(null);
  const [savedSimulations, setSavedSimulations] = useState<SimulationSummary[]>([]);
  const [currentResult, setCurrentResult] = useState<SimulationResult | null>(null);

  // Form State
  const [scenarioName, setScenarioName] = useState<string>('Custom What-If Scenario');
  const [scenarioCategory, setScenarioCategory] = useState<string>('custom');
  const [scenarioDescription, setScenarioDescription] = useState<string>('');
  const [parameterValues, setParameterValues] = useState<Record<string, number>>({});
  const [selectedCategoryTab, setSelectedCategoryTab] = useState<string>('all');
  const [affectedFilter, setAffectedFilter] = useState<'ALL' | 'DIRECT' | 'INDIRECT' | 'HIGH_RISK'>('ALL');

  // Loading & Error States
  const [isLoadingBaseline, setIsLoadingBaseline] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Comparison State
  const [compareSimAId, setCompareSimAId] = useState<number | null>(null);
  const [compareSimBId, setCompareSimBId] = useState<number | null>(null);
  const [compareData, setCompareData] = useState<SimulationCompareData | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState<boolean>(false);

  // Load Baseline Data
  const loadBaseline = useCallback(async (projectId: number) => {
    setIsLoadingBaseline(true);
    setError(null);
    try {
      const data = await apiService.getSimulationBaseline(projectId);
      setBaseline(data);

      // Initialize default parameter values from baseline
      const initial: Record<string, number> = {};
      data.available_parameters.forEach((param) => {
        if (param.current_value !== null) {
          initial[param.key] = param.current_value;
        }
      });
      setParameterValues(initial);
    } catch (err: any) {
      console.error('Failed to load simulation baseline:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to fetch Digital Twin baseline');
    } finally {
      setIsLoadingBaseline(false);
    }
  }, []);

  // Load Saved Simulations
  const loadHistory = useCallback(async (projectId: number) => {
    setIsLoadingHistory(true);
    try {
      const history = await apiService.getSimulations(projectId);
      setSavedSimulations(history);
      if (history.length >= 2) {
        setCompareSimAId(history[0].id);
        setCompareSimBId(history[1].id);
      } else if (history.length === 1) {
        setCompareSimAId(history[0].id);
      }
    } catch (err: any) {
      console.warn('Failed to load simulations history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  // Initialize when active project changes
  useEffect(() => {
    if (activeProject) {
      loadBaseline(activeProject.id);
      loadHistory(activeProject.id);
      setCurrentResult(null);
    } else {
      setBaseline(null);
      setSavedSimulations([]);
      setCurrentResult(null);
    }
  }, [activeProject, loadBaseline, loadHistory]);

  // Handle Preset Selection
  const applyPreset = (preset: ScenarioPreset) => {
    if (!baseline) return;
    setScenarioName(preset.name);
    setScenarioCategory(preset.category);
    setScenarioDescription(preset.description);

    const updated = { ...parameterValues };
    Object.entries(preset.params).forEach(([key, val]) => {
      updated[key] = val;
    });
    setParameterValues(updated);
  };

  // Reset all parameters to baseline
  const resetToBaseline = () => {
    if (!baseline) return;
    const initial: Record<string, number> = {};
    baseline.available_parameters.forEach((param) => {
      if (param.current_value !== null) {
        initial[param.key] = param.current_value;
      }
    });
    setParameterValues(initial);
    setScenarioName('Custom What-If Scenario');
    setScenarioDescription('');
  };

  // Update single parameter
  const handleParamChange = (key: string, value: number) => {
    setParameterValues((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  // Run Simulation
  const handleRunSimulation = async () => {
    if (!activeProject || !baseline) return;
    setIsExecuting(true);
    setError(null);

    try {
      const modifiedParams: SimulationParameterInput[] = [];
      baseline.available_parameters.forEach((p) => {
        const proposed = parameterValues[p.key];
        if (proposed !== undefined && proposed !== p.current_value) {
          modifiedParams.push({
            parameter_key: p.key,
            proposed_value: proposed,
            user_notes: `What-If test for ${p.name}`,
          });
        }
      });

      // If user hasn't changed anything, test at least one default delta or alert
      if (modifiedParams.length === 0) {
        // Find first available parameter and test a 10% shift
        const firstParam = baseline.available_parameters.find((p) => p.is_available && p.current_value !== null);
        if (firstParam) {
          const stepVal = firstParam.step || 1;
          const adjusted = Math.min(firstParam.max_value, (firstParam.current_value || 0) + stepVal);
          modifiedParams.push({
            parameter_key: firstParam.key,
            proposed_value: adjusted,
            user_notes: 'Automated delta baseline check',
          });
        }
      }

      const payload: SimulationCreatePayload = {
        name: scenarioName || 'What-If Simulation Run',
        description: scenarioDescription || 'Simulated against immutable Digital Twin baseline snapshot.',
        category: scenarioCategory || 'custom',
        parameters: modifiedParams,
      };

      const result = await apiService.createSimulation(activeProject.id, payload);
      setCurrentResult(result);
      await loadHistory(activeProject.id);
    } catch (err: any) {
      console.error('Simulation execution failed:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to calculate simulation');
    } finally {
      setIsExecuting(false);
    }
  };

  // Load a saved simulation from history
  const handleLoadSavedSimulation = async (simId: number) => {
    if (!activeProject) return;
    setIsExecuting(true);
    try {
      const detail = await apiService.getSimulationDetail(activeProject.id, simId);
      setCurrentResult(detail);
      setScenarioName(detail.name);
      setScenarioCategory(detail.category);
      setScenarioDescription(detail.description || '');

      // Reflect parameters in builder
      const restored = { ...parameterValues };
      detail.parameters.forEach((p) => {
        // proposed_value string might have units like "150.0 ms"
        const num = parseFloat(p.proposed_value);
        if (!isNaN(num)) {
          restored[p.parameter_key] = num;
        }
      });
      setParameterValues(restored);
    } catch (err: any) {
      console.error('Failed to load simulation detail:', err);
      setError('Failed to load simulation details');
    } finally {
      setIsExecuting(false);
    }
  };

  // Delete saved simulation
  const handleDeleteSimulation = async (simId: number) => {
    if (!activeProject) return;
    try {
      await apiService.deleteSimulation(activeProject.id, simId);
      if (currentResult?.id === simId) {
        setCurrentResult(null);
      }
      await loadHistory(activeProject.id);
    } catch (err: any) {
      console.error('Failed to delete simulation:', err);
    }
  };

  // Compare two simulations
  const handleCompare = async () => {
    if (!activeProject || !compareSimAId || !compareSimBId) return;
    setIsComparing(true);
    try {
      const comparison = await apiService.compareSimulations(activeProject.id, compareSimAId, compareSimBId);
      setCompareData(comparison);
      setIsCompareModalOpen(true);
    } catch (err: any) {
      console.error('Failed to compare simulations:', err);
      setError('Failed to generate scenario comparison');
    } finally {
      setIsComparing(false);
    }
  };

  // Filtered parameters by category
  const filteredParameters = useMemo(() => {
    if (!baseline) return [];
    if (selectedCategoryTab === 'all') return baseline.available_parameters;
    return baseline.available_parameters.filter((p) => p.category === selectedCategoryTab);
  }, [baseline, selectedCategoryTab]);

  // Categories list with counts
  const categories = useMemo(() => {
    if (!baseline) return [];
    const set = new Set(baseline.available_parameters.map((p) => p.category));
    return ['all', ...Array.from(set)];
  }, [baseline]);

  // Filtered affected modules
  const filteredAffectedModules = useMemo(() => {
    if (!currentResult?.affected_modules) return [];
    if (affectedFilter === 'ALL') return currentResult.affected_modules;
    if (affectedFilter === 'DIRECT') return currentResult.affected_modules.filter((m) => m.impact_type === 'DIRECT');
    if (affectedFilter === 'INDIRECT') return currentResult.affected_modules.filter((m) => m.impact_type === 'INDIRECT');
    if (affectedFilter === 'HIGH_RISK') return currentResult.affected_modules.filter((m) => m.risk_level === 'HIGH' || m.risk_level === 'CRITICAL');
    return currentResult.affected_modules;
  }, [currentResult, affectedFilter]);

  // Check how many parameters have modified values
  const modifiedCount = useMemo(() => {
    if (!baseline) return 0;
    return baseline.available_parameters.filter((p) => {
      const current = parameterValues[p.key];
      return current !== undefined && current !== p.current_value;
    }).length;
  }, [baseline, parameterValues]);

  // Status helper
  const getHealthBadgeStyle = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'HEALTHY':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:border-emerald-500/30 dark:text-emerald-400';
      case 'ATTENTION':
        return 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30 dark:text-amber-400';
      case 'DEGRADED':
        return 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-500/10 dark:border-orange-500/30 dark:text-orange-400';
      case 'CRITICAL':
        return 'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-400';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400';
    }
  };

  const getRiskBadgeStyle = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30';
      case 'HIGH':
        return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30';
      case 'MEDIUM':
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30';
      default:
        return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
    }
  };

  // If no active project selected
  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
        <div className="w-16 h-16 rounded-2xl bg-cyan-50 dark:bg-cyan-950/40 border border-cyan-200 dark:border-cyan-800 flex items-center justify-center text-cyan-600 dark:text-cyan-400 mb-4 shadow-sm">
          <Sliders className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No Repository Connected</h2>
        <p className="text-sm text-slate-500 dark:text-gray-400 max-w-md mb-6">
          Connect a repository to inspect its Digital Twin snapshot and run predictive What-If architectural simulations.
        </p>
        <button
          onClick={onOpenConnectModal}
          className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm transition-all shadow-md shadow-cyan-600/20"
        >
          Connect Repository
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* ─── Top Header & Baseline Assurance ─── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 dark:border-gray-800 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
              <Sliders className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              What-If Simulation Engine
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-500/10 dark:text-cyan-400 dark:border-cyan-500/30">
              Digital Twin Core
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-gray-400 mt-1 max-w-2xl">
            Simulate hypothetical changes to API performance, dependency architecture, team dynamics, and code complexity in an isolated, immutable sandbox without touching production records.
          </p>
        </div>

        {/* Baseline Metadata Pill */}
        <div className="flex flex-wrap items-center gap-2">
          {baseline && (
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-gray-800/80 border border-slate-200 dark:border-gray-700 text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-medium text-slate-700 dark:text-gray-300">
                Baseline Snapshot v{baseline.twin_version || 1}
              </span>
              <span className="text-slate-400">|</span>
              <span className="text-slate-500 dark:text-gray-400">
                Health: <strong className="text-slate-900 dark:text-white">{baseline.health_score}</strong>/100
              </span>
              <span className="text-slate-400">|</span>
              <span className="text-slate-500 dark:text-gray-400">
                Latency: <strong className="text-slate-900 dark:text-white">{baseline.metrics.api_latency || 38}ms</strong>
              </span>
            </div>
          )}

          <button
            onClick={() => loadBaseline(activeProject.id)}
            disabled={isLoadingBaseline}
            className="p-2 rounded-lg bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 text-slate-600 dark:text-gray-300 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors shadow-sm"
            title="Refresh Digital Twin Baseline"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingBaseline ? 'animate-spin text-cyan-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* Safety / Immutable Snapshot Guarantee Banner */}
      <div className="flex items-start space-x-3 p-3.5 rounded-xl bg-cyan-500/5 border border-cyan-500/20 text-xs text-cyan-800 dark:text-cyan-300">
        <Info className="w-4 h-4 text-cyan-600 dark:text-cyan-400 shrink-0 mt-0.5" />
        <div className="flex-1">
          <strong className="font-semibold text-cyan-900 dark:text-cyan-200">
            Immutable Baseline Snapshot Active:
          </strong>{' '}
          All What-If calculations execute isolated mathematical and dependency-graph models (M/M/1 queuing, McCabe complexity, graph coupling). Actual repository code, GitHub branches, and historical Digital Twin snapshots remain strictly unaltered.
        </div>
      </div>

      {error && (
        <div className="flex items-center space-x-2 p-3 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 text-xs text-red-700 dark:text-red-400">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ─── Scenario Presets Toolbar ─── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-gray-400 flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5 text-cyan-500" />
            <span>Quick Scenario Presets</span>
          </h2>
          {modifiedCount > 0 && (
            <button
              onClick={resetToBaseline}
              className="text-xs text-cyan-600 dark:text-cyan-400 hover:underline flex items-center space-x-1"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset {modifiedCount} modified parameter{modifiedCount > 1 ? 's' : ''} to baseline</span>
            </button>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {PRESETS.map((p) => {
            const Icon = p.icon;
            return (
              <button
                key={p.id}
                onClick={() => applyPreset(p)}
                className="flex flex-col text-left p-3 rounded-xl bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 hover:border-cyan-500/50 hover:shadow-md transition-all group"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="p-1 rounded-md bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 group-hover:scale-110 transition-transform">
                    <Icon className="w-3.5 h-3.5" />
                  </span>
                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-gray-800 text-slate-500 dark:text-gray-400">
                    {p.category}
                  </span>
                </div>
                <h3 className="text-xs font-semibold text-slate-900 dark:text-white line-clamp-1 mb-1">
                  {p.name}
                </h3>
                <p className="text-[11px] text-slate-500 dark:text-gray-400 line-clamp-2 leading-relaxed">
                  {p.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* ─── Main Two-Column Layout: Parameter Builder & Live Results ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Parameter Slider Builder (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-5 rounded-2xl bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-gray-800">
              <div className="flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-cyan-500" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Hypothetical Levers
                </h3>
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-gray-400 font-mono">
                {modifiedCount} modified
              </span>
            </div>

            {/* Scenario Name & Category */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-700 dark:text-gray-300">
                Scenario Title
              </label>
              <input
                type="text"
                value={scenarioName}
                onChange={(e) => setScenarioName(e.target.value)}
                placeholder="e.g. Latency Spike & Concurrency Surge"
                className="w-full px-3 py-2 text-xs rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-gray-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            {/* Category Filter Pills */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategoryTab(cat)}
                  className={`text-[11px] px-2.5 py-1 rounded-lg capitalize font-medium transition-colors ${
                    selectedCategoryTab === cat
                      ? 'bg-cyan-600 text-white shadow-sm'
                      : 'bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-gray-400 hover:bg-slate-200 dark:hover:bg-gray-700'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Dynamic Parameter Sliders */}
            <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
              {filteredParameters.map((param) => {
                const currentVal = parameterValues[param.key] ?? param.current_value ?? 0;
                const baselineVal = param.current_value ?? 0;
                const delta = Math.round((currentVal - baselineVal) * 10) / 10;
                const deltaPct = baselineVal !== 0 ? Math.round((delta / baselineVal) * 100) : 0;
                const isModified = currentVal !== baselineVal;

                return (
                  <div
                    key={param.key}
                    className={`p-3 rounded-xl border transition-all ${
                      isModified
                        ? 'bg-cyan-50/40 dark:bg-cyan-950/20 border-cyan-300 dark:border-cyan-800'
                        : 'bg-slate-50/50 dark:bg-[#0B0F17]/50 border-slate-200 dark:border-gray-800'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-1.5">
                      <div>
                        <div className="flex items-center space-x-1.5">
                          <span className="text-xs font-semibold text-slate-900 dark:text-white">
                            {param.name}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-gray-800 text-slate-600 dark:text-gray-400">
                            {param.unit}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 dark:text-gray-400 mt-0.5 leading-snug">
                          {param.description}
                        </p>
                      </div>

                      {/* Delta Indicator */}
                      {isModified && (
                        <div className="flex items-center space-x-1 shrink-0 text-[11px] font-mono font-semibold">
                          <span className={delta > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}>
                            {delta > 0 ? `+${delta}` : delta}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            ({delta > 0 ? `+${deltaPct}%` : `${deltaPct}%`})
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Slider & Numeric Value Input */}
                    <div className="flex items-center space-x-3 pt-1">
                      <input
                        type="range"
                        min={param.min_value}
                        max={param.max_value}
                        step={param.step}
                        value={currentVal}
                        onChange={(e) => handleParamChange(param.key, parseFloat(e.target.value))}
                        disabled={!param.is_available}
                        className="flex-1 h-1.5 bg-slate-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-600"
                      />
                      <div className="flex items-center space-x-1">
                        <input
                          type="number"
                          min={param.min_value}
                          max={param.max_value}
                          step={param.step}
                          value={currentVal}
                          onChange={(e) => handleParamChange(param.key, parseFloat(e.target.value) || 0)}
                          disabled={!param.is_available}
                          className="w-16 px-2 py-1 text-xs text-right font-mono font-medium rounded-lg bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
                        />
                        {isModified && (
                          <button
                            onClick={() => handleParamChange(param.key, baselineVal)}
                            className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-gray-300"
                            title="Reset to baseline"
                          >
                            <RotateCcw className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="flex justify-between items-center text-[10px] text-slate-400 mt-1 font-mono">
                      <span>Baseline: {baselineVal} {param.unit}</span>
                      <span>Max: {param.max_value} {param.unit}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Run Button */}
            <button
              onClick={handleRunSimulation}
              disabled={isExecuting}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-sm flex items-center justify-center space-x-2 transition-all shadow-md shadow-cyan-600/20 disabled:opacity-50"
            >
              {isExecuting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Computing Cascading Impact...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  <span>Run What-If Simulation</span>
                </>
              )}
            </button>
          </div>

          {/* Saved History Quick Card */}
          <div className="p-4 rounded-2xl bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-gray-400 flex items-center space-x-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-500" />
                <span>Saved Scenarios ({savedSimulations.length})</span>
              </h4>
              {savedSimulations.length >= 2 && (
                <button
                  onClick={handleCompare}
                  disabled={isComparing}
                  className="text-xs px-2.5 py-1 rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-500/10 dark:text-cyan-400 font-semibold hover:underline flex items-center space-x-1"
                >
                  <Scale className="w-3 h-3" />
                  <span>Compare Scenarios</span>
                </button>
              )}
            </div>

            {savedSimulations.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No previous simulations saved yet.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {savedSimulations.map((sim) => (
                  <div
                    key={sim.id}
                    className={`flex items-center justify-between p-2.5 rounded-xl border text-xs transition-all ${
                      currentResult?.id === sim.id
                        ? 'bg-cyan-50/60 dark:bg-cyan-950/30 border-cyan-400 dark:border-cyan-700'
                        : 'bg-slate-50 dark:bg-[#0B0F17] border-slate-200 dark:border-gray-800 hover:border-slate-300'
                    }`}
                  >
                    <div className="min-w-0 flex-1 cursor-pointer" onClick={() => handleLoadSavedSimulation(sim.id)}>
                      <p className="font-semibold text-slate-900 dark:text-white truncate">
                        {sim.name}
                      </p>
                      <div className="flex items-center space-x-2 text-[10px] text-slate-500 dark:text-gray-400 mt-0.5">
                        <span>Score: {sim.simulated_score}/100</span>
                        <span>•</span>
                        <span className={sim.score_delta && sim.score_delta > 0 ? 'text-emerald-500' : 'text-red-500'}>
                          {sim.score_delta && sim.score_delta > 0 ? `+${sim.score_delta}` : sim.score_delta} pts
                        </span>
                        <span>•</span>
                        <span>{new Date(sim.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-1 shrink-0 ml-2">
                      <button
                        onClick={() => handleLoadSavedSimulation(sim.id)}
                        className="p-1 rounded text-slate-400 hover:text-cyan-500"
                        title="Load"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteSimulation(sim.id)}
                        className="p-1 rounded text-slate-400 hover:text-red-500"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Simulation Outcomes & Cascading Propagation (7 Cols) */}
        <div className="lg:col-span-7 space-y-5">
          {!currentResult ? (
            <div className="flex flex-col items-center justify-center min-h-[460px] p-8 rounded-2xl bg-white dark:bg-[#111622] border border-dashed border-slate-300 dark:border-gray-800 text-center">
              <div className="w-14 h-14 rounded-2xl bg-cyan-50 dark:bg-cyan-950/40 border border-cyan-200 dark:border-cyan-800 flex items-center justify-center text-cyan-600 dark:text-cyan-400 mb-3">
                <Play className="w-6 h-6 ml-0.5" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">
                Configure Levers & Run Simulation
              </h3>
              <p className="text-xs text-slate-500 dark:text-gray-400 max-w-sm mb-4">
                Select a quick preset above or adjust the sliders to test hypothetical architecture and latency modifications against the Digital Twin.
              </p>
              <button
                onClick={handleRunSimulation}
                disabled={isExecuting}
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs transition-all shadow-sm"
              >
                Run Baseline Simulation
              </button>
            </div>
          ) : (
            <>
              {/* ─── Metric Scoreboard (Baseline vs Simulated) ─── */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {/* Health Score Tile */}
                <div className="p-4 rounded-2xl bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 shadow-sm space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider">
                    Project Health
                  </span>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-2xl font-black text-slate-900 dark:text-white">
                      {currentResult.health_impact.simulated_score}
                    </span>
                    <span className="text-xs text-slate-400">/100</span>
                    {currentResult.health_impact.delta !== null && (
                      <span
                        className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                          currentResult.health_impact.delta >= 0
                            ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400'
                            : 'bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400'
                        }`}
                      >
                        {currentResult.health_impact.delta >= 0 ? `+${currentResult.health_impact.delta}` : currentResult.health_impact.delta}
                      </span>
                    )}
                  </div>
                  <div className="pt-1">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${getHealthBadgeStyle(currentResult.health_impact.simulated_status)}`}>
                      {currentResult.health_impact.simulated_status}
                    </span>
                  </div>
                </div>

                {/* API Latency Tile */}
                <div className="p-4 rounded-2xl bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 shadow-sm space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider">
                    API Latency
                  </span>
                  <div className="flex items-baseline space-x-1.5">
                    <span className="text-2xl font-black text-slate-900 dark:text-white">
                      {currentResult.simulated_metrics.api_latency ?? 38}
                    </span>
                    <span className="text-xs text-slate-400">ms</span>
                  </div>
                  <p className="text-[10px] text-slate-500 dark:text-gray-400">
                    Baseline: {currentResult.baseline_metrics.api_latency ?? 38} ms
                  </p>
                </div>

                {/* Cyclomatic Complexity Tile */}
                <div className="p-4 rounded-2xl bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 shadow-sm space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider">
                    Module Complexity
                  </span>
                  <div className="flex items-baseline space-x-1.5">
                    <span className="text-2xl font-black text-slate-900 dark:text-white">
                      {currentResult.simulated_metrics.module_complexity ?? 7.5}
                    </span>
                    <span className="text-xs text-slate-400">CC</span>
                  </div>
                  <p className="text-[10px] text-slate-500 dark:text-gray-400">
                    Baseline: {currentResult.baseline_metrics.module_complexity ?? 7.5} CC
                  </p>
                </div>

                {/* Technical Debt Delta Tile */}
                <div className="p-4 rounded-2xl bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 shadow-sm space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 dark:text-gray-400 uppercase tracking-wider">
                    Debt Remediation
                  </span>
                  <div className="flex items-baseline space-x-1.5">
                    <span className={`text-2xl font-black ${(currentResult.simulated_metrics.technical_debt_hours_delta || 0) > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                      {(currentResult.simulated_metrics.technical_debt_hours_delta || 0) > 0 ? `+${currentResult.simulated_metrics.technical_debt_hours_delta}` : currentResult.simulated_metrics.technical_debt_hours_delta || 0}
                    </span>
                    <span className="text-xs text-slate-400">hrs</span>
                  </div>
                  <p className="text-[10px] text-slate-500 dark:text-gray-400">
                    McCabe Debt Shift
                  </p>
                </div>
              </div>

              {/* ─── Cascading Affected Modules Propagation ─── */}
              <div className="p-5 rounded-2xl bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100 dark:border-gray-800">
                  <div className="flex items-center space-x-2">
                    <Network className="w-4 h-4 text-cyan-500" />
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      Digital Twin Cascading Module Impact
                    </h3>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 dark:bg-cyan-500/10 dark:text-cyan-400 font-mono font-semibold">
                      Blast Radius: Tier {currentResult.cascading_depth || 1}
                    </span>
                  </div>

                  {/* Filter Pills */}
                  <div className="flex items-center space-x-1">
                    {(['ALL', 'DIRECT', 'INDIRECT', 'HIGH_RISK'] as const).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setAffectedFilter(mode)}
                        className={`text-[10px] px-2 py-1 rounded-md font-medium transition-colors ${
                          affectedFilter === mode
                            ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                            : 'bg-slate-100 dark:bg-gray-800 text-slate-500 dark:text-gray-400 hover:bg-slate-200'
                        }`}
                      >
                        {mode.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Modules Grid */}
                <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
                  {filteredAffectedModules.length === 0 ? (
                    <p className="text-xs text-slate-400 italic py-4 text-center">
                      No component modules match this filter.
                    </p>
                  ) : (
                    filteredAffectedModules.map((m, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-slate-50/70 dark:bg-[#0B0F17]/70 border border-slate-200/80 dark:border-gray-800 hover:border-cyan-500/40 transition-all space-y-2"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="flex items-center space-x-2">
                              <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                              <span className="text-xs font-bold text-slate-900 dark:text-white font-mono truncate">
                                {m.module_name}
                              </span>
                              <span
                                className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                                  m.impact_type === 'DIRECT'
                                    ? 'bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400 border border-purple-200 dark:border-purple-500/30'
                                    : 'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/10 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-500/30'
                                }`}
                              >
                                {m.impact_type} (Tier {m.blast_radius_depth})
                              </span>
                            </div>
                            <p className="text-[10px] text-slate-400 font-mono truncate mt-0.5 ml-5">
                              {m.file_path}
                            </p>
                          </div>

                          <span className={`text-[10px] px-2 py-0.5 rounded font-bold border shrink-0 ${getRiskBadgeStyle(m.risk_level)}`}>
                            {m.risk_level} RISK
                          </span>
                        </div>

                        {/* Metric Shifts & Actionable Mitigation */}
                        <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] pt-1 border-t border-slate-200/50 dark:border-gray-800/60 text-slate-600 dark:text-gray-400 font-mono">
                          <div className="flex items-center space-x-3">
                            <span>Latency: <strong className="text-slate-900 dark:text-white">{m.estimated_latency_ms}ms</strong></span>
                            <span>Δ Complexity: <strong className="text-slate-900 dark:text-white">+{m.complexity_delta} CC</strong></span>
                            <span>Coupling: <strong className="text-slate-900 dark:text-white">{m.coupling_score}</strong></span>
                          </div>
                          {m.mitigation && (
                            <span className="text-[10px] text-cyan-600 dark:text-cyan-400 font-sans italic">
                              💡 {m.mitigation}
                            </span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* ─── Explainable AI (XAI) Insight Panel ─── */}
              <div className="p-5 rounded-2xl bg-white dark:bg-[#111622] border border-slate-200 dark:border-gray-800 shadow-sm space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-gray-800">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-cyan-500" />
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      Explainable AI (XAI) Architecture Analysis
                    </h3>
                  </div>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full font-mono bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-gray-400 border border-slate-200 dark:border-gray-700">
                    Engine: {currentResult.ai_explanation.provider}
                  </span>
                </div>

                {/* Summary & Reasoning */}
                <div className="space-y-2 text-xs leading-relaxed text-slate-700 dark:text-gray-300">
                  <p className="font-semibold text-slate-900 dark:text-white">
                    {currentResult.ai_explanation.summary}
                  </p>
                  <p className="p-3 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200/80 dark:border-gray-800 text-slate-600 dark:text-gray-400">
                    {currentResult.ai_explanation.why_it_happens}
                  </p>
                </div>

                {/* Contributing Factors & Assumptions */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-gray-800 space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-gray-400 flex items-center space-x-1">
                      <Zap className="w-3 h-3 text-amber-500" />
                      <span>Contributing Factors</span>
                    </span>
                    <ul className="text-xs space-y-1 text-slate-600 dark:text-gray-400">
                      {currentResult.ai_explanation.contributing_factors?.map((f, i) => (
                        <li key={i} className="flex items-start space-x-1.5">
                          <span className="text-cyan-500">•</span>
                          <span>{f}</span>
                        </li>
                      )) || <li>Parameter changes tested</li>}
                    </ul>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-gray-800 space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-gray-400 flex items-center space-x-1">
                      <ShieldAlert className="w-3 h-3 text-cyan-500" />
                      <span>Evidence & Assumptions</span>
                    </span>
                    <ul className="text-xs space-y-1 text-slate-600 dark:text-gray-400">
                      {currentResult.ai_explanation.assumptions?.slice(0, 3).map((a, i) => (
                        <li key={i} className="flex items-start space-x-1.5">
                          <span className="text-cyan-500">•</span>
                          <span>{a}</span>
                        </li>
                      )) || <li>Deterministic queuing and graph propagation models applied.</li>}
                    </ul>
                  </div>
                </div>

                {/* Actionable Strategic Mitigations */}
                {currentResult.ai_explanation.actionable_mitigations && currentResult.ai_explanation.actionable_mitigations.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-emerald-500/5 border border-emerald-500/20 space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 flex items-center space-x-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Actionable Mitigations</span>
                    </span>
                    <ul className="text-xs space-y-1.5 text-slate-700 dark:text-gray-300">
                      {currentResult.ai_explanation.actionable_mitigations.map((m, i) => (
                        <li key={i} className="flex items-start space-x-2">
                          <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                          <span>{m}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ─── Side-by-Side Comparison Modal ─── */}
      {isCompareModalOpen && compareData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-[#111622] rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 dark:border-gray-800 shadow-2xl p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-gray-800">
              <div className="flex items-center space-x-2">
                <Scale className="w-5 h-5 text-cyan-500" />
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Scenario Comparative Analysis
                </h3>
              </div>
              <button
                onClick={() => setIsCompareModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-gray-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Winner / Advantage Highlight Banner */}
            <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-xs text-cyan-900 dark:text-cyan-200 space-y-1">
              <strong className="font-bold">Comparative Summary:</strong>
              <p>{compareData.comparative_summary}</p>
            </div>

            {/* Health Comparison Grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-gray-800 space-y-1">
                <span className="text-xs font-bold text-slate-900 dark:text-white">
                  Scenario A: {compareData.simulation_a.name}
                </span>
                <div className="flex items-baseline space-x-2">
                  <span className="text-2xl font-black text-cyan-600 dark:text-cyan-400">
                    {compareData.health_comparison.sim_a_score}
                  </span>
                  <span className="text-xs text-slate-400">/100</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold border ${getHealthBadgeStyle(compareData.health_comparison.sim_a_status)}`}>
                    {compareData.health_comparison.sim_a_status}
                  </span>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-gray-800 space-y-1">
                <span className="text-xs font-bold text-slate-900 dark:text-white">
                  Scenario B: {compareData.simulation_b.name}
                </span>
                <div className="flex items-baseline space-x-2">
                  <span className="text-2xl font-black text-blue-600 dark:text-blue-400">
                    {compareData.health_comparison.sim_b_score}
                  </span>
                  <span className="text-xs text-slate-400">/100</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold border ${getHealthBadgeStyle(compareData.health_comparison.sim_b_status)}`}>
                    {compareData.health_comparison.sim_b_status}
                  </span>
                </div>
              </div>
            </div>

            {/* Metrics Difference Table */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-gray-400">
                Key Metrics Side-by-Side
              </h4>
              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-gray-800">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-50 dark:bg-[#0B0F17] text-slate-500 dark:text-gray-400 font-mono">
                    <tr>
                      <th className="p-2.5">Metric</th>
                      <th className="p-2.5">Scenario A</th>
                      <th className="p-2.5">Scenario B</th>
                      <th className="p-2.5 text-right">Net Shift</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-gray-800">
                    {compareData.metric_comparisons.map((m, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-gray-800/30">
                        <td className="p-2.5 font-medium text-slate-900 dark:text-white">
                          {m.metric_name}
                        </td>
                        <td className="p-2.5 font-mono">{m.sim_a_value ?? '—'} {m.unit}</td>
                        <td className="p-2.5 font-mono">{m.sim_b_value ?? '—'} {m.unit}</td>
                        <td className={`p-2.5 text-right font-mono font-bold ${
                          (m.difference || 0) > 0 ? 'text-cyan-500' : (m.difference || 0) < 0 ? 'text-amber-500' : 'text-slate-400'
                        }`}>
                          {m.difference !== null && m.difference !== undefined ? (m.difference > 0 ? `+${m.difference}` : m.difference) : '—'} {m.unit}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setIsCompareModalOpen(false)}
                className="px-5 py-2 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-xs font-semibold hover:opacity-90 transition-opacity"
              >
                Close Comparison
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SimulationPage;
