import React, { useEffect, useRef, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { SettingsResponse } from '../../types';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { apiClient } from '../../services/apiClient';

export const ProfileSettingsModal: React.FC = () => {
  const {
    isProfileSettingsModalOpen,
    setIsProfileSettingsModalOpen,
    endpointConfig,
    runtimeSettings,
    saveSettings,
  } =
    useApp();

  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef, isProfileSettingsModalOpen, () => setIsProfileSettingsModalOpen(false));
  const [operatorName, setOperatorName] = useState('');
  const [llmProvider, setLlmProvider] = useState<SettingsResponse['llmProvider']>('openai');
  const [slaLatencyMs, setSlaLatencyMs] = useState(1500);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [autoHealingEnabled, setAutoHealingEnabled] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [formError, setFormError] = useState('');

  useEffect(() => {
    if (!isProfileSettingsModalOpen) {
      setSettingsLoaded(false);
      return;
    }
    if (!runtimeSettings || settingsLoaded) return;
    setOperatorName(runtimeSettings.operatorName);
    setLlmProvider(runtimeSettings.llmProvider);
    setSlaLatencyMs(runtimeSettings.p99LatencySlaMs);
    setWebhookUrl(runtimeSettings.webhookUrl ?? '');
    setAutoHealingEnabled(runtimeSettings.zeroTouchEnabled);
    setSettingsLoaded(true);
  }, [isProfileSettingsModalOpen, runtimeSettings, settingsLoaded]);

  useEffect(() => {
    if (!isProfileSettingsModalOpen || runtimeSettings) return;
    let active = true;
    void apiClient.getSettings()
      .then((settings) => {
        if (!active) return;
        setOperatorName(settings.operatorName);
        setLlmProvider(settings.llmProvider);
        setSlaLatencyMs(settings.p99LatencySlaMs);
        setWebhookUrl(settings.webhookUrl ?? '');
        setAutoHealingEnabled(settings.zeroTouchEnabled);
        setSettingsLoaded(true);
      })
      .catch((error: unknown) => {
        if (active) setFormError(error instanceof Error ? error.message : 'Unable to load settings.');
      });
    return () => {
      active = false;
    };
  }, [isProfileSettingsModalOpen, runtimeSettings]);

  if (!isProfileSettingsModalOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (webhookUrl.trim()) {
      try {
        const parsed = new URL(webhookUrl.trim());
        if (parsed.protocol !== 'https:') throw new Error();
      } catch {
        setFormError('Webhook URL must be a valid HTTPS URL.');
        return;
      }
    }
    setFormError('');
    setIsSaving(true);
    try {
      await saveSettings({
        operatorName: operatorName.trim(),
        llmProvider,
        p99LatencySlaMs: slaLatencyMs,
        webhookUrl: webhookUrl.trim() || null,
        zeroTouchEnabled: autoHealingEnabled,
      });
      setIsProfileSettingsModalOpen(false);
    } catch {
      // The context surfaces the backend error; keep the form open for correction.
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div ref={modalRef} role="dialog" aria-modal="true" aria-labelledby="profile-settings-title" tabIndex={-1} className="bg-surface-container rounded-xl w-full max-w-xl border border-outline-variant/50 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between p-space-md border-b border-surface-container-high bg-surface-container-low">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary">
              <span className="material-symbols-outlined text-[18px]">person</span>
            </div>
            <div>
              <h3 id="profile-settings-title" className="font-headline-md text-headline-md text-on-surface font-semibold">
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
          {!settingsLoaded && <p role="status" className="text-sm text-on-surface-variant">Loading settings…</p>}
          {formError && <p role="alert" className="text-sm text-error">{formError}</p>}
          {/* Operator Details */}
          <div className="grid grid-cols-1 gap-space-md">
            <div className="flex flex-col gap-1">
              <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
                On-Call Operator
              </label>
              <input
                type="text"
                maxLength={120}
                value={operatorName}
                onChange={(e) => setOperatorName(e.target.value)}
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
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value as SettingsResponse['llmProvider'])}
              className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Gemini</option>
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
                min={1}
                max={120000}
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
                    onChange={(e) => {
                      if (e.target.checked && !autoHealingEnabled &&
                        !window.confirm('Enable zero-touch remediation for registered demo targets?')) return;
                      setAutoHealingEnabled(e.target.checked);
                    }}
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
              maxLength={2048}
              placeholder="https://webhook.example/incident"
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
              disabled={isSaving || !settingsLoaded}
              className="px-4 py-2 rounded-lg bg-primary text-on-primary font-medium hover:bg-primary-container hover:text-on-primary-container text-body-md transition-colors cursor-pointer"
            >
              {isSaving ? 'Saving…' : 'Save Configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
