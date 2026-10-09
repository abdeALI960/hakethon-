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
  status: 'Auto-Recovered' | 'Investigating' | 'Remediating' | 'Resolved' | 'Awaiting Approval' | 'Failed';
  detectionTimeSec: number | null;
  fixTimeSec: number | null;
  evidenceSnapshot: string;
  aiDiagnosticTitle: string;
  aiDiagnosticAction: string;
  logs: TelemetryLogLine[];
  priority?: EmergencyPriority;
  anomalyType?: string;
  severity?: string;
  autoHealed?: boolean;
  stageTimestamps?: {
    injectedAt: string | null;
    detectedAt: string | null;
    diagnosedAt: string | null;
    fixedAt: string | null;
    verifiedAt: string | null;
  };
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
  safetyNotice?: string;
  status: 'Dispatched' | 'Triage In Progress' | 'Resolved';
  timestamp: string;
}

export type ChaosType = 'CRASH' | 'CPU_SPIKE' | 'HIGH_LATENCY' | 'OOM_KILL';
export type RemediationAction = 'restart' | 'kill_spinloop' | 'clear_latency' | 'none';
export type ProbeInterval = '1s' | '2s' | '5s';
export type IncidentAnomalyType = 'CRASH' | 'CPU_SPIKE' | 'LATENCY' | 'OTHER';
export type IncidentStatus =
  | 'injected'
  | 'detected'
  | 'diagnosed'
  | 'fixed'
  | 'verified'
  | 'awaiting_approval'
  | 'failed';
export type BackendIncidentSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Array<{
      field: string;
      message: string;
      type: string;
    }> | null;
  };
}

export interface ProbeResponse {
  httpStatus: number | null;
  pingLatencyMs: number;
  sslCertDays: number | null;
  lastCheckedUtc: string;
}

export interface ChaosInjectionRequest {
  service: 'web' | 'api' | 'worker';
  port: number;
  type: ChaosType;
}

export interface ChaosInjectionResponse {
  status: 'injected';
  command: string;
  targetPid: number | null;
}

export interface RemediationRequest {
  service: 'web' | 'api' | 'worker';
  action: RemediationAction;
}

export interface RemediationResponse {
  status: 'recovered' | 'failed';
  newPid: number | null;
  probeVerified: boolean;
  fixDurationSec: number;
}

export interface EmergencyIntakeRequest {
  incidentType: string;
  location: string;
  priority: EmergencyPriority;
  reportedBy: string;
  description: string;
}

export interface EmergencyIntakeResponse {
  caseId: string;
  status: 'Dispatched';
  aiTriageSummary: string;
  safetyNotice: string;
}

export interface EmergencyEvidenceUploadResponse {
  caseId: string;
  status: 'uploaded';
  contentType: 'image/png' | 'image/jpeg' | 'image/webp';
}

export interface BackendServiceHealth {
  service: string;
  port: number | null;
  status: ServiceStatus;
  latencyMs: number | null;
  lastCheckedUtc: string | null;
}

export interface BackendIncidentLog {
  ts: string;
  level: string;
  message: string;
}

export interface BackendIncident {
  id: string;
  service: string;
  port: number | null;
  anomalyType: IncidentAnomalyType;
  severity: BackendIncidentSeverity;
  autoHealed: boolean;
  status: IncidentStatus;
  injectedAt: string | null;
  detectedAt: string | null;
  diagnosedAt: string | null;
  fixedAt: string | null;
  verifiedAt: string | null;
  detectionDurationSec: number | null;
  fixDurationSec: number | null;
  aiRationale: string | null;
  logs: BackendIncidentLog[];
}

export interface IncidentListResponse {
  incidents: BackendIncident[];
  total: number;
  limit: number;
  offset: number;
}

export interface IncidentQuery {
  limit?: number;
  offset?: number;
  service?: string;
  status?: IncidentStatus;
}

export interface DurationStats {
  avg: number | null;
  stdDev: number | null;
}

export interface KpiResponse {
  totalIncidents: number;
  autoHealedRatePercent: number;
  humanEscalations: number;
  mttdSeconds: DurationStats;
  mttrSeconds: {
    avg: number | null;
  };
}

export interface BackendEndpoint {
  id: number;
  name: string;
  url: string;
  serviceKey: string | null;
  port: number | null;
  probeIntervalSeconds: number;
  enabled: boolean;
  isDemoTarget: boolean;
  createdAt: string;
}

export interface EndpointCreateRequest {
  name: string;
  url: string;
  serviceKey?: string | null;
  port?: number | null;
  probeIntervalSeconds?: number | ProbeInterval;
  enabled?: boolean;
}

export interface EndpointUpdateRequest {
  probeIntervalSeconds?: number | ProbeInterval | null;
  enabled?: boolean | null;
}

export interface EndpointDeleteResponse {
  deleted: boolean;
}

export interface SettingsResponse {
  llmProvider: 'openai' | 'anthropic' | 'gemini';
  p99LatencySlaMs: number;
  webhookUrl: string | null;
  zeroTouchEnabled: boolean;
  operatorName: string;
}

export type SettingsUpdateRequest = Partial<SettingsResponse>;

export interface AnalysisRequest {
  metrics?: Record<string, unknown>;
  logs?: string[];
}

export interface AnalysisResponse {
  summary: string;
  rootCause: string;
  confidence: number | null;
  severity: string;
  recommendedAction: Exclude<RemediationAction, 'none'> | 'none';
  rationale: string;
  evidence: string[];
  llmStatus: string;
  latencyMs: number;
  incidentId: string;
}

export interface DatabaseTableInfo {
  name: string;
  rowCount: number;
}

export interface DatabaseRowsResponse {
  table: string;
  rows: Array<Record<string, unknown>>;
  total: number;
  limit: number;
  offset: number;
  q: string | null;
}

export interface DatabaseSchemaTable {
  name: string;
  createSql: string;
}

export interface DatabaseSchemaResponse {
  tables: DatabaseSchemaTable[];
}

export interface DatabaseExportResponse {
  tables: Record<string, Array<Record<string, unknown>>>;
  rowCount: number;
  rowCap: number;
  truncated: boolean;
}

export interface StreamEvent {
  type: 'stage_changed' | 'log_line' | 'probe_result' | 'incident_created';
  incidentId?: string;
  endpointId?: number;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface EventStreamHandle {
  close: () => void;
}
