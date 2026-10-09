import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';

export const ChangeTargetModal: React.FC = () => {
  const {
    isChangeTargetModalOpen,
    setIsChangeTargetModalOpen,
    endpointConfig,
    updateTarget,
    forceProbe,
  } = useApp();

  const [url, setUrl] = useState(endpointConfig.url);
  const [interval, setInterval] = useState(endpointConfig.probeInterval);

  if (!isChangeTargetModalOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateTarget(url, interval);
    forceProbe();
    setIsChangeTargetModalOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-surface-container rounded-xl w-full max-w-lg border border-outline-variant/50 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between p-space-md border-b border-surface-container-high bg-surface-container-low">
          <div className="flex items-center gap-space-sm">
            <span className="material-symbols-outlined text-primary text-[20px]">swap_horiz</span>
            <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
              Change Target Website / Endpoint
            </h3>
          </div>
          <button
            onClick={() => setIsChangeTargetModalOpen(false)}
            className="p-1 rounded hover:bg-surface-container-high text-outline hover:text-on-surface cursor-pointer"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-space-lg flex flex-col gap-space-md">
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Target URL or Microservice Host
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com or http://127.0.0.1:8080"
              className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary"
              required
            />
            <p className="text-xs text-outline">
              Supports external domains, local dev hosts, or staging environments.
            </p>
          </div>

          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Probe Frequency
            </label>
            <select
              value={interval}
              onChange={(e) => setInterval(e.target.value as '1s' | '2s' | '5s')}
              className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value="1s">Every 1.0s (Aggressive / Real-time)</option>
              <option value="2s">Every 2.0s (Standard SLA)</option>
              <option value="5s">Every 5.0s (Background polling)</option>
            </select>
          </div>

          <div className="flex justify-end gap-space-sm pt-space-sm border-t border-surface-container-high">
            <button
              type="button"
              onClick={() => setIsChangeTargetModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-on-surface-variant text-body-md transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-primary text-on-primary font-medium hover:bg-primary-container hover:text-on-primary-container text-body-md transition-colors cursor-pointer"
            >
              Save &amp; Probe Now
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
