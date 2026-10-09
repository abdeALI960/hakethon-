import React from 'react';
import { useApp } from '../context/AppContext';
import { KpiMetrics } from './KpiMetrics';
import { IncidentTimeline } from './IncidentTimeline';
import { RoadmapCard } from './RoadmapCard';
import { TargetServiceHealth } from './TargetServiceHealth';

export const IncidentHistoryReport: React.FC = () => {
  const { downloadReport, setIsSqliteModalOpen } = useApp();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-start">
      {/* Left Column (8 cols): Incidents, Telemetry, KPI Summary */}
      <div className="lg:col-span-8 flex flex-col gap-space-lg">
        {/* Section Heading & Download / SQLite Actions */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md">
          <div className="flex flex-col">
            <div className="flex items-center gap-space-xs mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
              <span className="font-label-sm text-label-sm uppercase text-primary tracking-wider">
                Automated Remediation Telemetry
              </span>
            </div>
            <h1 className="font-headline-xl text-headline-xl text-on-surface font-semibold tracking-tight">
              Incident History &amp; Demo Post-Mortems
            </h1>
            <p className="font-body-md text-body-md text-on-surface-variant mt-1">
              Autonomous diagnostics and zero-touch healing logs captured during synthetic chaos simulations.
            </p>
          </div>

          <div className="flex items-center gap-space-sm flex-wrap">
            <button
              type="button"
              id="btn-export-md"
              onClick={downloadReport}
              className="flex items-center gap-space-xs px-space-md py-2 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-body-md text-body-md transition-all shadow-sm cursor-pointer border border-outline-variant/30"
            >
              <span className="material-symbols-outlined text-primary text-[18px]">
                markdown
              </span>
              <span>Download Day 5 Demo Report (.md)</span>
            </button>

            <button
              type="button"
              id="btn-sqlite"
              onClick={() => setIsSqliteModalOpen(true)}
              className="flex items-center gap-space-xs px-space-md py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface font-body-md text-body-md transition-all shadow-sm cursor-pointer border border-outline-variant/30"
            >
              <span className="material-symbols-outlined text-[18px]">database</span>
              <span>View SQLite DB</span>
            </button>
          </div>
        </div>

        {/* 4 KPI Metric Cards */}
        <KpiMetrics />

        {/* Incident Timeline */}
        <IncidentTimeline />
      </div>

      {/* Right Column (4 cols): Roadmap & Service Health */}
      <aside className="lg:col-span-4 flex flex-col gap-space-md">
        <RoadmapCard />
        <TargetServiceHealth />
      </aside>
    </div>
  );
};
