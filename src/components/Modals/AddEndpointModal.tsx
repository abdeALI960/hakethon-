import React, { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';

export const AddEndpointModal: React.FC = () => {
  const { isAddEndpointModalOpen, setIsAddEndpointModalOpen, addEndpoint } = useApp();
  const [name, setName] = useState('');
  const [port, setPort] = useState(5004);
  const [url, setUrl] = useState('http://127.0.0.1:5004');

  useEffect(() => {
    if (!isAddEndpointModalOpen) {
      return;
    }

    const sanitizedName = name.trim() || 'service';
    setUrl(`http://127.0.0.1:${port}/${sanitizedName.toLowerCase()}`);
  }, [isAddEndpointModalOpen, name, port]);

  if (!isAddEndpointModalOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    addEndpoint(name.trim(), Number(port), url.trim());
    setIsAddEndpointModalOpen(false);
    setName('');
    setPort(5004);
    setUrl('http://127.0.0.1:5004');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-surface-container rounded-xl w-full max-w-lg border border-outline-variant/50 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between p-space-md border-b border-surface-container-high bg-surface-container-low">
          <div className="flex items-center gap-space-sm">
            <span className="material-symbols-outlined text-primary text-[20px]">add_box</span>
            <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
              Add Monitored Microservice / Endpoint
            </h3>
          </div>
          <button
            onClick={() => setIsAddEndpointModalOpen(false)}
            className="p-1 rounded hover:bg-surface-container-high text-outline hover:text-on-surface cursor-pointer"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-space-lg flex flex-col gap-space-md">
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Service Name / Identifier
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                const nextName = e.target.value.trim() || 'service';
                setUrl(`http://127.0.0.1:${port}/${nextName.toLowerCase()}`);
              }}
              placeholder="e.g. gateway, auth, or hospital-dispatch"
              className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-space-md">
            <div className="flex flex-col gap-1">
              <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
                Local / Internal Port
              </label>
              <input
                type="number"
                value={port}
                onChange={(e) => {
                  const p = Number(e.target.value);
                  setPort(p);
                  setUrl(`http://127.0.0.1:${p}`);
                }}
                className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary"
                required
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
                Health Probe Path
              </label>
              <input
                type="text"
                defaultValue="/healthz"
                className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-label-sm uppercase text-on-surface-variant font-medium">
              Full Probe URL
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="bg-surface-container-lowest px-3 py-2 rounded-lg border border-outline-variant/40 font-code-sm text-code-sm text-on-surface focus:outline-none focus:border-primary"
              required
            />
          </div>

          <div className="flex justify-end gap-space-sm pt-space-sm border-t border-surface-container-high">
            <button
              type="button"
              onClick={() => setIsAddEndpointModalOpen(false)}
              className="px-4 py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-on-surface-variant text-body-md transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-primary text-on-primary font-medium hover:bg-primary-container hover:text-on-primary-container text-body-md transition-colors cursor-pointer"
            >
              Register &amp; Monitor
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
