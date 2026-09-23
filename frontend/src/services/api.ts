import axios from 'axios';
import {
  HealthResponse,
  Project,
  LiveDashboardData,
  ProjectOverviewData,
  SoftwareHealthData,
  RiskAnalysisData,
  EvolutionData,
  TechnicalDebtData,
  DigitalTwinStateData,
  DigitalTwinCore,
  DigitalTwinSnapshot,
  DigitalTwinChange,
  DigitalTwinEvent,
  DigitalTwinCompareResult,
  DigitalTwinSyncResult,
  DigitalTwinFullState,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export const apiService = {
  async getHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },

  async getProjects(): Promise<Project[]> {
    const response = await apiClient.get<Project[]>('/projects');
    return response.data;
  },

  async getActiveProject(): Promise<Project | null> {
    const response = await apiClient.get<Project | null>('/projects/active');
    return response.data;
  },

  async connectRepository(repoUrl: string): Promise<Project> {
    const response = await apiClient.post<Project>('/projects/connect', {
      repo_url: repoUrl,
    });
    return response.data;
  },

  async activateProject(projectId: number): Promise<Project> {
    const response = await apiClient.post<Project>(`/projects/${projectId}/activate`);
    return response.data;
  },

  async syncProject(projectId: number): Promise<Project> {
    const response = await apiClient.post<Project>(`/projects/${projectId}/sync`);
    return response.data;
  },

  async getDashboard(projectId: number): Promise<LiveDashboardData> {
    const response = await apiClient.get<LiveDashboardData>(`/projects/${projectId}/dashboard`);
    return response.data;
  },

  async getOverview(projectId: number): Promise<ProjectOverviewData> {
    const response = await apiClient.get<ProjectOverviewData>(`/projects/${projectId}/overview`);
    return response.data;
  },

  async deleteProject(projectId: number): Promise<void> {
    await apiClient.delete(`/projects/${projectId}`);
  },

  // ─── Analytics Endpoints ──────────────────────────────────────────────────

  async getSoftwareHealth(projectId: number): Promise<SoftwareHealthData> {
    const response = await apiClient.get<SoftwareHealthData>(`/projects/${projectId}/health`);
    return response.data;
  },

  async getRiskAnalysis(projectId: number): Promise<RiskAnalysisData> {
    const response = await apiClient.get<RiskAnalysisData>(`/projects/${projectId}/risks`);
    return response.data;
  },

  async getEvolution(projectId: number): Promise<EvolutionData> {
    const response = await apiClient.get<EvolutionData>(`/projects/${projectId}/evolution`);
    return response.data;
  },

  async getTechnicalDebt(projectId: number): Promise<TechnicalDebtData> {
    const response = await apiClient.get<TechnicalDebtData>(`/projects/${projectId}/technical-debt`);
    return response.data;
  },

  async getDigitalTwinState(projectId: number): Promise<DigitalTwinStateData> {
    const response = await apiClient.get<DigitalTwinStateData>(`/projects/${projectId}/digital-twin`);
    return response.data;
  },

  // ─── Phase 3: Digital Twin Core Endpoints ──────────────────────────────────

  async getDigitalTwinCore(projectId: number): Promise<DigitalTwinCore> {
    const response = await apiClient.get<DigitalTwinCore>(`/projects/${projectId}/digital-twin`);
    return response.data;
  },

  async getDigitalTwinFullState(projectId: number): Promise<DigitalTwinFullState> {
    const response = await apiClient.get<DigitalTwinFullState>(`/projects/${projectId}/digital-twin/state`);
    return response.data;
  },

  async initializeDigitalTwin(projectId: number): Promise<DigitalTwinSyncResult> {
    const response = await apiClient.post<DigitalTwinSyncResult>(`/projects/${projectId}/digital-twin/initialize`);
    return response.data;
  },

  async syncDigitalTwin(projectId: number): Promise<DigitalTwinSyncResult> {
    const response = await apiClient.post<DigitalTwinSyncResult>(`/projects/${projectId}/digital-twin/sync`);
    return response.data;
  },

  async getDigitalTwinSnapshots(projectId: number): Promise<DigitalTwinSnapshot[]> {
    const response = await apiClient.get<DigitalTwinSnapshot[]>(`/projects/${projectId}/digital-twin/snapshots`);
    return response.data;
  },

  async getDigitalTwinSnapshotDetail(
    projectId: number,
    snapshotId: number
  ): Promise<{ snapshot: DigitalTwinSnapshot; changes: DigitalTwinChange[] }> {
    const response = await apiClient.get<{ snapshot: DigitalTwinSnapshot; changes: DigitalTwinChange[] }>(
      `/projects/${projectId}/digital-twin/snapshots/${snapshotId}`
    );
    return response.data;
  },

  async compareDigitalTwinSnapshots(
    projectId: number,
    vFrom?: number,
    vTo?: number
  ): Promise<DigitalTwinCompareResult> {
    const params: Record<string, number> = {};
    if (vFrom !== undefined) params.v_from = vFrom;
    if (vTo !== undefined) params.v_to = vTo;
    const response = await apiClient.get<DigitalTwinCompareResult>(
      `/projects/${projectId}/digital-twin/compare`,
      { params }
    );
    return response.data;
  },

  async getDigitalTwinChanges(
    projectId: number,
    limit: number = 50,
    snapshotId?: number
  ): Promise<DigitalTwinChange[]> {
    const params: Record<string, any> = { limit };
    if (snapshotId) params.snapshot_id = snapshotId;
    const response = await apiClient.get<DigitalTwinChange[]>(
      `/projects/${projectId}/digital-twin/changes`,
      { params }
    );
    return response.data;
  },

  async getDigitalTwinEvents(
    projectId: number,
    limit: number = 50
  ): Promise<DigitalTwinEvent[]> {
    const response = await apiClient.get<DigitalTwinEvent[]>(
      `/projects/${projectId}/digital-twin/events`,
      { params: { limit } }
    );
    return response.data;
  },
};
