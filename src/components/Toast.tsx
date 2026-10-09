import React from 'react';
import { useApp } from '../context/AppContext';

export const Toast: React.FC = () => {
  const { toast } = useApp();

  if (!toast) return null;

  return (
    <div className="fixed bottom-12 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-lg bg-surface-container-high border border-outline-variant/60 shadow-xl text-xs font-medium text-on-surface animate-bounce">
      <span
        className={`w-2 h-2 rounded-full ${
          toast.type === 'success'
            ? 'bg-tertiary'
            : toast.type === 'warning'
            ? 'bg-amber-400'
            : 'bg-primary'
        }`}
      ></span>
      <span>{toast.message}</span>
    </div>
  );
};
