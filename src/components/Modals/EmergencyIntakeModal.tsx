import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { EmergencyPriority } from '../../types';

export const EmergencyIntakeModal: React.FC = () => {
  const { isEmergencyIntakeModalOpen, setIsEmergencyIntakeModalOpen, submitEmergencyCase } = useApp();

  const [incidentType, setIncidentType] = useState('Critical Server Blackout / Patient Telemetry Loss');
  const [location, setLocation] = useState('Metropolitan Emergency ICU Data Gateway (Rack 04)');
  const [callerOrReportedBy, setCallerOrReportedBy] = useState('On-Call Incident Commander / Dr. Vance');
  const [priority, setPriority] = useState<EmergencyPriority>('RED');
  const [description, setDescription] = useState(
    'Heart rate telemetry stream dropped packets on gateway node. Zero-touch auto-failover requested.'
  );
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  if (!isEmergencyIntakeModalOpen) return null;

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitEmergencyCase({
      incidentType,
      location,
      callerOrReportedBy,
      priority,
      description,
      imageUrl: imagePreview || undefined,
      status: 'Dispatched',
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-surface-container rounded-xl w-full max-w-2xl border border-outline-variant/50 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-space-md border-b border-surface-container-high bg-surface-container-low">
          <div className="flex items-center gap-space-sm">
            <span className="material-symbols-outlined text-error text-[22px]">emergency</span>
            <div>
              <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
                Emergency Case Intake &amp; Triage Form
              </h3>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Human-in-the-loop incident intake with AI decision-support triage
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsEmergencyIntakeModalOpen(false)}
            className="p-1 rounded hover:bg-surface-container-high text-outline hover:text-on-surface cursor-pointer"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-space-lg flex flex-col gap-space-md overflow-y-auto flex-1">
          {/* Priority selector using RED, YELLOW, and GREEN categories */}
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Emergency Priority Category (Triage Level)
            </label>
            <div className="grid grid-cols-3 gap-space-sm">
              <button
                type="button"
                onClick={() => setPriority('RED')}
                className={`flex flex-col items-center justify-center p-space-sm rounded-lg border transition-all cursor-pointer ${
                  priority === 'RED'
                    ? 'bg-error/20 border-error text-error shadow-sm'
                    : 'bg-surface-container-lowest border-outline-variant/30 text-outline hover:border-error/50'
                }`}
              >
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-error animate-ping"></span>
                  <span className="font-bold text-sm">RED</span>
                </div>
                <span className="text-[11px] mt-0.5">Critical Emergency (Immediate Action)</span>
              </button>

              <button
                type="button"
                onClick={() => setPriority('YELLOW')}
                className={`flex flex-col items-center justify-center p-space-sm rounded-lg border transition-all cursor-pointer ${
                  priority === 'YELLOW'
                    ? 'bg-amber-500/20 border-amber-500 text-amber-400 shadow-sm'
                    : 'bg-surface-container-lowest border-outline-variant/30 text-outline hover:border-amber-500/50'
                }`}
              >
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                  <span className="font-bold text-sm">YELLOW</span>
                </div>
                <span className="text-[11px] mt-0.5">Urgent (Degraded / At-Risk)</span>
              </button>

              <button
                type="button"
                onClick={() => setPriority('GREEN')}
                className={`flex flex-col items-center justify-center p-space-sm rounded-lg border transition-all cursor-pointer ${
                  priority === 'GREEN'
                    ? 'bg-tertiary/20 border-tertiary text-tertiary shadow-sm'
                    : 'bg-surface-container-lowest border-outline-variant/30 text-outline hover:border-tertiary/50'
                }`}
              >
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-tertiary"></span>
                  <span className="font-bold text-sm">GREEN</span>
                </div>
                <span className="text-[11px] mt-0.5">Non-Critical (Standard Flow)</span>
              </button>
            </div>
          </div>

          {/* Incident Type & Location */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <div className="flex flex-col gap-1">
              <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
                Incident / Case Type
              </label>
              <input
                type="text"
                value={incidentType}
                onChange={(e) => setIncidentType(e.target.value)}
                className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-body-md text-body-md text-on-surface focus:outline-none focus:border-primary"
                required
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
                Location / Facility / Node
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-body-md text-body-md text-on-surface focus:outline-none focus:border-primary"
                required
              />
            </div>
          </div>

          {/* Caller / Reporter */}
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Reporter / Attending Officer
            </label>
            <input
              type="text"
              value={callerOrReportedBy}
              onChange={(e) => setCallerOrReportedBy(e.target.value)}
              className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-body-md text-body-md text-on-surface focus:outline-none focus:border-primary"
              required
            />
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Incident &amp; Symptoms Description
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-body-md text-body-md text-on-surface focus:outline-none focus:border-primary resize-none"
              required
            />
          </div>

          {/* Image Upload & Preview */}
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Evidence / Incident Photo Attachment
            </label>
            <div className="flex items-center gap-space-md">
              <label className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-on-surface text-xs font-medium border border-outline-variant/40 cursor-pointer transition-colors">
                <span className="material-symbols-outlined text-[16px]">upload_file</span>
                <span>Select Image File</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageChange}
                  className="hidden"
                />
              </label>
              {imagePreview && (
                <button
                  type="button"
                  onClick={() => setImagePreview(null)}
                  className="text-xs text-error hover:underline cursor-pointer"
                >
                  Remove Image
                </button>
              )}
            </div>

            {imagePreview && (
              <div className="mt-2 w-full h-36 rounded-lg overflow-hidden border border-outline-variant/40 relative bg-surface-container-lowest">
                <img
                  src={imagePreview}
                  alt="Incident Preview"
                  className="w-full h-full object-contain"
                />
              </div>
            )}
          </div>

          {/* AI Decision Support Disclaimer */}
          <div className="p-space-sm rounded-lg bg-primary/10 border border-primary/20 text-xs text-primary flex items-start gap-2">
            <span className="material-symbols-outlined text-[16px] shrink-0 mt-0.5">info</span>
            <span>
              <strong>Clinical &amp; System Safety Notice:</strong> AI results provide decision-support telemetry and autonomous routing recommendations, not definitive medical diagnoses. Human confirmation remains active.
            </span>
          </div>

          {/* Modal Footer */}
          <div className="flex justify-end gap-space-sm pt-space-sm border-t border-surface-container-high">
            <button
              type="button"
              onClick={() => setIsEmergencyIntakeModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-on-surface-variant text-body-md transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-primary text-on-primary font-medium hover:bg-primary-container hover:text-on-primary-container text-body-md transition-colors cursor-pointer flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[16px]">send</span>
              <span>Submit &amp; Route Intake</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
