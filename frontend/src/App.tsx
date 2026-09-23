import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar, NAV_ITEMS } from './components/common/Sidebar';
import { Header } from './components/common/Header';
import { ConnectRepoModal } from './components/common/ConnectRepoModal';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectOverviewPage } from './pages/ProjectOverviewPage';
import { SoftwareHealthPage } from './pages/SoftwareHealthPage';
import { RiskAnalysisPage } from './pages/RiskAnalysisPage';
import { SoftwareEvolutionPage } from './pages/SoftwareEvolutionPage';
import { TechnicalDebtPage } from './pages/TechnicalDebtPage';
import { DigitalTwinPage } from './pages/DigitalTwinPage';
import { SettingsPage } from './pages/SettingsPage';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { apiService } from './services/api';
import {
  HealthResponse,
  Project,
  LiveDashboardData,
  ProjectOverviewData,
} from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [dashboardData, setDashboardData] = useState<LiveDashboardData | null>(null);
  const [overviewData, setOverviewData] = useState<ProjectOverviewData | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch health check status
  const fetchHealth = useCallback(async () => {
    try {
      const h = await apiService.getHealth();
      setHealth(h);
    } catch (err: any) {
      console.warn('Health check unreachable:', err);
      setHealth({
        status: 'degraded',
        service: 'AI Digital Twin for Software Intelligence',
        version: '0.1.0',
        environment: 'development',
        timestamp: new Date().toISOString(),
        database: { connected: false, status: 'disconnected' },
        github: { connected: false, remaining_rate_limit: 0, limit: 60, authenticated: false },
      });
    }
  }, []);

  // Fetch project specific data (Dashboard and Overview)
  const fetchProjectData = useCallback(async (projectId: number) => {
    setIsLoading(true);
    try {
      const [dash, over] = await Promise.all([
        apiService.getDashboard(projectId),
        apiService.getOverview(projectId),
      ]);
      setDashboardData(dash);
      setOverviewData(over);
      setError(null);
    } catch (err: any) {
      console.error(`Error loading data for project ${projectId}:`, err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load project telemetry');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize and load projects
  const loadProjects = useCallback(async () => {
    setIsLoading(true);
    try {
      const projs = await apiService.getProjects();
      setProjects(projs);

      if (projs.length === 0) {
        setActiveProject(null);
        setDashboardData(null);
        setOverviewData(null);
        setIsLoading(false);
        return;
      }

      // Check saved project in localStorage or use active/first
      const savedId = localStorage.getItem('activeProjectId');
      let targetProj: Project | undefined;
      if (savedId) {
        targetProj = projs.find((p) => p.id === parseInt(savedId, 10));
      }
      if (!targetProj) {
        targetProj = projs.find((p) => p.is_active) || projs[0];
      }

      setActiveProject(targetProj);
      localStorage.setItem('activeProjectId', targetProj.id.toString());
      await fetchProjectData(targetProj.id);
    } catch (err: any) {
      console.error('Error loading projects list:', err);
      setError('Failed to connect to backend service.');
      setIsLoading(false);
    }
  }, [fetchProjectData]);

  useEffect(() => {
    fetchHealth();
    loadProjects();

    // Health telemetry heartbeat every 20 seconds
    const interval = setInterval(fetchHealth, 20000);
    return () => clearInterval(interval);
  }, [fetchHealth, loadProjects]);

  // Connect new repository handler
  const handleConnectRepository = async (repoUrl: string) => {
    const newProject = await apiService.connectRepository(repoUrl);
    localStorage.setItem('activeProjectId', newProject.id.toString());
    setActiveProject(newProject);
    await loadProjects();
    await fetchProjectData(newProject.id);
    setActiveTab('dashboard');
  };

  // Switch active repository handler
  const handleSelectProject = async (projectId: number) => {
    if (activeProject?.id === projectId) return;
    try {
      setIsLoading(true);
      const switched = await apiService.activateProject(projectId);
      setActiveProject(switched);
      localStorage.setItem('activeProjectId', switched.id.toString());

      // Update projects list active indicator
      setProjects((prev) =>
        prev.map((p) => ({
          ...p,
          is_active: p.id === projectId,
        }))
      );

      await fetchProjectData(projectId);
    } catch (err: any) {
      console.error('Failed to switch project:', err);
      setError(err?.response?.data?.detail || 'Failed to switch project');
    } finally {
      setIsLoading(false);
    }
  };

  // Re-synchronize active repository handler
  const handleSyncActiveProject = async () => {
    if (!activeProject) return;
    setIsSyncing(true);
    try {
      const synced = await apiService.syncProject(activeProject.id);
      setActiveProject(synced);
      await fetchProjectData(activeProject.id);
      await fetchHealth();
    } catch (err: any) {
      console.error('Failed to synchronize project:', err);
      setError(err?.response?.data?.detail || 'Failed to synchronize with GitHub');
    } finally {
      setIsSyncing(false);
    }
  };

  const currentNavItem = NAV_ITEMS.find((item) => item.id === activeTab);

  return (
    <div className="flex h-screen bg-[#0B0F17] text-slate-100 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Header */}
        <Header
          health={health}
          projects={projects}
          activeProject={activeProject}
          isLoading={isLoading}
          isSyncing={isSyncing}
          onSync={handleSyncActiveProject}
          onSelectProject={handleSelectProject}
          onOpenConnectModal={() => setIsConnectModalOpen(true)}
        />

        {/* Content Area */}
        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
          {activeTab === 'dashboard' ? (
            <DashboardPage
              health={health}
              activeProject={activeProject}
              dashboardData={dashboardData}
              isLoading={isLoading}
              error={error}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
            />
          ) : activeTab === 'project-overview' ? (
            <ProjectOverviewPage
              activeProject={activeProject}
              overviewData={overviewData}
              isLoading={isLoading}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
            />
          ) : activeTab === 'software-health' ? (
            <SoftwareHealthPage
              activeProject={activeProject}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
            />
          ) : activeTab === 'risk-analysis' ? (
            <RiskAnalysisPage
              activeProject={activeProject}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
            />
          ) : activeTab === 'evolution' ? (
            <SoftwareEvolutionPage
              activeProject={activeProject}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
            />
          ) : activeTab === 'technical-debt' ? (
            <TechnicalDebtPage
              activeProject={activeProject}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
            />
          ) : activeTab === 'digital-twin' ? (
            <DigitalTwinPage
              activeProject={activeProject}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
              onSync={handleSyncActiveProject}
              isSyncing={isSyncing}
            />
          ) : activeTab === 'settings' ? (
            <SettingsPage
              activeProject={activeProject}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
            />
          ) : currentNavItem ? (
            <PlaceholderPage item={currentNavItem} />
          ) : null}
        </main>
      </div>

      {/* Connect Repository Modal */}
      <ConnectRepoModal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        onConnect={handleConnectRepository}
      />
    </div>
  );
};

export default App;
