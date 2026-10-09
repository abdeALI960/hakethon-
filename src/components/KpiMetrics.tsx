import React from 'react';
import { useApp } from '../context/AppContext';

export const KpiMetrics: React.FC = () => {
  const { totalIncidents, autoHealedRate, avgDetection, avgRecoveryTime } = useApp();

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
            {totalIncidents}
          </span>
          <span className="font-code-sm text-code-sm text-tertiary">All Handled</span>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <span className="font-label-sm text-label-sm text-outline">Across 3 Flask services</span>
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
            {autoHealedRate}
          </span>
          <span className="material-symbols-outlined text-tertiary text-[18px]">verified</span>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <span className="font-label-sm text-label-sm text-tertiary">0 human escalations</span>
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
            {avgDetection}
          </span>
          <span className="font-code-sm text-code-sm text-outline">±0.4s</span>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <span className="font-label-sm text-label-sm text-outline">Health probe polling: 1.0s</span>
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
            {avgRecoveryTime}
          </span>
          <span className="font-code-sm text-code-sm text-tertiary">Sub-2s MTTR</span>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <span className="font-label-sm text-label-sm text-tertiary">Fastest: 0.8s (INC-102)</span>
        </div>
      </div>
    </div>
  );
};
