import { IncidentRecord, RoadmapStep, ServiceNode, TargetEndpointConfig } from '../types';

export const INITIAL_SERVICES: ServiceNode[] = [
  {
    id: 'svc-1',
    name: 'web',
    port: 5001,
    status: 'healthy',
    latencyMs: 18,
    cpuPercent: 12.4,
    memoryMb: 142,
    uptime: '4d 18h',
    url: 'http://127.0.0.1:5001',
  },
  {
    id: 'svc-2',
    name: 'api',
    port: 5002,
    status: 'healthy',
    latencyMs: 22,
    cpuPercent: 18.2,
    memoryMb: 268,
    uptime: '4d 18h',
    url: 'http://127.0.0.1:5002',
  },
  {
    id: 'svc-3',
    name: 'worker',
    port: 5003,
    status: 'healthy',
    latencyMs: 14,
    cpuPercent: 3.1,
    memoryMb: 310,
    uptime: '4d 18h',
    url: 'http://127.0.0.1:5003',
  },
];

export const INITIAL_ENDPOINT_CONFIG: TargetEndpointConfig = {
  url: 'https://myapp.internal',
  probeInterval: '1s',
  status: 'Connected & Monitored',
  httpStatus: 200,
  pingLatencyMs: 18,
  sslCertDays: 242,
  lastCheckedUtc: '3s ago (14:35:02 UTC)',
  daemonPid: 48291,
};

export const INITIAL_INCIDENTS: IncidentRecord[] = [
  {
    id: 'INC-104',
    title: 'Service Crash on api:5002',
    service: 'api',
    port: 5002,
    timestamp: 'today at 14:32:10 UTC',
    status: 'Auto-Recovered',
    detectionTimeSec: 3.0,
    fixTimeSec: 1.4,
    evidenceSnapshot: 'psutil PID missing, 3 consecutive ECONNREFUSED.',
    aiDiagnosticTitle: 'Claude LLM Diagnostic & Action',
    aiDiagnosticAction:
      'Killed via inject.py crash. Claude identified missing process, ran python fixer.py restart api, verified /healthz 200 OK.',
    logs: [
      {
        timestamp: '14:32:07.102',
        level: 'CRIT',
        message:
          '[monitor.py] Healthcheck probe timeout on http://127.0.0.1:5002/healthz (timeout=2.0s)',
      },
      {
        timestamp: '14:32:08.109',
        level: 'CRIT',
        message:
          '[monitor.py] ConnectCallFailed: Errno 111 Connection refused (target_pid=null)',
      },
      {
        timestamp: '14:32:08.520',
        level: 'AI-EXEC',
        message:
          'Claude 3.5 Sonnet payload dispatched. Recommendation: RESTART_PROCESS_API',
      },
      {
        timestamp: '14:32:09.920',
        level: 'FIX',
        message:
          '[fixer.py] Subprocess spawn PID 48291 -> status: alive -> probe verified in 12ms',
      },
    ],
  },
  {
    id: 'INC-103',
    title: 'CPU Spike on worker:5003',
    service: 'worker',
    port: 5003,
    timestamp: 'today at 13:15:42 UTC',
    status: 'Auto-Recovered',
    detectionTimeSec: 2.5,
    fixTimeSec: 1.9,
    evidenceSnapshot: 'Worker PID 41203 thread-id 9 utilization 98.4% (while True loop)',
    aiDiagnosticTitle: 'Claude LLM Diagnostic & Action',
    aiDiagnosticAction:
      'CPU spiked to 98% in busy loop. Claude detected loop-hog thread, instructed fixer.py to terminate offending thread.',
    logs: [
      {
        timestamp: '13:15:39.410',
        level: 'WARN',
        message:
          '[monitor.py] CPU threshold exceeded for worker container: 98.4% > 80.0% limit',
      },
      {
        timestamp: '13:15:40.120',
        level: 'AI-EXEC',
        message:
          'Claude stack trace scan: spinloop detected inside handler /task/compute',
      },
      {
        timestamp: '13:15:42.020',
        level: 'FIX',
        message:
          '[fixer.py] SIGUSR1 thread interrupt sent to TID 9. CPU nominal: 3.1%',
      },
    ],
  },
  {
    id: 'INC-102',
    title: 'Slow Response on web:5001',
    service: 'web',
    port: 5001,
    timestamp: 'today at 11:04:19 UTC',
    status: 'Auto-Recovered',
    detectionTimeSec: 3.2,
    fixTimeSec: 0.8,
    evidenceSnapshot: 'Latency p99 spiked to 5120ms (synthetic delay flag active in memory)',
    aiDiagnosticTitle: 'Claude LLM Diagnostic & Action',
    aiDiagnosticAction:
      'Synthetic 5s sleep caused request timeout. Auto-reset delay flag in web.py gateway.',
    logs: [
      {
        timestamp: '11:04:16.002',
        level: 'WARN',
        message:
          '[monitor.py] P99 Latency warning: /api/v1/checkout took 5012ms (>1500ms SLA)',
      },
      {
        timestamp: '11:04:18.231',
        level: 'AI-EXEC',
        message:
          'Claude identified artificial delay param injected at runtime',
      },
      {
        timestamp: '11:04:19.031',
        level: 'FIX',
        message:
          '[fixer.py] POST http://127.0.0.1:5001/admin/reset-delay -> latency returned to 18ms',
      },
    ],
  },
];

export const ROADMAP_STEPS: RoadmapStep[] = [
  {
    day: 1,
    title: 'Day 1: 3 Flask services',
    subtitle: 'web:5001, api:5002, worker:5003',
    status: 'Done',
  },
  {
    day: 2,
    title: 'Day 2: Monitor agent & inject.py',
    subtitle: 'Chaos injector & health probe telemetry',
    status: 'Done',
  },
  {
    day: 3,
    title: 'Day 3: Auto-fixer',
    subtitle: 'Automated action execution engine',
    status: 'Done',
  },
  {
    day: 4,
    title: 'Day 4: Claude LLM Analyzer',
    subtitle: 'Root cause synthesis & remediation planner',
    status: 'Done',
  },
  {
    day: 5,
    title: 'Day 5: Streamlit demo dashboard',
    subtitle: 'Interactive observability & live triage UI',
    status: 'ACTIVE',
  },
];
