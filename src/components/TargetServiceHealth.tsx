import React from 'react';
import { useApp } from '../context/AppContext';

export const TargetServiceHealth: React.FC = () => {
  const { services, activeStage } = useApp();

  const allHealthy = services.every((s) => s.status === 'healthy');

  return (
    <div className="bg-surface-container rounded-xl p-space-lg flex flex-col gap-space-md shadow-md border border-outline-variant/30">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-space-xs">
          <span className="material-symbols-outlined text-primary text-[20px]">insights</span>
          <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
            Target Service Health
          </h3>
        </div>
        <span
          className={`w-2 h-2 rounded-full ${
            allHealthy ? 'bg-tertiary animate-pulse' : 'bg-error animate-ping'
          }`}
        ></span>
      </div>

      <div className="flex flex-col gap-space-xs font-code-sm text-code-sm">
        {services.map((svc) => {
          const isHealthy = svc.status === 'healthy';
          const isRecovering = svc.status === 'recovering';
          const isCritical = svc.status === 'critical';

          let statusColor = 'text-tertiary';
          let dotColor = 'bg-tertiary';
          let statusText = `Healthy (${
            svc.name === 'worker' ? `${svc.cpuPercent}% CPU` : `${svc.latencyMs}ms`
          })`;

          if (isCritical) {
            statusColor = 'text-error';
            dotColor = 'bg-error animate-ping';
            statusText = 'CRITICAL (Crash / Timeout)';
          } else if (svc.status === 'degraded') {
            statusColor = 'text-amber-400';
            dotColor = 'bg-amber-400 animate-pulse';
            statusText = `DEGRADED (${svc.cpuPercent}% CPU, ${svc.latencyMs}ms)`;
          } else if (isRecovering) {
            statusColor = 'text-primary';
            dotColor = 'bg-primary animate-spin';
            statusText = 'Recovering (Zero-Touch Fix)';
          }

          return (
            <div
              key={svc.id}
              className={`flex items-center justify-between p-space-sm rounded transition-colors ${
                isCritical
                  ? 'bg-error/10 border border-error/30'
                  : isRecovering
                  ? 'bg-primary/10 border border-primary/30'
                  : 'bg-surface-container-low'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${dotColor}`}></span>
                <span className="text-on-surface">
                  {svc.name} (port {svc.port})
                </span>
              </div>
              <span className={`font-medium ${statusColor}`}>{statusText}</span>
            </div>
          );
        })}
      </div>

      {activeStage !== 'IDLE' && (
        <div className="mt-1 p-2 rounded bg-surface-container-lowest border border-primary/20 text-xs text-primary flex items-center gap-2">
          <span className="material-symbols-outlined text-[16px] animate-spin">autorenew</span>
          <span>Autonomous agent actively observing socket connections</span>
        </div>
      )}
    </div>
  );
};
