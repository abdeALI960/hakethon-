import React from 'react';
import { useApp } from '../context/AppContext';

export const Header: React.FC = () => {
  const {
    activeTab,
    setActiveTab,
    endpointConfig,
    setIsChangeTargetModalOpen,
    runFullDemo,
    setIsProfileSettingsModalOpen,
  } = useApp();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#0f131c]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.25)] border-b border-surface-container-high/40">
      <div className="h-16 w-full px-margin-desktop flex items-center justify-between gap-space-lg">
        {/* Left: Brand & Status */}
        <div className="flex items-center gap-space-lg">
          <div
            className="flex items-center gap-space-sm cursor-pointer select-none"
            onClick={() => setActiveTab('incident-report')}
          >
            <div className="w-7 h-7 rounded-lg bg-surface-container-high flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[18px]">terminal</span>
            </div>
            <div className="flex flex-col">
              <span className="font-headline-md text-headline-md text-on-surface font-semibold tracking-tight">
                OpsPilot
              </span>
            </div>
          </div>

          <div className="h-4 w-[1px] bg-surface-container-highest hidden sm:block"></div>

          <div className="flex items-center gap-space-xs bg-surface-container-low px-space-sm py-1 rounded-full border border-outline-variant/30">
            <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
            <span className="font-label-sm text-label-sm text-tertiary uppercase tracking-wider">
              Cluster 3/3 Healthy
            </span>
          </div>
        </div>

        {/* Center: Main Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-space-xs bg-surface-container-lowest p-1 rounded-lg border border-outline-variant/30">
          <button
            type="button"
            onClick={() => setActiveTab('live-overview')}
            className={`px-space-md py-1.5 font-body-md text-body-md transition-all rounded cursor-pointer ${
              activeTab === 'live-overview'
                ? 'bg-surface-container-high text-on-surface font-medium shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
            }`}
          >
            Live Overview &amp; Demo
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('incident-report')}
            className={`px-space-md py-1.5 font-body-md text-body-md transition-all rounded cursor-pointer ${
              activeTab === 'incident-report'
                ? 'bg-surface-container-high text-on-surface font-medium shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
            }`}
          >
            Incident History &amp; AI Report
          </button>
        </nav>

        {/* Right: Target info, Run Demo CTA, and Profile */}
        <div className="flex items-center gap-space-md">
          {/* Target Host Quick Badge */}
          <div className="hidden xl:flex items-center gap-space-xs bg-surface-container-low px-space-sm py-1 rounded-lg border border-outline-variant/40 hover:border-primary/50 transition-colors">
            <span className="material-symbols-outlined text-tertiary text-[16px]">language</span>
            <div className="flex flex-col text-left">
              <div className="flex items-center gap-1">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Target:</span>
                <span className="font-code-sm text-code-sm font-semibold text-primary truncate max-w-[130px]">
                  {endpointConfig.url}
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
              </div>
              <span className="font-label-sm text-label-sm text-outline">
                {endpointConfig.httpStatus} OK • {endpointConfig.pingLatencyMs}ms latency
              </span>
            </div>
            <button
              onClick={() => setIsChangeTargetModalOpen(true)}
              className="ml-1 flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface-container hover:bg-surface-container-high text-on-surface text-label-sm font-label-sm transition-colors cursor-pointer"
              title="Change target website"
            >
              <span className="material-symbols-outlined text-[14px]">swap_horiz</span>
              <span>Change</span>
            </button>
          </div>

          {/* Run Demo Button */}
          <button
            type="button"
            onClick={runFullDemo}
            className="flex items-center gap-space-xs px-space-md py-1.5 rounded-lg bg-primary text-on-primary font-headline-md text-body-md font-medium hover:bg-primary-container hover:text-on-primary-container transition-all shadow-[0_0_12px_-2px_rgba(6,182,212,0.35)] cursor-pointer active:scale-95"
          >
            <span className="material-symbols-outlined text-[16px]">play_arrow</span>
            <span>Run Demo</span>
          </button>

          {/* User Profile Avatar */}
          <button
            type="button"
            onClick={() => setIsProfileSettingsModalOpen(true)}
            className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary hover:opacity-90 transition-opacity cursor-pointer focus:ring-2 focus:ring-primary/50"
            title="User Profile & Daemon Settings"
            aria-label="User Settings"
          >
            <span className="material-symbols-outlined text-[18px]">person</span>
          </button>
        </div>
      </div>

      {/* Mobile Nav strip */}
      <div className="md:hidden flex items-center justify-around border-t border-surface-container-high/40 bg-surface-container-lowest p-1">
        <button
          onClick={() => setActiveTab('live-overview')}
          className={`flex-1 py-1.5 text-center text-xs font-medium rounded ${
            activeTab === 'live-overview'
              ? 'bg-surface-container text-primary font-semibold'
              : 'text-on-surface-variant'
          }`}
        >
          Live Demo
        </button>
        <button
          onClick={() => setActiveTab('incident-report')}
          className={`flex-1 py-1.5 text-center text-xs font-medium rounded ${
            activeTab === 'incident-report'
              ? 'bg-surface-container text-primary font-semibold'
              : 'text-on-surface-variant'
          }`}
        >
          Incidents &amp; AI Report
        </button>
      </div>
    </header>
  );
};
