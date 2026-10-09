export type ServiceName = 'web' | 'api' | 'worker' | 'gateway';

export type ServiceStatus = 'healthy' | 'degraded' | 'critical' | 'recovering';

export interface ServiceNode {
  id: string;
  name: string;
  port: number;
  status: ServiceStatus;
  latencyMs: number;
  cpuPercent: number;
  memoryMb: number;
  uptime: string;
  url: string;
}

export type IncidentSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type EmergencyPriority = 'RED' | 'YELLOW' | 'GREEN';

export interface TelemetryLogLine {
  timestamp: string;
  level: 'CRIT' | 'WARN' | 'INFO' | 'AI-EXEC' | 'FIX' | 'OK';
  message: string;
}

export interface IncidentRecord {
  id: string;
  title: string;
  service: string;
  port: number;
  timestamp: string;
  status: 'Auto-Recovered' | 'Investigating' | 'Remediating' | 'Resolved';
  detectionTimeSec: number;
  fixTimeSec: number;
  evidenceSnapshot: string;
  aiDiagnosticTitle: string;
  aiDiagnosticAction: string;
  logs: TelemetryLogLine[];
  priority?: EmergencyPriority;
}

export interface TargetEndpointConfig {
  url: string;
  probeInterval: '1s' | '2s' | '5s';
  status: 'Connected & Monitored' | 'Probing' | 'Disconnected';
  httpStatus: number;
  pingLatencyMs: number;
  sslCertDays: number;
  lastCheckedUtc: string;
  daemonPid: number;
}

export interface RoadmapStep {
  day: number;
  title: string;
  subtitle: string;
  status: 'Done' | 'ACTIVE' | 'Upcoming';
}

export interface EmergencyCaseIntake {
  caseId: string;
  incidentType: string;
  location: string;
  priority: EmergencyPriority;
  callerOrReportedBy: string;
  description: string;
  imageUrl?: string;
  aiTriageSummary?: string;
  status: 'Dispatched' | 'Triage In Progress' | 'Resolved';
  timestamp: string;
}
