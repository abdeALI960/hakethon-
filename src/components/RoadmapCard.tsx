import React from 'react';
import { useApp } from '../context/AppContext';

export const RoadmapCard: React.FC = () => {
  const { roadmapSteps } = useApp();

  return (
    <div className="bg-surface-container rounded-xl p-space-lg flex flex-col gap-space-md shadow-md border border-outline-variant/30">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-surface-container-high pb-space-sm">
        <div className="flex items-center gap-space-xs">
          <span className="material-symbols-outlined text-tertiary text-[20px]">task_alt</span>
          <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
            5-Day Sprint Roadmap
          </h3>
        </div>
        <span className="font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-tertiary/10 text-tertiary uppercase font-medium">
          Phase 5 Live
        </span>
      </div>

      <p className="font-body-sm text-body-sm text-on-surface-variant">
        Autonomous incident detection and self-healing engineering cycle progress.
      </p>

      {/* Checklist items */}
      <div className="flex flex-col gap-space-sm">
        {roadmapSteps.map((step) => {
          const isDone = step.status === 'Done';
          const isActive = step.status === 'ACTIVE';

          return (
            <div
              key={step.day}
              className={`flex items-center justify-between p-space-sm rounded-lg transition-colors border ${
                isActive
                  ? 'bg-primary/10 border-primary/30'
                  : 'bg-surface-container-low hover:bg-surface-container-high/60 border-outline-variant/40'
              }`}
            >
              <div className="flex items-center gap-space-sm">
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center font-code-sm text-code-sm font-bold ${
                    isDone
                      ? 'bg-tertiary/20 text-tertiary'
                      : isActive
                      ? 'bg-primary/30 text-primary animate-pulse'
                      : 'bg-surface-container-highest text-outline'
                  }`}
                >
                  <span className="material-symbols-outlined text-[14px]">
                    {isDone ? 'check' : isActive ? 'radio_button_checked' : 'hourglass_empty'}
                  </span>
                </span>
                <div className="flex flex-col">
                  <span
                    className={`font-body-md text-body-md font-medium ${
                      isActive ? 'text-primary' : 'text-on-surface'
                    }`}
                  >
                    {step.title}
                  </span>
                  <span
                    className={`font-code-sm text-code-sm ${
                      isActive ? 'text-primary/80' : 'text-outline'
                    }`}
                  >
                    {step.subtitle}
                  </span>
                </div>
              </div>

              <span
                className={`font-label-sm text-label-sm font-semibold px-space-xs py-0.5 rounded ${
                  isDone
                    ? 'text-tertiary bg-surface-container'
                    : isActive
                    ? 'text-primary bg-surface-container-lowest uppercase tracking-wider'
                    : 'text-outline bg-surface-container'
                }`}
              >
                {step.status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
