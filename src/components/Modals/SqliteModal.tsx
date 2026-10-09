import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { apiClient } from '../../services/apiClient';

export const SqliteModal: React.FC = () => {
  const { isSqliteModalOpen, setIsSqliteModalOpen, incidents, showToast } = useApp();
  const [activeTab, setActiveTab] = useState<'records' | 'schema' | 'query'>('records');
  const [searchQuery, setSearchQuery] = useState('');

  if (!isSqliteModalOpen) return null;

  const dbDump = apiClient.getSqliteDump(incidents);

  const filteredRows = dbDump.rows.filter(
    (row) =>
      row.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      row.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      row.service.toLowerCase().includes(searchQuery.toLowerCase()) ||
      row.evidence.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCopySql = () => {
    navigator.clipboard.writeText(dbDump.schema);
    showToast('SQLite DDL schema copied to clipboard', 'success');
  };

  const handleExportJson = () => {
    const jsonStr = JSON.stringify(dbDump.rows, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `opspilot_sqlite_dump_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Exported incidents as SQLite JSON dump', 'success');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-surface-container rounded-xl w-full max-w-4xl border border-outline-variant/50 shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-space-md border-b border-surface-container-high bg-surface-container-low">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[20px]">database</span>
            </div>
            <div>
              <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
                SQLite Telemetry DataStore Inspector
              </h3>
              <p className="font-code-sm text-code-sm text-outline">
                URI: file://opspilot_telemetry.db • {incidents.length} indexed rows
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsSqliteModalOpen(false)}
            className="p-1 rounded hover:bg-surface-container-high text-outline hover:text-on-surface cursor-pointer"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Tabs & Controls */}
        <div className="flex items-center justify-between p-space-sm border-b border-surface-container-high bg-surface-container-lowest gap-space-sm flex-wrap">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab('records')}
              className={`px-3 py-1 rounded text-xs font-medium cursor-pointer ${
                activeTab === 'records'
                  ? 'bg-surface-container-high text-primary'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Table: incidents ({incidents.length})
            </button>
            <button
              onClick={() => setActiveTab('schema')}
              className={`px-3 py-1 rounded text-xs font-medium cursor-pointer ${
                activeTab === 'schema'
                  ? 'bg-surface-container-high text-primary'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              SQL DDL Schema
            </button>
          </div>

          <div className="flex items-center gap-2">
            {activeTab === 'records' && (
              <input
                type="text"
                placeholder="Filter rows..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-surface-container px-2 py-1 rounded text-xs text-on-surface border border-outline-variant/40 focus:outline-none focus:border-primary placeholder-outline w-44"
              />
            )}
            <button
              onClick={handleCopySql}
              className="px-2 py-1 rounded bg-surface-container hover:bg-surface-container-high text-xs text-on-surface flex items-center gap-1 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[14px]">content_copy</span>
              <span>Copy DDL</span>
            </button>
            <button
              onClick={handleExportJson}
              className="px-2 py-1 rounded bg-primary text-on-primary text-xs font-medium flex items-center gap-1 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[14px]">download</span>
              <span>Export JSON</span>
            </button>
          </div>
        </div>

        {/* Body Content */}
        <div className="p-space-md overflow-y-auto flex-1 font-code-sm text-code-sm">
          {activeTab === 'records' ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-surface-container-high text-outline text-[11px] uppercase tracking-wider">
                    <th className="py-2 px-2">ID</th>
                    <th className="py-2 px-2">Title</th>
                    <th className="py-2 px-2">Target</th>
                    <th className="py-2 px-2">Status</th>
                    <th className="py-2 px-2">MTTD</th>
                    <th className="py-2 px-2">MTTR</th>
                    <th className="py-2 px-2">Evidence Snapshot</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-container-high/40">
                  {filteredRows.map((row) => (
                    <tr key={row.id} className="hover:bg-surface-container-high/40">
                      <td className="py-2 px-2 font-bold text-primary">{row.id}</td>
                      <td className="py-2 px-2 text-on-surface">{row.title}</td>
                      <td className="py-2 px-2 text-outline">
                        {row.service}:{row.port}
                      </td>
                      <td className="py-2 px-2">
                        <span className="px-1.5 py-0.5 rounded bg-tertiary/10 text-tertiary text-[10px]">
                          {row.status}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-primary">{row.detection_sec}s</td>
                      <td className="py-2 px-2 text-tertiary">{row.fix_sec}s</td>
                      <td className="py-2 px-2 text-outline max-w-xs truncate" title={row.evidence}>
                        {row.evidence}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-surface-container-lowest p-space-md rounded-lg border border-outline-variant/30 text-on-surface font-code-sm">
              <pre className="overflow-x-auto whitespace-pre">{dbDump.schema}</pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-space-sm border-t border-surface-container-high bg-surface-container-low flex justify-between items-center text-xs text-outline">
          <span>Engine: SQLite3 In-Memory Virtual Store v3.45.1</span>
          <button
            onClick={() => setIsSqliteModalOpen(false)}
            className="px-3 py-1 rounded bg-surface-container hover:bg-surface-container-high text-on-surface cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
