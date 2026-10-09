import React from 'react';
import { useApp } from '../context/AppContext';

export const IncidentTimeline: React.FC = () => {
  const { incidents } = useApp();

  return (
    <section className="flex flex-col gap-space-md">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-space-sm">
          <span className="material-symbols-outlined text-primary text-[20px]">
            history_toggle_off
          </span>
          <h2 className="font-headline-md text-headline-md text-on-surface font-semibold">
            Incident Timeline
          </h2>
          <span className="bg-surface-container-high px-space-xs py-0.5 rounded text-on-surface-variant font-code-sm text-code-sm">
            Showing {incidents.length} recorded
          </span>
        </div>

        <div className="flex items-center gap-space-xs text-on-surface-variant font-label-sm text-label-sm">
          <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
          <span>Live daemon active</span>
        </div>
      </div>

      {/* Incidents List */}
      <div className="flex flex-col gap-space-md">
        {incidents.map((incident) => (
          <div
            key={incident.id}
            className="bg-surface-container rounded-xl p-space-lg flex flex-col gap-space-md shadow-md transition-all hover:bg-surface-container-high/60 border border-outline-variant/30"
          >
            {/* Header row */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-sm pb-space-sm border-b border-surface-container-high/40">
              <div className="flex items-center gap-space-sm flex-wrap">
                <span className="px-space-xs py-0.5 rounded bg-surface-container-lowest font-code-lg text-code-lg font-bold text-primary">
                  {incident.id}
                </span>
                <span className="font-headline-md text-headline-md font-medium text-on-surface">
                  {incident.title}
                </span>
                <span className="font-code-sm text-code-sm text-outline">
                  {incident.timestamp}
                </span>
              </div>

              {/* Badges */}
              <div className="flex items-center gap-space-xs flex-wrap">
                <div className="flex items-center gap-1.5 px-space-sm py-1 rounded bg-tertiary/10 text-tertiary font-label-sm text-label-sm font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
                  <span>{incident.status}</span>
                </div>
                <div className="px-space-sm py-1 rounded bg-surface-container-low text-on-surface-variant font-code-sm text-code-sm">
                  Detection: <span className="text-primary font-medium">{incident.detectionTimeSec}s</span>
                </div>
                <div className="px-space-sm py-1 rounded bg-surface-container-low text-on-surface-variant font-code-sm text-code-sm">
                  Fix: <span className="text-tertiary font-medium">{incident.fixTimeSec}s</span>
                </div>
                <div className="flex items-center gap-1 px-space-sm py-1 rounded bg-surface-container-lowest text-tertiary font-label-sm text-label-sm">
                  <span className="material-symbols-outlined text-[14px]">check_circle</span>
                  <span>Resolved</span>
                </div>
              </div>
            </div>

            {/* AI Diagnostic Box */}
            <div className="bg-surface-container-low p-space-md rounded-lg flex flex-col gap-space-xs border border-outline-variant/20">
              <div className="flex items-center gap-space-xs text-primary font-label-sm text-label-sm">
                <span className="material-symbols-outlined text-[16px]">smart_toy</span>
                <span className="uppercase font-semibold tracking-wider">
                  {incident.aiDiagnosticTitle}
                </span>
              </div>
              <p className="font-body-lg text-body-lg text-on-surface leading-relaxed">
                {incident.aiDiagnosticAction}
              </p>
            </div>

            {/* Expandable Telemetry Logs */}
            <details className="group bg-surface-container-lowest rounded-lg p-space-md border border-outline-variant/20">
              <summary className="flex items-center justify-between cursor-pointer list-none select-none text-on-surface-variant hover:text-on-surface font-label-md text-label-md">
                <div className="flex items-center gap-space-xs flex-wrap">
                  <span className="material-symbols-outlined text-outline text-[16px] group-open:rotate-90 transition-transform">
                    chevron_right
                  </span>
                  <span className="font-code-sm text-code-sm text-outline">
                    Evidence snapshot:
                  </span>
                  <span className="font-code-sm text-code-sm text-error">
                    {incident.evidenceSnapshot}
                  </span>
                </div>
                <span className="font-label-sm text-label-sm text-outline group-open:hidden">
                  Expand Telemetry Logs
                </span>
                <span className="font-label-sm text-label-sm text-outline hidden group-open:inline">
                  Hide Logs
                </span>
              </summary>

              <div className="mt-space-md pt-space-sm flex flex-col gap-1 font-code-sm text-code-sm text-on-surface-variant overflow-x-auto border-t border-surface-container-high/40">
                {incident.logs.map((log, index) => (
                  <div key={index} className="flex gap-space-sm py-0.5 items-start">
                    <span className="text-outline shrink-0 tabular-nums">{log.timestamp}</span>
                    <span
                      className={`font-semibold shrink-0 px-1 rounded text-[10px] ${
                        log.level === 'CRIT'
                          ? 'text-error bg-error/10'
                          : log.level === 'WARN'
                          ? 'text-amber-400 bg-amber-400/10'
                          : log.level === 'AI-EXEC'
                          ? 'text-primary bg-primary/10'
                          : 'text-tertiary bg-tertiary/10'
                      }`}
                    >
                      {log.level}
                    </span>
                    <span className="break-all">{log.message}</span>
                  </div>
                ))}
              </div>
            </details>
          </div>
        ))}
      </div>
    </section>
  );
};
