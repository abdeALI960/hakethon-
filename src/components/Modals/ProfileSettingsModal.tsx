import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';

export const ProfileSettingsModal: React.FC = () => {
  const { isProfileSettingsModalOpen, setIsProfileSettingsModalOpen, endpointConfig, showToast } =
    useApp();

  const [operatorName, setOperatorName] = useState('Alex Rivera (Lead Site Reliability Engineer)');
  const [operatorEmail, setOperatorEmail] = useState('aadarshthakur2140@gmail.com');
  const [llmEngine, setLlmEngine] = useState('Claude 3.5 Sonnet (Autonomous Fixer Mode)');
  const [slaLatencyMs, setSlaLatencyMs] = useState(1500);
  const [webhookUrl, setWebhookUrl] = useState('https://hooks.slack.com/services/T00/B00/emergency-alerts');
  const [autoHealingEnabled, setAutoHealingEnabled] = useState(true);

  if (!isProfileSettingsModalOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    showToast('Telemetry and Daemon settings updated successfully.', 'success');
    setIsProfileSettingsModalOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-surface-container rounded-xl w-full max-w-xl border border-outline-variant/50 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between p-space-md border-b border-surface-container-high bg-surface-container-low">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary">
              <span className="material-symbols-outlined text-[18px]">person</span>
            </div>
            <div>
              <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
                Operator Profile &amp; Daemon Settings
              </h3>
              <p className="font-code-sm text-code-sm text-outline">
                OpsPilot Local Daemon v1.2.4 • PID {endpointConfig.daemonPid}
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsProfileSettingsModalOpen(false)}
            className="p-1 rounded hover:bg-surface-container-high text-outline hover:text-on-surface cursor-pointer"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <form onSubmit={handleSave} className="p-space-lg flex flex-col gap-space-md overflow-y-auto flex-1">
          {/* Operator Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <div className="flex flex-col gap-1">
              <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
                On-Call Operator
              </label>
              <input
                type="text"
                value={operatorName}
                onChange={(e) => setOperatorName(e.target.value)}
                className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-body-md text-body-md text-on-surface focus:outline-none focus:border-primary"
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
                Notification Email
              </label>
              <input
                type="email"
                value={operatorEmail}
                onChange={(e) => setOperatorEmail(e.target.value)}
                className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-body-md text-body-md text-on-surface focus:outline-none focus:border-primary"
                required
              />
            </div>
          </div>

          {/* AI Reasoning Engine */}
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Autonomous Diagnostic LLM Engine
            </label>
            <select
              value={llmEngine}
              onChange={(e) => setLlmEngine(e.target.value)}
              className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value="Claude 3.5 Sonnet (Autonomous Fixer Mode)">
                Claude 3.5 Sonnet (Autonomous Fixer Mode)
              </option>
              <option value="Gemini 2.5 Flash (Ultra-Low Latency Triage)">
                Gemini 2.5 Flash (Ultra-Low Latency Triage)
              </option>
              <option value="Local llama.cpp Daemon (Air-Gapped Node)">
                Local llama.cpp Daemon (Air-Gapped Node)
              </option>
            </select>
          </div>

          {/* SLA Threshold & Webhook */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <div className="flex flex-col gap-1">
              <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
                P99 Latency SLA (ms)
              </label>
              <input
                type="number"
                value={slaLatencyMs}
                onChange={(e) => setSlaLatencyMs(Number(e.target.value))}
                className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
                Auto-Healing Zero-Touch Mode
              </label>
              <div className="flex items-center h-full pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={autoHealingEnabled}
                    onChange={(e) => setAutoHealingEnabled(e.target.checked)}
                    className="w-4 h-4 rounded text-primary focus:ring-primary cursor-pointer"
                  />
                  <span className="text-body-md text-on-surface">
                    {autoHealingEnabled ? 'Enabled (Auto-execute fixer.py)' : 'Manual Approval Required'}
                  </span>
                </label>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Emergency Escalation Webhook
            </label>
            <input
              type="text"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary"
            />
          </div>

          <div className="flex justify-end gap-space-sm pt-space-sm border-t border-surface-container-high">
            <button
              type="button"
              onClick={() => setIsProfileSettingsModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-on-surface-variant text-body-md transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-primary text-on-primary font-medium hover:bg-primary-container hover:text-on-primary-container text-body-md transition-colors cursor-pointer"
            >
              Save Configuration
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
