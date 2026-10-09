import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import confetti from 'canvas-confetti';
import {
  EmergencyCaseIntake,
  IncidentRecord,
  RoadmapStep,
  ServiceNode,
  TargetEndpointConfig,
} from '../types';
import {
  apiClient,
  CHAOS_SCENARIOS,
  ChaosScenario,
} from '../services/apiClient';
import {
  INITIAL_ENDPOINT_CONFIG,
  INITIAL_INCIDENTS,
  INITIAL_SERVICES,
  ROADMAP_STEPS,
} from '../services/mockData';

export type AppTab = 'incident-report' | 'live-overview';

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
  endpointConfig: TargetEndpointConfig;
  setEndpointConfig: React.Dispatch<React.SetStateAction<TargetEndpointConfig>>;
  services: ServiceNode[];
  setServices: React.Dispatch<React.SetStateAction<ServiceNode[]>>;
  incidents: IncidentRecord[];
  roadmapSteps: RoadmapStep[];
  emergencyCases: EmergencyCaseIntake[];
  isProbing: boolean;
  forceProbe: () => Promise<void>;
  updateTarget: (url: string, interval: '1s' | '2s' | '5s') => void;
  addEndpoint: (name: string, port: number, url: string) => void;
  // Chaos & Demo
  activeStage: SimulationStage;
  activeScenario: ChaosScenario | null;
  stageProgress: number; // 0 to 100
  stageMessage: string;
  triggerChaos: (scenario: ChaosScenario) => void;
  runFullDemo: () => void;
  resetServices: () => void;
  // Modals
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
  // Downloads & Actions
  downloadReport: () => void;
  submitEmergencyCase: (caseData: Omit<EmergencyCaseIntake, 'caseId' | 'timestamp'>) => void;
  // Feedback toast
  toast: { message: string; type: 'success' | 'info' | 'warning' } | null;
  showToast: (message: string, type?: 'success' | 'info' | 'warning') => void;
  // Derived metrics
  totalIncidents: number;
  autoHealedRate: string;
  avgDetection: string;
  avgRecoveryTime: string;
}

const AppContext = createContext<AppContextType | null>(null);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<AppTab>('incident-report');
  const [endpointConfig, setEndpointConfig] = useState<TargetEndpointConfig>(INITIAL_ENDPOINT_CONFIG);
  const [services, setServices] = useState<ServiceNode[]>(INITIAL_SERVICES);
  const [incidents, setIncidents] = useState<IncidentRecord[]>(INITIAL_INCIDENTS);
  const [roadmapSteps] = useState<RoadmapStep[]>(ROADMAP_STEPS);
  const [emergencyCases, setEmergencyCases] = useState<EmergencyCaseIntake[]>([]);
  const [isProbing, setIsProbing] = useState(false);

  // Simulation states
  const [activeStage, setActiveStage] = useState<SimulationStage>('IDLE');
  const [activeScenario, setActiveScenario] = useState<ChaosScenario | null>(null);
  const [stageProgress, setStageProgress] = useState(0);
  const [stageMessage, setStageMessage] = useState('');

  // Modals
  const [isSqliteModalOpen, setIsSqliteModalOpen] = useState(false);
  const [isChangeTargetModalOpen, setIsChangeTargetModalOpen] = useState(false);
  const [isAddEndpointModalOpen, setIsAddEndpointModalOpen] = useState(false);
  const [isEmergencyIntakeModalOpen, setIsEmergencyIntakeModalOpen] = useState(false);
  const [isProfileSettingsModalOpen, setIsProfileSettingsModalOpen] = useState(false);

  // Toast
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' | 'warning' } | null>(null);

  const showToast = useCallback((message: string, type: 'success' | 'info' | 'warning' = 'info') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast((curr) => (curr?.message === message ? null : curr));
    }, 3800);
  }, []);

  // Force probe target
  const forceProbe = useCallback(async () => {
    setIsProbing(true);
    showToast(`Sending HTTP GET health probe to ${endpointConfig.url}...`, 'info');
    try {
      const probeResult = await apiClient.probeEndpoint(endpointConfig.url);
      setEndpointConfig((prev) => ({
        ...prev,
        ...probeResult,
        status: 'Connected & Monitored',
      }));
      showToast(`Health check confirmed: HTTP 200 OK (${probeResult.pingLatencyMs}ms)`, 'success');
    } finally {
      setIsProbing(false);
    }
  }, [endpointConfig.url, showToast]);

  const updateTarget = useCallback(
    (url: string, interval: '1s' | '2s' | '5s') => {
      setEndpointConfig((prev) => ({
        ...prev,
        url: url.trim() || 'https://myapp.internal',
        probeInterval: interval,
        lastCheckedUtc: `just now (${new Date().toISOString().substring(11, 19)} UTC)`,
      }));
      showToast(`Target updated to ${url} (interval: ${interval})`, 'success');
    },
    [showToast]
  );

  const addEndpoint = useCallback(
    (name: string, port: number, url: string) => {
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
      setServices((prev) => [...prev, newNode]);
      showToast(`Endpoint registered: ${newNode.name} on port ${port}`, 'success');
    },
    [showToast]
  );

  // Reset services to healthy
  const resetServices = useCallback(() => {
    setServices((prev) =>
      prev.map((s) => ({
        ...s,
        status: 'healthy',
        latencyMs: s.name === 'web' ? 18 : s.name === 'api' ? 22 : 14,
        cpuPercent: s.name === 'worker' ? 3.1 : s.name === 'api' ? 18.2 : 12.4,
      }))
    );
    setActiveStage('IDLE');
    setActiveScenario(null);
    setStageProgress(0);
    setStageMessage('');
  }, []);

  // Trigger synthetic chaos scenario
  const triggerChaos = useCallback(
    (scenario: ChaosScenario) => {
      if (activeStage !== 'IDLE') return;

      setActiveScenario(scenario);
      setActiveStage('CHAOS_INJECTED');
      setStageProgress(15);
      setStageMessage(`Synthetic chaos executed: ${scenario.command}`);

      // Mark targeted service as degraded/critical
      setServices((prev) =>
        prev.map((s) => {
          if (s.name === scenario.targetService) {
            return {
              ...s,
              status: scenario.failureType === 'CRASH' ? 'critical' : 'degraded',
              latencyMs: scenario.failureType === 'HIGH_LATENCY' ? 5120 : s.latencyMs,
              cpuPercent: scenario.failureType === 'CPU_SPIKE' ? 98.4 : s.cpuPercent,
            };
          }
          return s;
        })
      );

      showToast(`Chaos injected into ${scenario.targetService}:${scenario.targetPort}`, 'warning');

      // Step 2: Detection after 1.2s
      setTimeout(() => {
        setActiveStage('DETECTING');
        setStageProgress(35);
        setStageMessage(
          `Monitor agent detected anomaly on ${scenario.targetService}:${scenario.targetPort} via health probe timeout.`
        );
      }, 1200);

      // Step 3: Claude AI Analysis after 2.4s
      setTimeout(() => {
        setActiveStage('AI_ANALYZING');
        setStageProgress(65);
        setStageMessage(
          `Claude 3.5 Sonnet analyzing telemetry snapshots & generating root cause diagnosis...`
        );
      }, 2400);

      // Step 4: Auto Fixing after 3.8s
      setTimeout(() => {
        setActiveStage('AUTO_FIXING');
        setStageProgress(85);
        setStageMessage(`Auto-fixer executing remediation: ${scenario.fixAction}`);

        setServices((prev) =>
          prev.map((s) => (s.name === scenario.targetService ? { ...s, status: 'recovering' } : s))
        );
      }, 3800);

      // Step 5: Verification & Resolved after 5.0s
      setTimeout(() => {
        setActiveStage('VERIFIED');
        setStageProgress(100);
        setStageMessage(`Health check verified 200 OK. Zero-touch auto-recovery complete!`);

        // Restore service health
        setServices((prev) =>
          prev.map((s) => {
            if (s.name === scenario.targetService) {
              return {
                ...s,
                status: 'healthy',
                latencyMs: s.name === 'web' ? 18 : s.name === 'api' ? 22 : 14,
                cpuPercent: s.name === 'worker' ? 3.1 : s.name === 'api' ? 18.2 : 12.4,
              };
            }
            return s;
          })
        );

        // Add new incident to timeline
        const newIncId = `INC-${105 + (incidents.length - 3)}`;
        const nowTime = new Date().toISOString().substring(11, 19);
        const newIncident: IncidentRecord = {
          id: newIncId,
          title:
            scenario.failureType === 'CRASH'
              ? `Service Crash on ${scenario.targetService}:${scenario.targetPort}`
              : scenario.failureType === 'CPU_SPIKE'
              ? `CPU Spike on ${scenario.targetService}:${scenario.targetPort}`
              : `Slow Response on ${scenario.targetService}:${scenario.targetPort}`,
          service: scenario.targetService,
          port: scenario.targetPort,
          timestamp: `today at ${nowTime} UTC`,
          status: 'Auto-Recovered',
          detectionTimeSec: 2.8,
          fixTimeSec: 1.4,
          evidenceSnapshot:
            scenario.failureType === 'CRASH'
              ? 'psutil PID missing, ECONNREFUSED probe failure.'
              : scenario.failureType === 'CPU_SPIKE'
              ? 'Worker PID thread utilization 98.4% in spinloop.'
              : 'Latency p99 spiked to 5120ms (injected sleep flag).',
          aiDiagnosticTitle: 'Claude LLM Diagnostic & Action',
          aiDiagnosticAction: `Autonomous diagnosis for ${scenario.name}. Executed ${scenario.fixAction}, verified /healthz 200 OK.`,
          logs: [
            {
              timestamp: nowTime,
              level: 'CRIT',
              message: `[monitor.py] Alert on http://127.0.0.1:${scenario.targetPort}/healthz`,
            },
            {
              timestamp: nowTime,
              level: 'AI-EXEC',
              message: `Claude analysis completed. Recommendation: ${scenario.fixAction}`,
            },
            {
              timestamp: nowTime,
              level: 'FIX',
              message: `[fixer.py] Action executed -> Health status verified nominal.`,
            },
          ],
        };

        setIncidents((prev) => [newIncident, ...prev]);

        confetti({
          particleCount: 50,
          spread: 60,
          origin: { y: 0.7 },
          colors: ['#4cd7f6', '#4edea3', '#06b6d4'],
        });

        showToast(`Incident ${newIncId} successfully auto-healed in 1.4s!`, 'success');

        // Reset stage back to IDLE after 4 seconds
        setTimeout(() => {
          setActiveStage('IDLE');
          setActiveScenario(null);
          setStageProgress(0);
          setStageMessage('');
        }, 4000);
      }, 5200);
    },
    [activeStage, incidents.length, showToast]
  );

  // Run full demo walkthrough
  const runFullDemo = useCallback(() => {
    setActiveTab('live-overview');
    showToast('Starting Autonomous OpsPilot Live Demonstration...', 'info');
    // Run crash scenario
    setTimeout(() => {
      triggerChaos(CHAOS_SCENARIOS[0]);
    }, 600);
  }, [showToast, triggerChaos]);

  // Download markdown report
  const downloadReport = useCallback(() => {
    apiClient.downloadReportMarkdown(incidents);
    showToast('OpsPilot-Day5-Demo-Report.md downloaded successfully.', 'success');
  }, [incidents, showToast]);

  // Emergency intake submission
  const submitEmergencyCase = useCallback(
    (caseData: Omit<EmergencyCaseIntake, 'caseId' | 'timestamp'>) => {
      const newCase: EmergencyCaseIntake = {
        ...caseData,
        caseId: `EMG-${Math.floor(1000 + Math.random() * 9000)}`,
        timestamp: new Date().toLocaleTimeString(),
        status: 'Dispatched',
        aiTriageSummary:
          caseData.priority === 'RED'
            ? 'Critical Priority Level 1: Immediate autonomous failover triggered. Emergency team dispatched.'
            : caseData.priority === 'YELLOW'
            ? 'Medium Priority Level 2: Anomaly quarantined. Automated mitigation in progress.'
            : 'Low Priority Level 3: Non-critical telemetry logging and ticket generated.',
      };

      setEmergencyCases((prev) => [newCase, ...prev]);
      showToast(`Emergency case ${newCase.caseId} recorded with Priority ${newCase.priority}!`, 'success');
      setIsEmergencyIntakeModalOpen(false);
    },
    [showToast]
  );

  // Derived KPI metrics
  const totalIncidents = incidents.length;
  const autoHealedRate = '100%';
  const avgDetection = useMemo(() => {
    if (!incidents.length) return '2.8s';
    const sum = incidents.reduce((acc, i) => acc + i.detectionTimeSec, 0);
    return `${(sum / incidents.length).toFixed(1)}s`;
  }, [incidents]);

  const avgRecoveryTime = useMemo(() => {
    if (!incidents.length) return '1.6s';
    const sum = incidents.reduce((acc, i) => acc + i.fixTimeSec, 0);
    return `${(sum / incidents.length).toFixed(1)}s`;
  }, [incidents]);

  return (
    <AppContext.Provider
      value={{
        activeTab,
        setActiveTab,
        endpointConfig,
        setEndpointConfig,
        services,
        setServices,
        incidents,
        roadmapSteps,
        emergencyCases,
        isProbing,
        forceProbe,
        updateTarget,
        addEndpoint,
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
