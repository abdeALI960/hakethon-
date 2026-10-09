import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { sanitizeDisplay } from '../utils/sanitize';

export const EndpointManager: React.FC = () => {
  const {
    endpointConfig,
    updateTarget,
    forceProbe,
    isProbing,
    setIsAddEndpointModalOpen,
    showToast,
    endpoints,
    deleteEndpoint,
  } = useApp();

  const [inputUrl, setInputUrl] = useState(endpointConfig.url);
  const [selectedInterval, setSelectedInterval] = useState<'1s' | '2s' | '5s'>(
    endpointConfig.probeInterval
  );

  useEffect(() => {
    setInputUrl(endpointConfig.url);
    setSelectedInterval(endpointConfig.probeInterval);
  }, [endpointConfig.url, endpointConfig.probeInterval]);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) {
      showToast('Please enter a valid website URL or host:port endpoint', 'warning');
      return;
    }
    try {
      await updateTarget(inputUrl.trim(), selectedInterval);
      await forceProbe(inputUrl.trim());
    } catch {
      // Context reports the API error and restores the optimistic target.
    }
  };

  const handleClear = () => {
    setInputUrl('');
  };

  return (
    <section className="bg-surface-container rounded-xl p-space-lg flex flex-col gap-space-md shadow-md border border-outline-variant/40">
      {/* Title & Daemon Status Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-sm pb-space-xs border-b border-surface-container-high">
        <div className="flex items-center gap-space-sm">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-[20px]">hub</span>
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-space-xs flex-wrap">
              <h2 className="font-headline-md text-headline-md text-on-surface font-semibold">
                Target Website &amp; Endpoint Manager
              </h2>
              <span className="px-space-xs py-0.5 rounded bg-tertiary/10 text-tertiary font-label-sm text-label-sm font-medium">
                {endpointConfig.status}
              </span>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Configure external URL endpoints or local microservice ports for real-time
              autonomous chaos detection.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-space-xs text-outline font-label-sm text-label-sm">
          <span className="material-symbols-outlined text-[16px] text-tertiary">sync</span>
          <span>Auto-sync enabled (daemon pid {endpointConfig.daemonPid})</span>
        </div>
      </div>

      {/* Target Config Form */}
      <form onSubmit={handleConnect} className="grid grid-cols-1 md:grid-cols-12 gap-space-md items-center">
        {/* Target URL input */}
        <div className="md:col-span-6 flex flex-col gap-1">
          <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
            Target Website URL / Host Endpoint
          </label>
          <div className="flex items-center gap-space-xs bg-surface-container-lowest px-space-md py-2 rounded-lg border border-outline-variant/50 focus-within:border-primary transition-colors">
            <span className="material-symbols-outlined text-outline text-[18px]">link</span>
            <input
              type="text"
              className="bg-transparent font-code-sm text-code-sm text-on-surface w-full focus:outline-none placeholder-outline"
              placeholder="https://myapp.internal (or custom host:port)"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
            />
            {inputUrl && (
              <button
                type="button"
                onClick={handleClear}
                className="text-outline hover:text-on-surface cursor-pointer"
                title="Clear input"
              >
                <span className="material-symbols-outlined text-[16px]">cancel</span>
              </button>
            )}
          </div>
        </div>

        {/* Health probe interval */}
        <div className="md:col-span-3 flex flex-col gap-1">
          <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
            Health Probe Interval
          </label>
          <div className="flex items-center gap-space-xs bg-surface-container-lowest px-space-md py-2 rounded-lg border border-outline-variant/50">
            <span className="material-symbols-outlined text-outline text-[18px]">timer</span>
            <select
              aria-label="Health Probe Interval"
              className="bg-transparent font-code-sm text-code-sm text-on-surface w-full focus:outline-none cursor-pointer"
              value={selectedInterval}
              onChange={(e) => setSelectedInterval(e.target.value as '1s' | '2s' | '5s')}
            >
              <option className="bg-surface-container text-on-surface" value="1s">
                Every 1.0s (Aggressive)
              </option>
              <option className="bg-surface-container text-on-surface" value="2s">
                Every 2.0s (Standard)
              </option>
              <option className="bg-surface-container text-on-surface" value="5s">
                Every 5.0s (Background)
              </option>
            </select>
          </div>
        </div>

        {/* Connect Button */}
        <div className="md:col-span-3 flex flex-col gap-1 justify-end pt-1 md:pt-5">
          <button
            type="submit"
            disabled={isProbing}
            className="flex items-center justify-center gap-space-xs px-space-md py-2 rounded-lg bg-primary text-on-primary font-headline-md text-body-md font-medium hover:bg-primary-container hover:text-on-primary-container transition-all shadow-[0_0_12px_-2px_rgba(6,182,212,0.35)] cursor-pointer disabled:opacity-50"
          >
            <span
              className={`material-symbols-outlined text-[18px] ${
                isProbing ? 'animate-spin' : ''
              }`}
            >
              sensors
            </span>
            <span>{isProbing ? 'Probing...' : 'Connect Target / Probe Website'}</span>
          </button>
        </div>
      </form>

      {/* Active Target Telemetry Bar */}
      {endpoints.length > 0 && (
        <div className="flex flex-col gap-1" aria-label="Registered endpoints">
          {endpoints.map((endpoint) => (
            <div key={endpoint.id} className="flex items-center justify-between rounded bg-surface-container-low px-3 py-2 text-xs">
              <span className="truncate text-on-surface">{endpoint.name} — {endpoint.url}</span>
              <button
                type="button"
                aria-label={`Delete endpoint ${endpoint.name}`}
                onClick={() => void deleteEndpoint(endpoint.id)}
                className="ml-3 text-error hover:underline"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
      <div className="bg-surface-container-low p-space-md rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-space-md border border-outline-variant/20">
        <div className="flex items-center gap-space-md flex-wrap">
          {/* Target string */}
          <div className="flex items-center gap-space-xs">
            <span className="font-label-sm text-label-sm text-outline uppercase">
              Active Target:
            </span>
            <span className="font-code-sm text-code-sm font-bold text-on-surface">
              {sanitizeDisplay(endpointConfig.url)}
            </span>
            <span className="px-1.5 py-0.5 rounded bg-tertiary/10 text-tertiary font-label-sm text-label-sm font-semibold">
              HTTP Probe {endpointConfig.httpStatus} OK
            </span>
          </div>

          <div className="h-3 w-[1px] bg-surface-container-highest hidden md:block"></div>

          {/* Latency */}
          <div className="flex items-center gap-space-xs font-code-sm text-code-sm text-on-surface-variant">
            <span className="text-outline">Ping Latency:</span>
            <span className="text-tertiary font-medium">
              {endpointConfig.pingLatencyMs}ms
            </span>
          </div>

          <div className="h-3 w-[1px] bg-surface-container-highest hidden md:block"></div>

          {/* SSL */}
          <div className="flex items-center gap-space-xs font-code-sm text-code-sm text-on-surface-variant">
            <span className="text-outline">SSL / Cert:</span>
            <span className="text-primary font-medium flex items-center gap-0.5">
              <span className="material-symbols-outlined text-[14px]">lock</span>
              Valid ({endpointConfig.sslCertDays}d left)
            </span>
          </div>

          <div className="h-3 w-[1px] bg-surface-container-highest hidden md:block"></div>

          {/* Last checked */}
          <div className="flex items-center gap-space-xs font-code-sm text-code-sm text-on-surface-variant">
            <span className="text-outline">Last Checked:</span>
            <span className="text-on-surface">{endpointConfig.lastCheckedUtc}</span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-space-xs shrink-0">
          <button
            type="button"
            onClick={() => void forceProbe()}
            disabled={isProbing}
            className="flex items-center gap-1 px-space-sm py-1 rounded bg-surface-container hover:bg-surface-container-high text-on-surface font-label-sm text-label-sm transition-colors cursor-pointer border border-outline-variant/30"
          >
            <span
              className={`material-symbols-outlined text-[14px] ${
                isProbing ? 'animate-spin' : ''
              }`}
            >
              refresh
            </span>
            <span>Force Probe</span>
          </button>

          <button
            type="button"
            onClick={() => setIsAddEndpointModalOpen(true)}
            className="flex items-center gap-1 px-space-sm py-1 rounded bg-surface-container hover:bg-surface-container-high text-on-surface font-label-sm text-label-sm transition-colors cursor-pointer border border-outline-variant/30"
          >
            <span className="material-symbols-outlined text-[14px]">add</span>
            <span>+ Add Endpoint</span>
          </button>
        </div>
      </div>
    </section>
  );
};
