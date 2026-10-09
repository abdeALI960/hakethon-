import React, { useEffect, useRef, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { apiClient } from '../../services/apiClient';
import type { DatabaseTableInfo } from '../../types';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { sanitizeDisplay } from '../../utils/sanitize';

export const SqliteModal: React.FC = () => {
  const {
    isSqliteModalOpen,
    setIsSqliteModalOpen,
    incidents,
    showToast,
    backendStatus,
  } = useApp();
  const modalRef = useRef<HTMLDivElement>(null);
  const incidentsRef = useRef(incidents);
  incidentsRef.current = incidents;
  useFocusTrap(modalRef, isSqliteModalOpen, () => setIsSqliteModalOpen(false));
  const [activeTab, setActiveTab] = useState<'records' | 'schema'>('records');
  const [searchQuery, setSearchQuery] = useState('');
  const [tables, setTables] = useState<DatabaseTableInfo[]>([]);
  const [selectedTable, setSelectedTable] = useState('incidents');
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [schema, setSchema] = useState('');
  const [exportJson, setExportJson] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isSqliteModalOpen) return;
    let active = true;
    setLoading(true);
    setError(null);
    if (backendStatus === 'connected') {
      void Promise.all([apiClient.dbTables(), apiClient.dbSchema(), apiClient.dbExport()])
        .then(([loadedTables, loadedSchema, loadedExport]) => {
          if (!active) return;
          setTables(loadedTables);
          setSelectedTable((current) =>
            loadedTables.some((table) => table.name === current)
              ? current
              : loadedTables[0]?.name ?? '',
          );
          setSchema(loadedSchema.tables.map((table) => table.createSql).join('\n\n'));
          setExportJson(JSON.stringify(loadedExport, null, 2));
        })
        .catch((reason: unknown) => {
          if (active) setError(reason instanceof Error ? reason.message : 'Unable to load database data.');
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    } else {
      const dump = apiClient.getSqliteDump(incidentsRef.current);
      setTables([{ name: 'incidents', rowCount: dump.rows.length }]);
      setSelectedTable('incidents');
      setRows(dump.rows);
      setSchema(dump.schema);
      setExportJson(JSON.stringify({ incidents: dump.rows }, null, 2));
      setLoading(false);
    }
    return () => {
      active = false;
    };
  }, [backendStatus, isSqliteModalOpen]);

  useEffect(() => {
    if (!isSqliteModalOpen || backendStatus !== 'connected' || !selectedTable) return;
    let active = true;
    setLoading(true);
    void apiClient.dbRows(selectedTable, { limit: 200, offset: 0, q: searchQuery || undefined })
      .then((response) => {
        if (active) setRows(response.rows);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Unable to load table rows.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [backendStatus, isSqliteModalOpen, searchQuery, selectedTable]);

  if (!isSqliteModalOpen) return null;

  const displayedRows = backendStatus === 'connected' || !searchQuery
    ? rows
    : rows.filter((row) =>
        Object.values(row).some((value) =>
          String(value ?? '').toLowerCase().includes(searchQuery.toLowerCase()),
        ),
      );

  const handleCopySql = async () => {
    await navigator.clipboard.writeText(schema);
    showToast('SQLite DDL schema copied to clipboard', 'success');
  };

  const handleExportJson = () => {
    const blob = new Blob([exportJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `opspilot_sqlite_dump_${Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    showToast('Exported read-only SQLite JSON dump', 'success');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div ref={modalRef} role="dialog" aria-modal="true" aria-labelledby="sqlite-modal-title" tabIndex={-1} className="bg-surface-container rounded-xl w-full max-w-4xl border border-outline-variant/50 shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        <div className="flex items-center justify-between p-space-md border-b border-surface-container-high bg-surface-container-low">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[20px]">database</span>
            </div>
            <div>
              <h3 id="sqlite-modal-title" className="font-headline-md text-headline-md text-on-surface font-semibold">
                SQLite Telemetry DataStore Inspector
              </h3>
              <p className="font-code-sm text-code-sm text-outline">
                Read-only database • {tables.reduce((total, table) => total + table.rowCount, 0)} indexed rows
              </p>
            </div>
          </div>
          <button onClick={() => setIsSqliteModalOpen(false)} aria-label="Close database inspector" className="p-1 rounded hover:bg-surface-container-high text-outline hover:text-on-surface cursor-pointer">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <div className="flex items-center justify-between p-space-sm border-b border-surface-container-high bg-surface-container-lowest gap-space-sm flex-wrap">
          <div className="flex items-center gap-1">
            <button onClick={() => setActiveTab('records')} className={`px-3 py-1 rounded text-xs font-medium cursor-pointer ${activeTab === 'records' ? 'bg-surface-container-high text-primary' : 'text-on-surface-variant hover:text-on-surface'}`}>
              Records
            </button>
            <button onClick={() => setActiveTab('schema')} className={`px-3 py-1 rounded text-xs font-medium cursor-pointer ${activeTab === 'schema' ? 'bg-surface-container-high text-primary' : 'text-on-surface-variant hover:text-on-surface'}`}>
              SQL DDL Schema
            </button>
          </div>
          <div className="flex items-center gap-2">
            {activeTab === 'records' && <>
              <select aria-label="Database table" value={selectedTable} onChange={(event) => setSelectedTable(event.target.value)} className="bg-surface-container px-2 py-1 rounded text-xs text-on-surface">
                {tables.map((table) => <option key={table.name} value={table.name}>{table.name} ({table.rowCount})</option>)}
              </select>
              <input type="search" placeholder="Filter rows..." value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} className="bg-surface-container px-2 py-1 rounded text-xs text-on-surface border border-outline-variant/40 w-44" />
            </>}
            <button onClick={() => void handleCopySql()} className="px-2 py-1 rounded bg-surface-container text-xs text-on-surface cursor-pointer">Copy DDL</button>
            <button onClick={handleExportJson} className="px-2 py-1 rounded bg-primary text-on-primary text-xs font-medium cursor-pointer">Export JSON</button>
          </div>
        </div>

        <div className="p-space-md overflow-y-auto flex-1 font-code-sm text-code-sm">
          {loading && <p role="status" className="text-on-surface-variant">Loading database…</p>}
          {error && <p role="alert" className="text-error">{error}</p>}
          {!loading && !error && activeTab === 'records' && (
            displayedRows.length
              ? <div className="overflow-x-auto"><table className="w-full text-left border-collapse"><thead><tr className="border-b border-surface-container-high text-outline text-[11px] uppercase tracking-wider">{Object.keys(displayedRows[0]).map((key) => <th key={key} className="py-2 px-2">{key}</th>)}</tr></thead><tbody className="divide-y divide-surface-container-high/40">{displayedRows.map((row, index) => <tr key={String(row.id ?? index)}>{Object.entries(row).map(([key, value]) => <td key={key} className="py-2 px-2 text-on-surface max-w-xs break-all">{sanitizeDisplay(typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value ?? ''))}</td>)}</tr>)}</tbody></table></div>
              : <p className="text-on-surface-variant">No rows found.</p>
          )}
          {!loading && !error && activeTab === 'schema' && <pre className="overflow-x-auto whitespace-pre text-on-surface">{schema}</pre>}
        </div>
        <div className="p-space-sm border-t border-surface-container-high bg-surface-container-low flex justify-end">
          <button onClick={() => setIsSqliteModalOpen(false)} className="px-3 py-1 rounded bg-surface-container hover:bg-surface-container-high text-on-surface cursor-pointer">Close</button>
        </div>
      </div>
    </div>
  );
};
