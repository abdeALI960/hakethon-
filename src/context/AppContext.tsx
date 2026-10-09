import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import confetti from 'canvas-confetti';
import type {
  BackendEndpoint,
  BackendIncident,
  BackendServiceHealth,
  EmergencyCaseIntake,
  EmergencyIntakeRequest,
  IncidentRecord,
  KpiResponse,
  ProbeInterval,
  RoadmapStep,
  ServiceNode,
  SettingsResponse,
  TargetEndpointConfig,
  TelemetryLogLine,
} from '../types';
import {
  ApiError,
  apiClient,
  CHAOS_SCENARIOS,
  ChaosScenario,
  hasConfiguredBackend,
} from '../services/apiClient';
import {
  INITIAL_ENDPOINT_CONFIG,
  INITIAL_INCIDENTS,
  INITIAL_SERVICES,
  ROADMAP_STEPS,
} from '../services/mockData';
import { sanitizeDisplay } from '../utils/sanitize';

export type AppTab = 'incident-report' | 'live-overview';
export type BackendStatus = 'connected' | 'offline' | 'mock';
export type SimulationStage =
  | 'IDLE'
  | 'CHAOS_INJECTED'
  | 'DETECTING'
  | 'AI_ANALYZING'
  | 'AUTO_FIXING'
  | 'VERIFIED';

interface AppContextType {
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;
  backendStatus: BackendStatus;
  endpointConfig: TargetEndpointConfig;
  setEndpointConfig: React.Dispatch<React.SetStateAction<TargetEndpointConfig>>;
  services: ServiceNode[];
  setServices: React.Dispatch<React.SetStateAction<ServiceNode[]>>;
  incidents: IncidentRecord[];
  roadmapSteps: RoadmapStep[];
  emergencyCases: EmergencyCaseIntake[];
  endpoints: BackendEndpoint[];
  kpis: KpiResponse | null;
  runtimeSettings: SettingsResponse | null;
  dashboardLoading: boolean;
  dashboardError: string | null;
  terminalLogs: TelemetryLogLine[];
  chaosRequestInFlight: boolean;
  isProbing: boolean;
  forceProbe: (url?: string) => Promise<void>;
  updateTarget: (url: string, interval: ProbeInterval) => Promise<void>;
  addEndpoint: (name: string, port: number, url: string) => Promise<void>;
  deleteEndpoint: (id: number) => Promise<void>;
  activeStage: SimulationStage;
  activeScenario: ChaosScenario | null;
  stageProgress: number;
  stageMessage: string;
  triggerChaos: (scenario: ChaosScenario) => Promise<void>;
  runFullDemo: () => void;
  resetServices: () => void;
  isSqliteModalOpen: boolean;
  setIsSqliteModalOpen: (open: boolean) => void;
  isChangeTargetModalOpen: boolean;
  setIsChangeTargetModalOpen: (open: boolean) => void;
  isAddEndpointModalOpen: boolean;
  setIsAddEndpointModalOpen: (open: boolean) => void;
  isEmergencyIntakeModalOpen: boolean;
  setIsEmergencyIntakeModalOpen: (open: boolean) => void;
  isProfileSettingsModalOpen: boolean;
  setIsProfileSettingsModalOpen: (open: boolean) => void;
  downloadReport: () => void;
  submitEmergencyCase: (
    caseData: Omit<EmergencyCaseIntake, 'caseId' | 'timestamp'>,
    image?: File,
  ) => Promise<void>;
  saveSettings: (settings: Partial<SettingsResponse>) => Promise<void>;
  refreshDashboard: () => Promise<void>;
  toast: { message: string; type: 'success' | 'info' | 'warning' } | null;
  showToast: (message: string, type?: 'success' | 'info' | 'warning') => void;
  totalIncidents: number;
  autoHealedRate: string;
  avgDetection: string;
  avgRecoveryTime: string;
}

const AppContext = createContext<AppContextType | null>(null);
const MAX_TERMINAL_LINES = 500;

function formatTimestamp(value: string | null): string {
  if (!value) return 'n/a';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleTimeString();
}

function incidentToRecord(incident: BackendIncident): IncidentRecord {
  const anomalyLabel =
    incident.anomalyType === 'CPU_SPIKE'
      ? 'CPU Spike'
      : incident.anomalyType === 'LATENCY'
        ? 'Slow Response'
        : incident.anomalyType === 'CRASH'
          ? 'Service Crash'
          : 'Incident';
  const status =
    incident.status === 'verified'
      ? incident.autoHealed ? 'Auto-Recovered' : 'Resolved'
      : incident.status === 'awaiting_approval'
        ? 'Awaiting Approval'
        : incident.status === 'failed'
          ? 'Failed'
          : incident.status === 'fixed'
            ? 'Remediating'
            : 'Investigating';
  const logs: TelemetryLogLine[] = incident.logs.map((log) => ({
    timestamp: formatTimestamp(log.ts),
    level: ['CRIT', 'WARN', 'INFO', 'AI-EXEC', 'FIX', 'OK'].includes(log.level)
      ? (log.level as TelemetryLogLine['level'])
      : 'INFO',
    message: sanitizeDisplay(log.message),
  }));
  return {
    id: incident.id,
    title: `${anomalyLabel} on ${incident.service}:${incident.port ?? 'unknown'}`,
    service: incident.service,
    port: incident.port ?? 0,
    timestamp: formatTimestamp(incident.injectedAt ?? incident.detectedAt),
    status,
    detectionTimeSec: incident.detectionDurationSec,
    fixTimeSec: incident.fixDurationSec,
    evidenceSnapshot: logs[0]?.message ?? 'No evidence recorded.',
    aiDiagnosticTitle: 'AI Diagnostic & Action',
    aiDiagnosticAction: sanitizeDisplay(incident.aiRationale ?? 'No diagnosis recorded.'),
    logs,
    anomalyType: incident.anomalyType,
    severity: incident.severity,
    autoHealed: incident.autoHealed,
    stageTimestamps: {
      injectedAt: incident.injectedAt,
      detectedAt: incident.detectedAt,
      diagnosedAt: incident.diagnosedAt,
      fixedAt: incident.fixedAt,
      verifiedAt: incident.verifiedAt,
    },
  };
}

function serviceStatus(service: BackendServiceHealth): ServiceNode {
  const current = INITIAL_SERVICES.find((item) => item.name === service.service);
  return {
    id: current?.id ?? `svc-${service.service}`,
    name: service.service,
    port: service.port ?? current?.port ?? 0,
    status: service.status,
    latencyMs: service.latencyMs ?? current?.latencyMs ?? 0,
    cpuPercent: current?.cpuPercent ?? 0,
    memoryMb: current?.memoryMb ?? 0,
    uptime: current?.uptime ?? 'n/a',
    url: current?.url ?? '',
  };
}

function stageFromEvent(stage: unknown, status: unknown): SimulationStage | null {
  const value = String(stage ?? status ?? '').toLowerCase();
  if (value === 'injected') return 'CHAOS_INJECTED';
  if (value === 'detected') return 'DETECTING';
  if (value === 'diagnosed') return 'AI_ANALYZING';
  if (value === 'fixed') return 'AUTO_FIXING';
  if (value === 'verified') return 'VERIFIED';
  return null;
}

function progressForStage(stage: SimulationStage): number {
  return {
    IDLE: 0,
    CHAOS_INJECTED: 15,
    DETECTING: 35,
    AI_ANALYZING: 65,
    AUTO_FIXING: 85,
    VERIFIED: 100,
  }[stage];
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return `${error.code}: ${error.message}`;
  return error instanceof Error ? error.message : 'The request failed.';
}

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<AppTab>('incident-report');
  const [backendStatus, setBackendStatus] = useState<BackendStatus>(
    hasConfiguredBackend ? 'offline' : 'mock',
  );
  const [endpointConfig, setEndpointConfig] = useState<TargetEndpointConfig>(INITIAL_ENDPOINT_CONFIG);
  const [services, setServices] = useState<ServiceNode[]>(INITIAL_SERVICES);
  const [incidents, setIncidents] = useState<IncidentRecord[]>(INITIAL_INCIDENTS);
  const [roadmapSteps] = useState<RoadmapStep[]>(ROADMAP_STEPS);
  const [emergencyCases, setEmergencyCases] = useState<EmergencyCaseIntake[]>([]);
  const [endpoints, setEndpoints] = useState<BackendEndpoint[]>([]);
  const [kpis, setKpis] = useState<KpiResponse | null>(null);
  const [runtimeSettings, setRuntimeSettings] = useState<SettingsResponse | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(hasConfiguredBackend);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [terminalLogs, setTerminalLogs] = useState<TelemetryLogLine[]>([]);
  const [isProbing, setIsProbing] = useState(false);
  const [chaosRequestInFlight, setChaosRequestInFlight] = useState(false);
  const [activeStage, setActiveStage] = useState<SimulationStage>('IDLE');
  const [activeScenario, setActiveScenario] = useState<ChaosScenario | null>(null);
  const [stageProgress, setStageProgress] = useState(0);
  const [stageMessage, setStageMessage] = useState('');
  const [isSqliteModalOpen, setIsSqliteModalOpen] = useState(false);
  const [isChangeTargetModalOpen, setIsChangeTargetModalOpen] = useState(false);
  const [isAddEndpointModalOpen, setIsAddEndpointModalOpen] = useState(false);
  const [isEmergencyIntakeModalOpen, setIsEmergencyIntakeModalOpen] = useState(false);
  const [isProfileSettingsModalOpen, setIsProfileSettingsModalOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' | 'warning' } | null>(null);
  const [streamConnected, setStreamConnected] = useState(false);
  const toastTimer = useRef<number | undefined>(undefined);
  const celebratedIncidents = useRef<Set<string>>(new Set());
  const endpointsRef = useRef(endpoints);
  const targetUrlRef = useRef(endpointConfig.url);
  const activeScenarioRef = useRef(activeScenario);
  endpointsRef.current = endpoints;
  targetUrlRef.current = endpointConfig.url;
  activeScenarioRef.current = activeScenario;

  const showToast = useCallback((message: string, type: 'success' | 'info' | 'warning' = 'info') => {
    setToast({ message: sanitizeDisplay(message), type });
    if (toastTimer.current !== undefined) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 4200);
  }, []);

  const refreshDashboard = useCallback(async () => {
    if (!hasConfiguredBackend) return;
    const [healthResult, incidentResult, kpiResult, endpointResult, settingsResult] =
      await Promise.allSettled([
        apiClient.getServicesHealth(),
        apiClient.getIncidents({ limit: 100 }),
        apiClient.getKpis(),
        apiClient.listEndpoints(),
        apiClient.getSettings(),
      ]);
    let failed = false;
    if (healthResult.status === 'fulfilled') {
      setServices(healthResult.value.map(serviceStatus));
    } else failed = true;
    if (incidentResult.status === 'fulfilled') {
      setIncidents(incidentResult.value.incidents.map(incidentToRecord));
    } else failed = true;
    if (kpiResult.status === 'fulfilled') setKpis(kpiResult.value);
    else failed = true;
    if (endpointResult.status === 'fulfilled') setEndpoints(endpointResult.value);
    else failed = true;
    if (settingsResult.status === 'fulfilled') setRuntimeSettings(settingsResult.value);
    else failed = true;
    if (failed) setDashboardError('Some backend dashboard data could not be loaded.');
    else setDashboardError(null);
  }, []);

  useEffect(() => {
    if (!hasConfiguredBackend) {
      setBackendStatus('mock');
      setDashboardLoading(false);
      return;
    }
    let active = true;

    void (async () => {
      try {
        await apiClient.getHealth();
        if (!active) return;
        setBackendStatus('connected');
        await refreshDashboard();
      } catch {
        if (!active) return;
        setBackendStatus('offline');
        setDashboardLoading(false);
        setDashboardError('Backend offline, showing simulated data.');
        return;
      } finally {
        if (active) setDashboardLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, [refreshDashboard]);

  const prependIncident = useCallback((incident: BackendIncident) => {
    const record = incidentToRecord(incident);
    setIncidents((current) => [record, ...current.filter((item) => item.id !== record.id)]);
  }, []);

  useEffect(() => {
    if (!hasConfiguredBackend || backendStatus !== 'connected') return;
    const stream = apiClient.openEventStream(
      (event) => {
        if (event.type === 'log_line') {
          const payload = event.payload;
          const line: TelemetryLogLine = {
            timestamp: formatTimestamp(event.timestamp),
            level: typeof payload.level === 'string' &&
              ['CRIT', 'WARN', 'INFO', 'AI-EXEC', 'FIX', 'OK'].includes(payload.level)
              ? (payload.level as TelemetryLogLine['level'])
              : 'INFO',
            message: sanitizeDisplay(String(payload.message ?? '')),
          };
          setTerminalLogs((current) => [...current, line].slice(-MAX_TERMINAL_LINES));
          return;
        }
        if (event.type === 'probe_result') {
          const payload = event.payload;
          const endpoint = endpointsRef.current.find((item) => item.id === event.endpointId);
          const probeStatus = typeof payload.status === 'string'
            ? payload.status
            : typeof payload.httpStatus === 'number' &&
                payload.httpStatus >= 200 && payload.httpStatus < 300
              ? 'healthy'
              : 'critical';
          if (endpoint) {
            const serviceName = endpoint.serviceKey ?? endpoint.name;
            setServices((current) => current.map((service) =>
              service.name === serviceName || service.port === endpoint.port
                ? {
                    ...service,
                    status: ['healthy', 'degraded', 'critical', 'recovering'].includes(probeStatus)
                      ? probeStatus as ServiceNode['status']
                      : service.status,
                    latencyMs: typeof payload.pingLatencyMs === 'number'
                      ? payload.pingLatencyMs
                      : service.latencyMs,
                  }
                : service,
            ));
          }
          if (endpoint && endpoint.url === targetUrlRef.current) {
            setEndpointConfig((current) => ({
              ...current,
              httpStatus: typeof payload.httpStatus === 'number' ? payload.httpStatus : 0,
              pingLatencyMs: typeof payload.pingLatencyMs === 'number' ? payload.pingLatencyMs : 0,
              sslCertDays: typeof payload.sslCertDays === 'number' ? payload.sslCertDays : 0,
              lastCheckedUtc: formatTimestamp(event.timestamp),
              status: probeStatus === 'healthy' || probeStatus === 'degraded'
                ? 'Connected & Monitored'
                : 'Disconnected',
            }));
          }
          return;
        }
        if (event.type === 'incident_created' && event.incidentId) {
          void apiClient.getIncident(event.incidentId).then(prependIncident).catch(() => undefined);
          return;
        }
        if (event.type === 'stage_changed') {
          const eventStage = String(event.payload.stage ?? event.payload.status ?? '').toLowerCase();
          if (eventStage === 'awaiting_approval') {
            setStageMessage('Remediation is awaiting operator approval.');
            return;
          }
          if (eventStage === 'failed') {
            setStageMessage('Remediation failed. Review the incident logs.');
            return;
          }
          const stage = stageFromEvent(event.payload.stage, event.payload.status);
          if (!stage) return;
          setActiveStage(stage);
          setStageProgress(progressForStage(stage));
          const scenario = CHAOS_SCENARIOS.find(
            (item) => item.targetService === (event.payload.service ?? activeScenarioRef.current?.targetService),
          );
          if (scenario) setActiveScenario(scenario);
          setStageMessage(
            stage === 'VERIFIED'
              ? 'Health check verified. Remediation completed.'
              : `Incident stage: ${stage.replaceAll('_', ' ').toLowerCase()}.`,
          );
          if (stage === 'VERIFIED' && event.incidentId) {
            void apiClient.getIncident(event.incidentId).then((incident) => {
              prependIncident(incident);
              if (incident.autoHealed && !celebratedIncidents.current.has(incident.id)) {
                celebratedIncidents.current.add(incident.id);
                confetti({
                  particleCount: 50,
                  spread: 60,
                  origin: { y: 0.7 },
                  colors: ['#4cd7f6', '#4edea3', '#06b6d4'],
                });
              }
            }).catch(() => undefined);
          }
        }
      },
      () => setStreamConnected(false),
      (connected) => setStreamConnected(connected),
    );
    return () => stream.close();
  }, [backendStatus, prependIncident]);

  useEffect(() => {
    if (!hasConfiguredBackend || backendStatus !== 'connected' || streamConnected) return;
    const interval = window.setInterval(() => {
      void refreshDashboard().catch(() => setDashboardError('Dashboard refresh failed.'));
    }, 5000);
    return () => window.clearInterval(interval);
  }, [backendStatus, refreshDashboard, streamConnected]);

  const forceProbe = useCallback(async (targetUrl = endpointConfig.url) => {
    setIsProbing(true);
    showToast(`Sending HTTP GET health probe to ${targetUrl}...`, 'info');
    try {
      const result = await apiClient.probe(targetUrl);
      setEndpointConfig((previous) => ({
        ...previous,
        httpStatus: result.httpStatus ?? 0,
        pingLatencyMs: result.pingLatencyMs,
        sslCertDays: result.sslCertDays ?? 0,
        lastCheckedUtc: result.lastCheckedUtc,
        status: result.httpStatus !== null && result.httpStatus >= 200 && result.httpStatus < 300
          ? 'Connected & Monitored'
          : 'Disconnected',
      }));
      showToast(`Health check completed: HTTP ${result.httpStatus ?? 'unavailable'} (${result.pingLatencyMs}ms)`, 'success');
    } catch (error) {
      setEndpointConfig((previous) => ({ ...previous, status: 'Disconnected' }));
      showToast(errorMessage(error), 'warning');
    } finally {
      setIsProbing(false);
    }
  }, [endpointConfig.url, showToast]);

  const updateTarget = useCallback(async (url: string, interval: ProbeInterval) => {
    const previous = endpointConfig;
    const previousEndpoints = endpoints;
    const normalizedUrl = url.trim() || 'https://myapp.internal';
    const seconds = Number(interval.replace('s', ''));
    const existing = endpoints.find((endpoint) => endpoint.url === normalizedUrl);
    const temporaryId = -Date.now();
    setEndpointConfig((current) => ({
      ...current,
      url: normalizedUrl,
      probeInterval: interval,
      lastCheckedUtc: `just now (${new Date().toISOString().substring(11, 19)} UTC)`,
    }));
    if (hasConfiguredBackend) {
      setEndpoints((current) => existing
        ? current.map((endpoint) => endpoint.id === existing.id
            ? { ...endpoint, probeIntervalSeconds: seconds }
            : endpoint)
        : [...current, {
            id: temporaryId,
            name: 'target',
            url: normalizedUrl,
            serviceKey: null,
            port: null,
            probeIntervalSeconds: seconds,
            enabled: true,
            isDemoTarget: false,
            createdAt: new Date().toISOString(),
          }]);
    }
    try {
      if (hasConfiguredBackend) {
        if (existing) {
          const updated = await apiClient.updateEndpoint(existing.id, {
            probeIntervalSeconds: seconds,
          });
          setEndpoints((current) => current.map((item) => item.id === updated.id ? updated : item));
        } else {
          const created = await apiClient.addEndpoint({
            name: 'target',
            url: normalizedUrl,
            probeIntervalSeconds: seconds,
          });
          setEndpoints((current) => current.map((item) => item.id === temporaryId ? created : item));
        }
      }
      showToast(`Target updated to ${normalizedUrl} (interval: ${interval})`, 'success');
    } catch (error) {
      setEndpointConfig(previous);
      setEndpoints(previousEndpoints);
      showToast(errorMessage(error), 'warning');
      throw error;
    }
  }, [endpointConfig, endpoints, showToast]);

  const addEndpoint = useCallback(async (name: string, port: number, url: string) => {
    const previousServices = services;
    const temporaryId = -Date.now();
    const newNode: ServiceNode = {
      id: `svc-${Date.now()}`,
      name: name.toLowerCase().trim(),
      port,
      status: 'healthy',
      latencyMs: 16,
      cpuPercent: 8.5,
      memoryMb: 195,
      uptime: '0h 01m',
      url,
    };
    setServices((current) => [...current, newNode]);
    if (hasConfiguredBackend) {
      setEndpoints((current) => [...current, {
        id: temporaryId,
        name: name.trim(),
        url,
        serviceKey: name.toLowerCase().trim(),
        port,
        probeIntervalSeconds: 2,
        enabled: true,
        isDemoTarget: false,
        createdAt: new Date().toISOString(),
      }]);
    }
    try {
      if (hasConfiguredBackend) {
        const endpoint = await apiClient.addEndpoint({
          name: name.trim(),
          port,
          url,
          serviceKey: name.toLowerCase().trim(),
          probeIntervalSeconds: 2,
        });
        setEndpoints((current) => current.map((item) => item.id === temporaryId ? endpoint : item));
      }
      showToast(`Endpoint registered: ${newNode.name} on port ${port}`, 'success');
    } catch (error) {
      setServices(previousServices);
      setEndpoints((current) => current.filter((item) => item.id !== temporaryId));
      showToast(errorMessage(error), 'warning');
      throw error;
    }
  }, [services, showToast]);

  const deleteEndpoint = useCallback(async (id: number) => {
    const existing = endpoints.find((item) => item.id === id);
    if (!existing) return;
    setEndpoints((current) => current.filter((item) => item.id !== id));
    setServices((current) => current.filter((item) => item.name !== (existing.serviceKey ?? existing.name)));
    try {
      await apiClient.deleteEndpoint(id);
      showToast(`Endpoint ${existing.name} removed.`, 'success');
    } catch (error) {
      setEndpoints((current) => [...current, existing]);
      setServices((current) => [...current, serviceStatus({
        service: existing.serviceKey ?? existing.name,
        port: existing.port,
        status: 'healthy',
        latencyMs: null,
        lastCheckedUtc: null,
      })]);
      showToast(errorMessage(error), 'warning');
    }
  }, [endpoints, showToast]);

  const resetServices = useCallback(() => {
    setServices((current) =>
      current.map((service) => ({
        ...service,
        status: 'healthy',
        latencyMs: service.name === 'web' ? 18 : service.name === 'api' ? 22 : 14,
        cpuPercent: service.name === 'worker' ? 3.1 : service.name === 'api' ? 18.2 : 12.4,
      })),
    );
    setActiveStage('IDLE');
    setActiveScenario(null);
    setStageProgress(0);
    setStageMessage('');
  }, []);

  const triggerChaos = useCallback(async (scenario: ChaosScenario) => {
    if (activeStage !== 'IDLE' || chaosRequestInFlight) return;
    setChaosRequestInFlight(true);
    setActiveScenario(scenario);
    if (backendStatus === 'connected') {
      try {
        await apiClient.injectChaos({
          service: scenario.targetService,
          port: scenario.targetPort,
          type: scenario.failureType,
        });
        setActiveStage('CHAOS_INJECTED');
        setStageProgress(progressForStage('CHAOS_INJECTED'));
        setStageMessage(`Chaos injected into ${scenario.targetService}:${scenario.targetPort}. Waiting for monitor events.`);
        showToast(`Chaos injected into ${scenario.targetService}:${scenario.targetPort}`, 'warning');
      } catch (error) {
        setActiveScenario(null);
        showToast(errorMessage(error), 'warning');
      } finally {
        setChaosRequestInFlight(false);
      }
      return;
    }

    setActiveStage('CHAOS_INJECTED');
    setStageProgress(15);
    setStageMessage(`Synthetic chaos executed: ${scenario.command}`);
    setServices((current) => current.map((service) => service.name === scenario.targetService
      ? {
          ...service,
          status: scenario.failureType === 'CRASH' ? 'critical' : 'degraded',
          latencyMs: scenario.failureType === 'HIGH_LATENCY' ? 5120 : service.latencyMs,
          cpuPercent: scenario.failureType === 'CPU_SPIKE' ? 98.4 : service.cpuPercent,
        }
      : service));
    showToast(`Chaos injected into ${scenario.targetService}:${scenario.targetPort}`, 'warning');
    setChaosRequestInFlight(false);
    window.setTimeout(() => {
      setActiveStage('DETECTING');
      setStageProgress(35);
      setStageMessage(`Monitor agent detected anomaly on ${scenario.targetService}:${scenario.targetPort}.`);
    }, 1200);
    window.setTimeout(() => {
      setActiveStage('AI_ANALYZING');
      setStageProgress(65);
      setStageMessage('Analyzing telemetry snapshots and generating root-cause diagnosis...');
    }, 2400);
    window.setTimeout(() => {
      setActiveStage('AUTO_FIXING');
      setStageProgress(85);
      setStageMessage(`Auto-fixer executing remediation: ${scenario.fixAction}`);
      setServices((current) => current.map((service) => service.name === scenario.targetService
        ? { ...service, status: 'recovering' }
        : service));
    }, 3800);
    window.setTimeout(() => {
      setActiveStage('VERIFIED');
      setStageProgress(100);
      setStageMessage('Health check verified 200 OK. Zero-touch auto-recovery complete!');
      setServices((current) => current.map((service) => service.name === scenario.targetService
        ? {
            ...service,
            status: 'healthy',
            latencyMs: service.name === 'web' ? 18 : service.name === 'api' ? 22 : 14,
            cpuPercent: service.name === 'worker' ? 3.1 : service.name === 'api' ? 18.2 : 12.4,
          }
        : service));
      const timestamp = new Date().toISOString();
      const id = `INC-${105 + Math.max(0, incidents.length - 3)}`;
      const record: IncidentRecord = {
        id,
        title: `${scenario.name} on ${scenario.targetService}:${scenario.targetPort}`,
        service: scenario.targetService,
        port: scenario.targetPort,
        timestamp,
        status: 'Auto-Recovered',
        detectionTimeSec: 2.8,
        fixTimeSec: 1.4,
        evidenceSnapshot: `Synthetic ${scenario.failureType} anomaly detected.`,
        aiDiagnosticTitle: 'AI Diagnostic & Action',
        aiDiagnosticAction: `Executed ${scenario.fixAction} and verified /healthz 200 OK.`,
        logs: [],
      };
      setIncidents((current) => [record, ...current]);
      confetti({ particleCount: 50, spread: 60, origin: { y: 0.7 }, colors: ['#4cd7f6', '#4edea3', '#06b6d4'] });
      showToast(`Incident ${id} successfully auto-healed in 1.4s!`, 'success');
      window.setTimeout(resetServices, 4000);
    }, 5200);
  }, [activeStage, backendStatus, chaosRequestInFlight, incidents.length, resetServices, services, showToast]);

  const runFullDemo = useCallback(() => {
    setActiveTab('live-overview');
    showToast('Starting OpsPilot live demonstration...', 'info');
    window.setTimeout(() => void triggerChaos(CHAOS_SCENARIOS[0]), 600);
  }, [showToast, triggerChaos]);

  const downloadReport = useCallback(() => {
    apiClient.downloadReportMarkdown(incidents);
    showToast('OpsPilot-Day5-Demo-Report.md downloaded successfully.', 'success');
  }, [incidents, showToast]);

  const submitEmergencyCase = useCallback(async (
    caseData: Omit<EmergencyCaseIntake, 'caseId' | 'timestamp'>,
    image?: File,
  ) => {
    try {
      const payload: EmergencyIntakeRequest = {
        incidentType: caseData.incidentType,
        location: caseData.location,
        priority: caseData.priority,
        reportedBy: caseData.callerOrReportedBy,
        description: caseData.description,
      };
      const response = await apiClient.submitEmergency(payload);
      if (image) await apiClient.uploadEvidence(response.caseId, image);
      const newCase: EmergencyCaseIntake = {
        ...caseData,
        caseId: response.caseId,
        timestamp: new Date().toLocaleTimeString(),
        status: 'Dispatched',
        aiTriageSummary: sanitizeDisplay(response.aiTriageSummary),
        safetyNotice: sanitizeDisplay(response.safetyNotice),
      };
      setEmergencyCases((current) => [newCase, ...current]);
      showToast(`${response.aiTriageSummary} ${response.safetyNotice}`, 'success');
      setIsEmergencyIntakeModalOpen(false);
    } catch (error) {
      showToast(errorMessage(error), 'warning');
    }
  }, [showToast]);

  const saveSettings = useCallback(async (updated: Partial<SettingsResponse>) => {
    try {
      const saved = await apiClient.updateSettings(updated);
      setRuntimeSettings(saved);
      showToast('Telemetry and daemon settings saved.', 'success');
    } catch (error) {
      showToast(errorMessage(error), 'warning');
      throw error;
    }
  }, [showToast]);

  const totalIncidents = kpis?.totalIncidents ?? incidents.length;
  const autoHealedRate = kpis
    ? `${kpis.autoHealedRatePercent.toFixed(1)}%`
    : `${incidents.length ? 100 : 0}%`;
  const avgDetection = kpis
    ? kpis.totalIncidents ? `${kpis.mttdSeconds.avg?.toFixed(1) ?? 'n/a'}s` : 'n/a'
    : incidents.some((incident) => incident.detectionTimeSec !== null)
      ? `${(incidents.reduce((sum, incident) => sum + (incident.detectionTimeSec ?? 0), 0) /
        incidents.filter((incident) => incident.detectionTimeSec !== null).length).toFixed(1)}s`
      : 'n/a';
  const avgRecoveryTime = kpis
    ? kpis.totalIncidents ? `${kpis.mttrSeconds.avg?.toFixed(1) ?? 'n/a'}s` : 'n/a'
    : incidents.some((incident) => incident.fixTimeSec !== null)
      ? `${(incidents.reduce((sum, incident) => sum + (incident.fixTimeSec ?? 0), 0) /
        incidents.filter((incident) => incident.fixTimeSec !== null).length).toFixed(1)}s`
      : 'n/a';

  return (
    <AppContext.Provider
      value={{
        activeTab,
        setActiveTab,
        backendStatus,
        endpointConfig,
        setEndpointConfig,
        services,
        setServices,
        incidents,
        roadmapSteps,
        emergencyCases,
        endpoints,
        kpis,
        runtimeSettings,
        dashboardLoading,
        dashboardError,
        terminalLogs,
        chaosRequestInFlight,
        isProbing,
        forceProbe,
        updateTarget,
        addEndpoint,
        deleteEndpoint,
        activeStage,
        activeScenario,
        stageProgress,
        stageMessage,
        triggerChaos,
        runFullDemo,
        resetServices,
        isSqliteModalOpen,
        setIsSqliteModalOpen,
        isChangeTargetModalOpen,
        setIsChangeTargetModalOpen,
        isAddEndpointModalOpen,
        setIsAddEndpointModalOpen,
        isEmergencyIntakeModalOpen,
        setIsEmergencyIntakeModalOpen,
        isProfileSettingsModalOpen,
        setIsProfileSettingsModalOpen,
        downloadReport,
        submitEmergencyCase,
        saveSettings,
        refreshDashboard,
        toast,
        showToast,
        totalIncidents,
        autoHealedRate,
        avgDetection,
        avgRecoveryTime,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
};
