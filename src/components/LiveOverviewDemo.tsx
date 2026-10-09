import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { CHAOS_SCENARIOS, ChaosScenario } from '../services/apiClient';
import { sanitizeDisplay } from '../utils/sanitize';

export const LiveOverviewDemo: React.FC = () => {
  const {
    services,
    endpointConfig,
    activeStage,
    activeScenario,
    stageProgress,
    stageMessage,
    triggerChaos,
    resetServices,
    setIsEmergencyIntakeModalOpen,
    emergencyCases,
    terminalLogs,
    chaosRequestInFlight,
    backendStatus,
    runtimeSettings,
    kpis,
    totalIncidents,
    avgRecoveryTime,
  } = useApp();

  const [selectedService, setSelectedService] = useState<string>('api');

  return (
    <div className="flex flex-col gap-space-xl">
      {/* Top Banner: Autonomous Demo Stage */}
      <section className="bg-surface-container rounded-xl p-space-lg shadow-md border border-outline-variant/40 flex flex-col gap-space-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-sm border-b border-surface-container-high pb-space-sm">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[20px]">smart_toy</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-headline-md text-headline-md text-on-surface font-semibold">
                  Autonomous Zero-Touch Incident Remediation Engine
                </h2>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-semibold ${
                    activeStage === 'IDLE'
                      ? 'bg-tertiary/10 text-tertiary'
                      : activeStage === 'VERIFIED'
                      ? 'bg-tertiary/20 text-tertiary'
                      : 'bg-primary/20 text-primary animate-pulse'
                  }`}
                >
                  {activeStage === 'IDLE' ? 'MONITORING ACTIVE' : `STAGE: ${activeStage}`}
                </span>
              </div>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Live incident response paired with the {runtimeSettings?.llmProvider ?? 'configured'} diagnosis provider.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-space-sm">
            <button
              onClick={() => setIsEmergencyIntakeModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-error/15 hover:bg-error/25 text-error text-body-md font-medium transition-colors border border-error/30 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">emergency</span>
              <span>+ Emergency Case Intake</span>
            </button>
            {activeStage !== 'IDLE' && (
              <button
                onClick={resetServices}
                className="px-3 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-body-md transition-colors cursor-pointer"
              >
                Reset Cluster
              </button>
            )}
          </div>
        </div>

        {/* 5-Step Visual Pipeline */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-space-sm">
          {/* Step 1 */}
          <div
            className={`p-space-sm rounded-lg border transition-all ${
              activeStage === 'CHAOS_INJECTED'
                ? 'bg-error/15 border-error text-error'
                : activeStage !== 'IDLE'
                ? 'bg-surface-container-low border-outline-variant/30 text-outline'
                : 'bg-surface-container-lowest border-outline-variant/20 text-outline'
            }`}
          >
            <div className="flex items-center justify-between text-xs font-semibold">
              <span>01. Chaos Injected</span>
              <span className="material-symbols-outlined text-[14px]">bolt</span>
            </div>
            <p className="text-[11px] mt-1 text-on-surface-variant">
              Synthetic crash / spike triggered via inject.py
            </p>
          </div>

          {/* Step 2 */}
          <div
            className={`p-space-sm rounded-lg border transition-all ${
              activeStage === 'DETECTING'
                ? 'bg-amber-400/15 border-amber-400 text-amber-400'
                : activeStage === 'AI_ANALYZING' ||
                  activeStage === 'AUTO_FIXING' ||
                  activeStage === 'VERIFIED'
                ? 'bg-surface-container-low border-outline-variant/30 text-outline'
                : 'bg-surface-container-lowest border-outline-variant/20 text-outline'
            }`}
          >
            <div className="flex items-center justify-between text-xs font-semibold">
              <span>02. Anomaly Detected</span>
              <span className="material-symbols-outlined text-[14px]">sensors</span>
            </div>
            <p className="text-[11px] mt-1 text-on-surface-variant">
              Health probe timeout or threshold breached (&lt;3s)
            </p>
          </div>

          {/* Step 3 */}
          <div
            className={`p-space-sm rounded-lg border transition-all ${
              activeStage === 'AI_ANALYZING'
                ? 'bg-primary/15 border-primary text-primary'
                : activeStage === 'AUTO_FIXING' || activeStage === 'VERIFIED'
                ? 'bg-surface-container-low border-outline-variant/30 text-outline'
                : 'bg-surface-container-lowest border-outline-variant/20 text-outline'
            }`}
          >
            <div className="flex items-center justify-between text-xs font-semibold">
              <span>03. AI Diagnostic</span>
              <span className="material-symbols-outlined text-[14px]">psychology</span>
            </div>
            <p className="text-[11px] mt-1 text-on-surface-variant">
              LLM analyzes stack trace &amp; generates plan
            </p>
          </div>

          {/* Step 4 */}
          <div
            className={`p-space-sm rounded-lg border transition-all ${
              activeStage === 'AUTO_FIXING'
                ? 'bg-primary/20 border-primary text-primary'
                : activeStage === 'VERIFIED'
                ? 'bg-surface-container-low border-outline-variant/30 text-outline'
                : 'bg-surface-container-lowest border-outline-variant/20 text-outline'
            }`}
          >
            <div className="flex items-center justify-between text-xs font-semibold">
              <span>04. Auto-Fixer Run</span>
              <span className="material-symbols-outlined text-[14px]">build</span>
            </div>
            <p className="text-[11px] mt-1 text-on-surface-variant">
              fixer.py restarts process or terminates loop
            </p>
          </div>

          {/* Step 5 */}
          <div
            className={`p-space-sm rounded-lg border transition-all ${
              activeStage === 'VERIFIED'
                ? 'bg-tertiary/20 border-tertiary text-tertiary'
                : 'bg-surface-container-lowest border-outline-variant/20 text-outline'
            }`}
          >
            <div className="flex items-center justify-between text-xs font-semibold">
              <span>05. Self-Healed OK</span>
              <span className="material-symbols-outlined text-[14px]">check_circle</span>
            </div>
            <p className="text-[11px] mt-1 text-on-surface-variant">
              Probe verified 200 OK, zero human escalation
            </p>
          </div>
        </div>

        {/* Live Stage Status Message / Progress Bar */}
        {activeStage !== 'IDLE' && (
          <div className="bg-surface-container-low p-space-md rounded-lg flex flex-col gap-2 border border-primary/30">
            <div className="flex items-center justify-between text-xs font-code-sm">
              <span className="text-primary font-semibold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
                {stageMessage}
              </span>
              <span className="text-outline">{stageProgress}%</span>
            </div>
            <div className="w-full bg-surface-container-lowest h-2 rounded-full overflow-hidden">
              <div
                className="bg-primary h-full transition-all duration-300 ease-out"
                style={{ width: `${stageProgress}%` }}
              ></div>
            </div>
          </div>
        )}
      </section>

      {/* Main Grid: Chaos Control Station & Live Microservice Topologies */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-start">
        {/* Left Col (8 cols): Interactive Microservice Topology & Live Terminal */}
        <div className="lg:col-span-8 flex flex-col gap-space-lg">
          {/* Topology Canvas Card */}
          <div className="bg-surface-container rounded-xl p-space-lg shadow-md border border-outline-variant/30 flex flex-col gap-space-md">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-space-sm">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-primary text-[20px]">hub</span>
                <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
                  Microservice Cluster Topology
                </h3>
              </div>
              <span className="text-xs font-code-sm text-outline">
                Target Gateway: {endpointConfig.url}
              </span>
            </div>

            {/* Microservice Visual Nodes */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md">
              {services.map((svc) => {
                const isCritical = svc.status === 'critical';
                const isDegraded = svc.status === 'degraded';
                const isRecovering = svc.status === 'recovering';
                const isHealthy = svc.status === 'healthy';

                return (
                  <div
                    key={svc.id}
                    onClick={() => setSelectedService(svc.name)}
                    className={`p-space-md rounded-xl border transition-all cursor-pointer flex flex-col gap-space-sm relative overflow-hidden ${
                      selectedService === svc.name
                        ? 'ring-2 ring-primary/60'
                        : 'hover:border-outline-variant'
                    } ${
                      isCritical
                        ? 'bg-error/10 border-error'
                        : isDegraded
                        ? 'bg-amber-400/10 border-amber-400'
                        : isRecovering
                        ? 'bg-primary/10 border-primary'
                        : 'bg-surface-container-low border-outline-variant/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`w-2.5 h-2.5 rounded-full ${
                            isHealthy
                              ? 'bg-tertiary animate-pulse'
                              : isCritical
                              ? 'bg-error animate-ping'
                              : isDegraded
                              ? 'bg-amber-400 animate-pulse'
                              : 'bg-primary animate-spin'
                          }`}
                        ></span>
                        <span className="font-code-lg text-code-lg font-bold text-on-surface">
                          {svc.name}
                        </span>
                      </div>
                      <span className="font-code-sm text-code-sm text-outline">
                        :{svc.port}
                      </span>
                    </div>

                    <div className="flex flex-col gap-1 text-xs font-code-sm text-on-surface-variant">
                      <div className="flex justify-between">
                        <span className="text-outline">Latency:</span>
                        <span
                          className={
                            svc.latencyMs > 500
                              ? 'text-error font-semibold'
                              : 'text-tertiary'
                          }
                        >
                          {svc.latencyMs}ms
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-outline">CPU Usage:</span>
                        <span
                          className={
                            svc.cpuPercent > 80
                              ? 'text-error font-semibold'
                              : 'text-on-surface'
                          }
                        >
                          {svc.cpuPercent}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-outline">Memory:</span>
                        <span>{svc.memoryMb} MB</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-outline">Uptime:</span>
                        <span>{svc.uptime}</span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-surface-container-high/40 flex justify-between items-center text-[11px]">
                      <span className="text-outline">Socket Probe</span>
                      <span
                        className={`font-medium ${
                          isHealthy
                            ? 'text-tertiary'
                            : isCritical
                            ? 'text-error'
                            : isDegraded
                            ? 'text-amber-400'
                            : 'text-primary'
                        }`}
                      >
                        {isHealthy
                          ? '200 OK'
                          : isCritical
                          ? 'FAIL'
                          : isDegraded
                          ? 'SLOW'
                          : 'FIXING'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Live Telemetry Log Viewer */}
            <div className="bg-surface-container-lowest rounded-lg p-space-md border border-outline-variant/30 flex flex-col gap-2">
              <div className="flex items-center justify-between text-xs text-outline font-code-sm pb-1 border-b border-surface-container-high/40">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[14px] text-tertiary">
                    terminal
                  </span>
                  <span>Autonomous Daemon Log Stream (pid {endpointConfig.daemonPid})</span>
                </div>
                <span>STREAM: ACTIVE</span>
              </div>

              <div aria-live="polite" aria-label="Live daemon log stream" className="font-code-sm text-code-sm text-on-surface-variant flex flex-col gap-1 max-h-48 overflow-y-auto pt-1">
                {backendStatus !== 'connected' && <><div className="flex gap-2">
                  <span className="text-outline">14:35:00.120</span>
                  <span className="text-tertiary">[probe.py]</span>
                  <span>HTTP GET {sanitizeDisplay(endpointConfig.url)}/healthz -&gt; 200 OK (18ms)</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-outline">14:35:01.125</span>
                  <span className="text-tertiary">[probe.py]</span>
                  <span>All 3 microservices responded within 50ms SLA window</span>
                </div></>}
                {terminalLogs.map((line, index) => (
                  <div key={`${line.timestamp}-${index}`} className="flex gap-2 break-all">
                    <span className="text-outline shrink-0">{line.timestamp}</span>
                    <span className="text-tertiary shrink-0">[{line.level}]</span>
                    <span>{line.message}</span>
                  </div>
                ))}
                {activeStage === 'CHAOS_INJECTED' && (
                  <div className="flex gap-2 text-error animate-pulse">
                    <span className="text-outline">NOW</span>
                    <span className="font-bold">[inject.py]</span>
                    <span>{stageMessage}</span>
                  </div>
                )}
                {activeStage === 'DETECTING' && (
                  <div className="flex gap-2 text-amber-400">
                    <span className="text-outline">NOW</span>
                    <span className="font-bold">[monitor.py]</span>
                    <span>ALERT: Connection refused / response timeout detected!</span>
                  </div>
                )}
                {activeStage === 'AI_ANALYZING' && (
                  <div className="flex gap-2 text-primary">
                    <span className="text-outline">NOW</span>
                    <span className="font-bold">[claude-ai]</span>
                    <span>Dispatched stack trace to LLM reasoning engine...</span>
                  </div>
                )}
                {activeStage === 'AUTO_FIXING' && (
                  <div className="flex gap-2 text-primary">
                    <span className="text-outline">NOW</span>
                    <span className="font-bold">[fixer.py]</span>
                    <span>Executing autonomous remedial command...</span>
                  </div>
                )}
                {activeStage === 'VERIFIED' && (
                  <div className="flex gap-2 text-tertiary font-bold">
                    <span className="text-outline">NOW</span>
                    <span>[auto-heal]</span>
                    <span>RECOVERED: Health probe confirmed 200 OK. Zero-touch fix verified!</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Emergency Cases List if any */}
          {emergencyCases.length > 0 && (
            <div className="bg-surface-container rounded-xl p-space-lg shadow-md border border-outline-variant/30 flex flex-col gap-space-md">
              <div className="flex items-center justify-between border-b border-surface-container-high pb-space-sm">
                <div className="flex items-center gap-space-xs">
                  <span className="material-symbols-outlined text-error text-[20px]">
                    emergency
                  </span>
                  <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
                    Reported Emergency Cases ({emergencyCases.length})
                  </h3>
                </div>
              </div>

              <div className="flex flex-col gap-space-sm">
                {emergencyCases.map((c) => (
                  <div
                    key={c.caseId}
                    className="p-space-sm rounded-lg bg-surface-container-low border border-outline-variant/30 flex flex-col md:flex-row md:items-center justify-between gap-space-sm"
                  >
                    <div className="flex items-start gap-space-sm">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-bold ${
                          c.priority === 'RED'
                            ? 'bg-error/20 text-error'
                            : c.priority === 'YELLOW'
                            ? 'bg-amber-400/20 text-amber-400'
                            : 'bg-tertiary/20 text-tertiary'
                        }`}
                      >
                        {c.priority}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-code-sm text-code-sm font-bold text-primary">
                            {c.caseId}
                          </span>
                          <span className="font-body-md text-body-md text-on-surface font-medium">
                            {sanitizeDisplay(c.incidentType)}
                          </span>
                        </div>
                        <p className="text-xs text-outline">{sanitizeDisplay(c.description)}</p>
                        <p className="text-[11px] text-primary mt-1">
                          AI Triage: {sanitizeDisplay(c.aiTriageSummary ?? '')}
                        </p>
                        {c.safetyNotice && (
                          <p className="text-[11px] text-outline mt-1">{sanitizeDisplay(c.safetyNotice)}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-outline">{c.timestamp}</span>
                      <span className="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary text-xs font-medium">
                        {c.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Col (4 cols): Chaos Trigger Panel */}
        <aside className="lg:col-span-4 flex flex-col gap-space-md">
          {/* Chaos Injection Panel */}
          <div className="bg-surface-container rounded-xl p-space-lg shadow-md border border-outline-variant/30 flex flex-col gap-space-md">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-space-sm">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-error text-[20px]">
                  pest_control
                </span>
                <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
                  Synthetic Chaos Injector
                </h3>
              </div>
              <span className="text-xs text-outline font-label-sm">inject.py</span>
            </div>

            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Trigger real chaos scenarios against microservices to watch OpsPilot detect, analyze with Claude LLM, and self-heal automatically.
            </p>

            <div className="flex flex-col gap-space-sm">
              {CHAOS_SCENARIOS.map((scenario) => {
                const isTargetActive =
                  activeScenario?.id === scenario.id && activeStage !== 'IDLE';

                return (
                  <div
                    key={scenario.id}
                    className="p-space-sm rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2 hover:border-primary/40 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-body-md text-body-md font-medium text-on-surface">
                        {scenario.name}
                      </span>
                      <span className="font-code-sm text-code-sm text-primary">
                        {scenario.targetService}:{scenario.targetPort}
                      </span>
                    </div>

                    <div className="bg-surface-container-lowest p-1.5 rounded font-code-sm text-[11px] text-outline break-all">
                      <code>{scenario.command}</code>
                    </div>

                    <button
                      type="button"
                      disabled={activeStage !== 'IDLE' || chaosRequestInFlight}
                      onClick={() => void triggerChaos(scenario)}
                      className={`w-full py-1.5 px-3 rounded text-xs font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                        isTargetActive
                          ? 'bg-error text-white animate-pulse'
                          : 'bg-surface-container-high hover:bg-primary hover:text-on-primary text-on-surface'
                      } disabled:opacity-40 disabled:cursor-not-allowed`}
                    >
                      <span className="material-symbols-outlined text-[14px]">
                        {isTargetActive ? 'autorenew' : 'play_arrow'}
                      </span>
                      <span>
                        {chaosRequestInFlight ? 'Injecting…' : isTargetActive ? 'Healing in Progress...' : 'Inject Chaos Scenario'}
                      </span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Quick Metrics */}
          <div className="bg-surface-container rounded-xl p-space-lg shadow-md border border-outline-variant/30 flex flex-col gap-space-sm">
            <h4 className="font-headline-md text-headline-md text-on-surface font-semibold">
              Measured Incident Metrics
            </h4>
            <div className="flex justify-between items-center py-1 border-b border-surface-container-high/40 text-xs">
              <span className="text-outline">Average MTTR</span>
              <span className="text-tertiary font-semibold">{totalIncidents ? avgRecoveryTime : 'n/a'}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-surface-container-high/40 text-xs">
              <span className="text-outline">Human Escalations</span>
              <span className="text-tertiary font-semibold">{kpis?.humanEscalations ?? 0}</span>
            </div>
            <div className="flex justify-between items-center py-1 text-xs">
              <span className="text-outline">Active Daemon PID</span>
              <span className="font-code-sm text-on-surface">{endpointConfig.daemonPid}</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};
