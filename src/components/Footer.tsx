import React from 'react';
import { useApp } from '../context/AppContext';

export const Footer: React.FC = () => {
  const { endpointConfig } = useApp();

  return (
    <footer className="w-full bg-surface-container-lowest py-space-md shadow-[0_-1px_4px_rgba(0,0,0,0.15)] border-t border-surface-container-high/40">
      <div className="w-full px-margin-desktop flex items-center justify-between text-on-surface-variant font-label-sm text-label-sm">
        <div className="flex items-center gap-2">
          <span>OPSPILOT LOCAL DAEMON • v1.2.4</span>
          <span className="hidden sm:inline text-outline font-normal">
            (pid {endpointConfig.daemonPid} • {endpointConfig.url})
          </span>
        </div>
        <span className="font-code-sm text-code-sm text-outline">
          TELEMETRY LATENCY {endpointConfig.pingLatencyMs}MS
        </span>
      </div>
    </footer>
  );
};
