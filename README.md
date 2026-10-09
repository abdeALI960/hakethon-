# OpsPilot: AI-Powered Autonomous Incident Response & Self-Healing Telemetry

An enterprise-grade, high-density telemetry console and autonomous emergency response application designed for Site Reliability Engineers (SREs), DevOps architects, and critical systems operators. OpsPilot provides real-time health probing, synthetic chaos injection, autonomous LLM root-cause diagnostics, and zero-touch self-healing verification for distributed microservices and endpoints.

---

## 1. Project Title & Overview

**OpsPilot** is an autonomous incident response platform that monitors distributed services (e.g., `web:5001`, `api:5002`, `worker:5003`, and custom target endpoints). When latency spikes, thread spinloops, or process crashes occur, OpsPilot's local daemon detects the anomaly within seconds, synthesizes diagnostic telemetry via LLM reasoning engines (Claude 3.5 Sonnet / Gemini 2.5 Flash), triggers remediation action scripts (`fixer.py`), and verifies health restoration without human on-call escalations.

---

## 2. Problem Statement & Objectives

* **Problem**: Traditional on-call incident response suffers from high Mean Time to Detect (MTTD) and Mean Time to Remediate (MTTR). Alert fatigue leads to delayed escalations, degraded SLOs, and high downtime costs during critical system failures.
* **Objectives**:
  1. Achieve sub-3.0s MTTD and sub-2.0s MTTR across distributed services.
  2. Implement zero-touch automated self-healing for common failure patterns (crashes, CPU spikes, synthetic latency).
  3. Provide an intuitive, dark-mode tactical console replicating real-time post-mortem reports, live microservice topology, and SQLite datastore inspection.
  4. Enable human-in-the-loop Emergency Case Intake with RED, YELLOW, and GREEN triage categorization and AI decision support.

---

## 3. Features Implemented

* **Target Website & Endpoint Manager**:
  * Real-time endpoint URL configuration (`https://myapp.internal` or custom host:port).
  * Configurable probe intervals: Aggressive (1.0s), Standard (2.0s), Background (5.0s).
  * Live status strip: HTTP Probe 200 OK, ping latency (18ms), SSL certificate validity (242d left), and last checked timestamp.
  * Interactive "Force Probe" and "+ Add Endpoint" modal.
* **Incident History & Post-Mortem Feed**:
  * Post-mortem records for `INC-104` (Crash on api:5002), `INC-103` (CPU Spike on worker:5003), and `INC-102` (Latency on web:5001).
  * Real-time addition of auto-healed incidents during live chaos simulation.
  * AI diagnostic rationale and expandable telemetry log details with colored severity levels (`CRIT`, `WARN`, `AI-EXEC`, `FIX`).
* **KPI Telemetry Cards**:
  * Total Incidents counter with dynamic updates.
  * 100% Auto-Healed Rate (0 human escalations).
  * Average Detection Time (MTTD) tabular benchmark (~2.8s ±0.4s).
  * Average Recovery Time (MTTR) benchmark (~1.6s).
* **5-Day Sprint Roadmap**:
  * Phase 5 Live tracker detailing Day 1 through Day 5 deliverables (3 Flask services, Monitor agent, Auto-fixer, Claude LLM Analyzer, Streamlit demo dashboard).
* **Target Service Health Panel**:
  * Live health matrix monitoring `web (5001)`, `api (5002)`, and `worker (5003)`.
* **Live Overview & Chaos Simulation Engine**:
  * Interactive visual node graph representing microservice states (`healthy`, `degraded`, `critical`, `recovering`).
  * Synthetic chaos buttons: Crash Simulation, CPU 98% Spinloop, and 5s Sleep Latency Injection.
  * 5-stage automated healing workflow tracker: Injected $\rightarrow$ Detected $\rightarrow$ AI Diagnosed $\rightarrow$ Auto-Fixed $\rightarrow$ Verified.
  * Real-time terminal log stream from the autonomous daemon.
* **Emergency Case Intake & Triage Modal**:
  * Patient/facility emergency intake form.
  * Triage level selection: **RED** (Critical), **YELLOW** (Urgent), **GREEN** (Standard).
  * Evidence image upload, preview, and removal.
  * AI decision-support triage advice and clinical safety notices.
* **SQLite DataStore Inspector Modal**:
  * In-browser SQLite viewer for `file://opspilot_telemetry.db`.
  * Dynamic filtering, DDL schema viewer, and single-click JSON dump export.
* **Markdown Post-Mortem Export**:
  * Single-click generation and browser download of `OpsPilot-Day5-Demo-Report.md`.
* **Operator Profile & Daemon Settings**:
  * Configurable LLM engine, P99 latency SLA threshold, webhook escalation URLs, and zero-touch mode toggle.

---

## 4. Technology Stack

* **Framework**: React 19 (TypeScript) with functional components and hooks.
* **Build Tool**: Vite 8 with ESNext compilation.
* **Styling**: Tailwind CSS v4 with bespoke Dark Technical Telemetry design tokens (`surface`, `surface-container`, `primary`, `tertiary`, `outline`).
* **Icons**: Google Material Symbols Outlined & Lucide React.
* **Animations & Effects**: Canvas Confetti for successful auto-healing celebrations.
* **Fonts**: `Geist` (Display/Prose) and `JetBrains Mono` (Code & Tabular Telemetry).

---

## 5. Design Assets & References

* **Primary Reference**: User-supplied high-fidelity dark-mode UI design and telemetry tokens (`Image 1.png` and embedded HTML layout).
* **Visual Philosophy**: Tactical SRE dashboard featuring `#0f131c` canvas, `#1c2028` container layering, `#4cd7f6` cyan accents, and `#4edea3` recovery indicators.

---

## 6. Complete Project Folder Structure

```
├── .env.example              # Environment variables template
├── index.html                # Application HTML entry point with Geist & JetBrains fonts
├── metadata.json             # AI Studio applet metadata & capabilities
├── package.json              # Project dependencies and run scripts
├── tsconfig.json             # TypeScript compiler settings
├── vite.config.ts            # Vite bundler configuration
└── src/
    ├── App.tsx               # Root application component
    ├── main.tsx              # React DOM initialization
    ├── index.css             # Tailwind v4 theme tokens and global typography
    ├── types/
    │   └── index.ts          # TypeScript interfaces (Incidents, Services, Endpoints, Triage)
    ├── services/
    │   ├── apiClient.ts      # Centralized API client & chaos scenarios
    │   └── mockData.ts       # Baseline post-mortem logs, services, and roadmap
    ├── context/
    │   └── AppContext.tsx    # Global state, live chaos simulation, and modal orchestration
    └── components/
        ├── Header.tsx                 # Top navigation bar, cluster status, Run Demo button
        ├── EndpointManager.tsx        # Target Website & Endpoint Manager card
        ├── KpiMetrics.tsx             # 4-card telemetry KPI metrics strip
        ├── IncidentTimeline.tsx       # Incident post-mortems with expandable logs
        ├── RoadmapCard.tsx            # 5-Day Sprint Roadmap card
        ├── TargetServiceHealth.tsx    # Live service health indicators
        ├── IncidentHistoryReport.tsx  # Main design report page view
        ├── LiveOverviewDemo.tsx       # Interactive topology & live chaos injection tab
        ├── Footer.tsx                 # Pinned daemon status & latency readout
        ├── Toast.tsx                  # Action feedback toast notification
        └── Modals/
            ├── SqliteModal.tsx            # SQLite database records & DDL inspector
            ├── ChangeTargetModal.tsx      # Target endpoint update modal
            ├── AddEndpointModal.tsx       # Custom service registration modal
            ├── EmergencyIntakeModal.tsx   # RED/YELLOW/GREEN emergency intake form
            └── ProfileSettingsModal.tsx   # Operator profile and daemon configuration
```

---

## 7. Prerequisites & Installation Instructions

### Prerequisites
* Node.js $\ge 18.0.0$
* npm $\ge 9.0.0$

### Installation
```bash
git clone <repository-url>
cd react-example
npm install
```

---

## 8. Running the Development Server

To launch the local development server:
```bash
npm run dev
```
The application will be accessible at `http://localhost:3000`.

---

## 9. Building & Previewing for Production

To create an optimized production build:
```bash
npm run build
```

To preview the production build locally:
```bash
npm run preview
```

---

## 10. Environment Variable Setup

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Available variables:
```env
# GEMINI_API_KEY: Injected by AI Studio for Gemini calls
GEMINI_API_KEY="MY_GEMINI_API_KEY"

# APP_URL: Current hosting origin
APP_URL="http://localhost:3000"

# VITE_API_BASE_URL: Backend REST API server for live daemon integration
VITE_API_BASE_URL="http://localhost:5000"
```

---

## 11. Frontend Architecture & Component Responsibilities

1. **`AppProvider` (`src/context/AppContext.tsx`)**:
   * Single source of truth for target endpoint state, microservice health, incident log history, active simulation state, and modals.
   * Dispatches synthetic chaos actions and increments metrics without page reloads.
2. **`EndpointManager` (`src/components/EndpointManager.tsx`)**:
   * Manages target URL inputs, health check frequency, and immediate force probe executions.
3. **`LiveOverviewDemo` (`src/components/LiveOverviewDemo.tsx`)**:
   * Renders the interactive cluster nodes and real-time execution flow (Anomalies $\rightarrow$ Detection $\rightarrow$ Claude AI Diagnostic $\rightarrow$ Auto-Fixer $\rightarrow$ Recovery).
4. **`IncidentHistoryReport` (`src/components/IncidentHistoryReport.tsx`)**:
   * Houses the exact view from the supplied design mockup, featuring the KPI grid, post-mortem cards, 5-day roadmap, and export triggers.
5. **`EmergencyIntakeModal` (`src/components/Modals/EmergencyIntakeModal.tsx`)**:
   * Facilitates emergency incident intake with RED/YELLOW/GREEN prioritization and file upload preview.

---

## 12. Backend Integration Instructions

To connect OpsPilot to a real Python/Flask daemon:

1. Configure `VITE_API_BASE_URL` in your `.env` file to point to your Flask server (e.g. `http://localhost:5000`).
2. Implement the REST endpoints specified in section 13.
3. Replace the local simulation in `src/services/apiClient.ts` with direct calls to `fetch(`${BASE_URL}/api/...`)`.

---

## 13. API Endpoint & Expected Payload Documentation

### 1. `GET /api/probe?url=<target_url>`
* **Description**: Performs an HTTP health check on the specified target endpoint.
* **Response**:
```json
{
  "httpStatus": 200,
  "pingLatencyMs": 18,
  "sslCertDays": 242,
  "lastCheckedUtc": "2026-10-09T14:35:02Z"
}
```

### 2. `POST /api/chaos/inject`
* **Description**: Executes synthetic chaos injection via `inject.py`.
* **Payload**:
```json
{
  "service": "api",
  "port": 5002,
  "type": "CRASH"
}
```
* **Response**:
```json
{
  "status": "injected",
  "command": "python inject.py crash --target api:5002",
  "targetPid": null
}
```

### 3. `POST /api/remediate`
* **Description**: Executes the remediation script `fixer.py`.
* **Payload**:
```json
{
  "service": "api",
  "action": "restart"
}
```
* **Response**:
```json
{
  "status": "recovered",
  "newPid": 48291,
  "probeVerified": true,
  "fixDurationSec": 1.4
}
```

### 4. `POST /api/emergency/intake`
* **Description**: Submits an emergency case intake for triage.
* **Payload**:
```json
{
  "incidentType": "Cardiac Telemetry Gateway Dropout",
  "location": "ICU Rack 04",
  "priority": "RED",
  "reportedBy": "Lead SRE",
  "description": "Packet loss exceeded 15%"
}
```
* **Response**:
```json
{
  "caseId": "EMG-8192",
  "status": "Dispatched",
  "aiTriageSummary": "Critical Priority Level 1: Immediate failover triggered."
}
```

---

## 14. Mock Data vs. Real API Behavior

* **Default State**: In local development without a backend, OpsPilot operates with full fidelity using simulated daemon telemetry, synthetic latency calculations, and automatic stage transitions.
* **Production API State**: When `VITE_API_BASE_URL` is set, `apiClient.ts` routes requests to the real backend daemon, capturing live `psutil` metrics and process IDs.

---

## 15. Testing & Troubleshooting

* **Build Validation**: Run `npm run build` to verify clean compilation.
* **Type Checking**: Run `npm run lint` (`tsc --noEmit`) to verify zero TypeScript errors.
* **Connection Failures**: If target endpoints return connection errors, ensure the target server is listening on the configured port and permits CORS requests from `http://localhost:3000`.

---

## 16. Security & Data Protection Considerations

* **Telemetry Logs**: Telemetry streams should sanitize authentication tokens, bearer headers, and passwords prior to displaying them in incident post-mortems.
* **Clinical Triage Notice**: For emergency response workflows, AI diagnostics serve exclusively as decision-support information and do not replace professional human evaluation.

---

## 17. Current Limitations & Future Roadmap

* **Air-Gapped Deployment**: Add support for local offline LLM inference via Ollama or llama.cpp for classified operations.
* **Multi-Cluster Orchestration**: Extend cluster monitoring beyond the 3 microservices to multi-region Kubernetes clusters.

---

## 18. Contributing Guidelines

1. Branch from `main` using descriptive naming: `feature/<feature-name>`.
2. Adhere to Tailwind v4 theme variables and JetBrains Mono tabular styling for numerical data.
3. Ensure `npm run lint` and `npm run build` pass before submitting pull requests.
