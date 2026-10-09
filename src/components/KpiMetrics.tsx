import React from 'react';
import { useApp } from '../context/AppContext';

export const KpiMetrics: React.FC = () => {
  const {
    totalIncidents,
    autoHealedRate,
    avgDetection,
    avgRecoveryTime,
    kpis,
    dashboardLoading,
    dashboardError,
  } = useApp();

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-space-md">
      {/* 1. Total Incidents */}
      <div className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between shadow-sm relative overflow-hidden group border border-outline-variant/30">
        <div className="absolute top-0 right-0 w-16 h-16 bg-primary/5 rounded-bl-full pointer-events-none transition-transform group-hover:scale-110"></div>
        <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
          Total Incidents
        </span>
        <div className="flex items-baseline gap-space-xs mt-2">
          <span className="font-headline-xl text-headline-xl font-bold text-on-surface tabular-nums">
            {dashboardLoading
              ? <span aria-hidden="true" className="inline-block h-8 w-12 animate-pulse rounded bg-surface-container-high" />
              : totalIncidents}
          </span>
          <span className="font-code-sm text-code-sm text-tertiary">All Handled</span>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <span className="font-label-sm text-label-sm text-outline">
            {dashboardError ? 'Backend data unavailable' : 'Measured from incident records'}
          </span>
        </div>
      </div>

      {/* 2. Auto-Healed Rate */}
      <div className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between shadow-sm relative overflow-hidden group border border-outline-variant/30">
        <div className="absolute top-0 right-0 w-16 h-16 bg-tertiary/5 rounded-bl-full pointer-events-none transition-transform group-hover:scale-110"></div>
        <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
          Auto-Healed Rate
        </span>
        <div className="flex items-baseline gap-space-xs mt-2">
          <span className="font-headline-xl text-headline-xl font-bold text-tertiary tabular-nums">
            {dashboardLoading
              ? <span aria-hidden="true" className="inline-block h-8 w-16 animate-pulse rounded bg-surface-container-high" />
              : autoHealedRate}
          </span>
          <span className="material-symbols-outlined text-tertiary text-[18px]">verified</span>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <span className="font-label-sm text-label-sm text-tertiary">
            {kpis?.humanEscalations ?? 0} human escalations
          </span>
        </div>
      </div>

      {/* 3. Avg Detection */}
      <div className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between shadow-sm relative overflow-hidden group border border-outline-variant/30">
        <div className="absolute top-0 right-0 w-16 h-16 bg-primary/5 rounded-bl-full pointer-events-none transition-transform group-hover:scale-110"></div>
        <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
          Avg Detection
        </span>
        <div className="flex items-baseline gap-space-xs mt-2">
          <span className="font-headline-xl text-headline-xl font-bold text-primary tabular-nums">
            {dashboardLoading
              ? <span aria-hidden="true" className="inline-block h-8 w-16 animate-pulse rounded bg-surface-container-high" />
              : avgDetection}
          </span>
          <span className="font-code-sm text-code-sm text-outline">
            {kpis?.mttdSeconds.stdDev == null ? '' : `±${kpis.mttdSeconds.stdDev.toFixed(1)}s`}
          </span>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <span className="font-label-sm text-label-sm text-outline">
            {dashboardError ? 'Could not load measured metrics' : 'Measured MTTD'}
          </span>
        </div>
      </div>

      {/* 4. Avg Recovery Time */}
      <div className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between shadow-sm relative overflow-hidden group border border-outline-variant/30">
        <div className="absolute top-0 right-0 w-16 h-16 bg-primary/5 rounded-bl-full pointer-events-none transition-transform group-hover:scale-110"></div>
        <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
          Avg Recovery Time
        </span>
        <div className="flex items-baseline gap-space-xs mt-2">
          <span className="font-headline-xl text-headline-xl font-bold text-on-surface tabular-nums">
            {dashboardLoading
              ? <span aria-hidden="true" className="inline-block h-8 w-16 animate-pulse rounded bg-surface-container-high" />
              : avgRecoveryTime}
          </span>
          <span className="font-code-sm text-code-sm text-tertiary">Measured MTTR</span>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <span className="font-label-sm text-label-sm text-tertiary">
            {totalIncidents ? 'From verified incident timestamps' : 'No verified incidents'}
          </span>
        </div>
      </div>
    </div>
  );
};
