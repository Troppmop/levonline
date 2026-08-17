import { useQuery } from "@tanstack/react-query";
import { useRef, useState, type DragEvent } from "react";
import { ApiError, api } from "../../api/client";

interface TableInfo {
  table_name: string;
  label: string;
}

interface RowError {
  row: number;
  column: string | null;
  message: string;
}

interface ImportResponse {
  inserted_count: number;
  updated_count: number;
  errors: RowError[];
  dry_run: boolean;
}

interface ColumnSchema {
  name: string;
  type: string;
  choices: string[] | null;
  required: boolean;
  writable: boolean;
}

interface TableSchema {
  table_name: string;
  label: string;
  columns: ColumnSchema[];
  allow_create: boolean;
  match_fields: string[];
}

export default function DataManagement() {
  const { data: tables } = useQuery({
    queryKey: ["admin", "data-tables"],
    queryFn: () => api.get<TableInfo[]>("/admin/data-tables"),
  });

  const [importTable, setImportTable] = useState<TableInfo | null>(null);
  const [schemaTable, setSchemaTable] = useState<TableInfo | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  async function exportTable(table: TableInfo) {
    setExportError(null);
    try {
      await api.download(`/admin/export/${table.table_name}?format=xlsx`, `${table.table_name}.xlsx`);
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : "Export failed");
    }
  }

  async function exportAll() {
    setExportError(null);
    try {
      await api.download("/admin/export-all", "lev-lachayal-full-export.xlsx");
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : "Export failed");
    }
  }

  return (
    <div>
      <p className="mb-4 text-sm text-slate-500">
        Bulk export or import every table as an Excel workbook — useful for offline edits, backups, or
        migrating data in from another system.
      </p>

      <button
        onClick={exportAll}
        className="mb-4 rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900"
      >
        Export Complete Database (all tables, one workbook)
      </button>

      {exportError && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{exportError}</p>}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {tables?.map((table) => (
          <div
            key={table.table_name}
            className="flex items-center justify-between rounded-lg bg-white p-4 shadow-sm"
          >
            <span className="text-sm font-medium text-slate-700">{table.label}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setSchemaTable(table)}
                className="rounded bg-slate-100 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-200"
              >
                Schema
              </button>
              <button
                onClick={() => exportTable(table)}
                className="rounded bg-slate-200 px-3 py-1.5 text-xs hover:bg-slate-300"
              >
                Export
              </button>
              <button
                onClick={() => setImportTable(table)}
                className="rounded bg-indigo-100 px-3 py-1.5 text-xs text-indigo-700 hover:bg-indigo-200"
              >
                Import
              </button>
            </div>
          </div>
        ))}
      </div>

      {importTable && <ImportModal table={importTable} onClose={() => setImportTable(null)} />}
      {schemaTable && <SchemaModal table={schemaTable} onClose={() => setSchemaTable(null)} />}
    </div>
  );
}

function SchemaTable({ schema }: { schema: TableSchema }) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500">
        Matches existing rows by <span className="font-medium">{schema.match_fields.join(" + ")}</span>
        {!schema.allow_create && " — this table is update-only; import can't create brand-new rows."}
      </p>
      <div className="max-h-72 overflow-y-auto rounded border border-slate-200 text-xs">
        <table className="w-full text-left">
          <thead className="sticky top-0 bg-slate-100 text-slate-500">
            <tr>
              <th className="px-2 py-1">Column</th>
              <th className="px-2 py-1">Type</th>
              <th className="px-2 py-1">Required</th>
              <th className="px-2 py-1">Notes</th>
            </tr>
          </thead>
          <tbody>
            {schema.columns.map((col) => (
              <tr key={col.name} className="border-t border-slate-100">
                <td className="px-2 py-1 font-mono">{col.name}</td>
                <td className="px-2 py-1">{col.choices ? `one of: ${col.choices.join(", ")}` : col.type}</td>
                <td className="px-2 py-1">{col.writable ? (col.required ? "Yes" : "Optional") : "—"}</td>
                <td className="px-2 py-1 text-slate-400">
                  {!col.writable ? "Read-only, server-managed" : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SchemaModal({ table, onClose }: { table: TableInfo; onClose: () => void }) {
  const { data: schema, isLoading } = useQuery({
    queryKey: ["admin", "schema", table.table_name],
    queryFn: () => api.get<TableSchema>(`/admin/schema/${table.table_name}`),
  });

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-lg">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">{table.label} — Column Reference</h2>
        {isLoading && <p className="text-sm text-slate-500">Loading...</p>}
        {schema && <SchemaTable schema={schema} />}
        <div className="mt-5 flex justify-end">
          <button
            onClick={onClose}
            className="rounded bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function ImportModal({ table, onClose }: { table: TableInfo; onClose: () => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dryRun, setDryRun] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSchema, setShowSchema] = useState(false);

  const { data: schema } = useQuery({
    queryKey: ["admin", "schema", table.table_name],
    queryFn: () => api.get<TableSchema>(`/admin/schema/${table.table_name}`),
    enabled: showSchema,
  });

  async function downloadTemplate() {
    await api.download(
      `/admin/import-template/${table.table_name}`,
      `${table.table_name}-template.xlsx`
    );
  }

  async function runImport() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.upload<ImportResponse>(
        `/admin/import/${table.table_name}?dry_run=${dryRun}`,
        formData
      );
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) {
      setFile(dropped);
      setResult(null);
      setError(null);
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-lg">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Import {table.label}</h2>
          <div className="flex gap-3">
            <button
              onClick={() => setShowSchema((v) => !v)}
              className="text-xs text-indigo-600 hover:underline"
            >
              {showSchema ? "Hide" : "View"} column requirements
            </button>
            <button onClick={downloadTemplate} className="text-xs text-indigo-600 hover:underline">
              Download template
            </button>
          </div>
        </div>

        {showSchema && schema && (
          <div className="mb-3">
            <SchemaTable schema={schema} />
          </div>
        )}

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="cursor-pointer rounded-lg border-2 border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 hover:border-indigo-400"
        >
          {file ? (
            <span className="font-medium text-slate-700">{file.name}</span>
          ) : (
            <span>Drag & drop an .xlsx or .csv file here, or click to choose one</span>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.csv"
            className="hidden"
            onChange={(e) => {
              const selected = e.target.files?.[0];
              if (selected) {
                setFile(selected);
                setResult(null);
                setError(null);
              }
            }}
          />
        </div>

        <label className="mt-3 flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
          Validate only (dry run) — don't save changes yet
        </label>

        {error && <p className="mt-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        {result && (
          <div className="mt-3 space-y-2">
            <p
              className={`rounded px-3 py-2 text-sm ${
                result.errors.length > 0 ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"
              }`}
            >
              {result.dry_run && result.errors.length === 0 && "Dry run passed — nothing was saved yet. "}
              {result.errors.length > 0
                ? `${result.errors.length} row(s) failed validation — nothing was saved.`
                : `Would insert ${result.inserted_count}, update ${result.updated_count}.`}
            </p>
            {result.errors.length > 0 && (
              <div className="max-h-48 overflow-y-auto rounded border border-slate-200 text-xs">
                <table className="w-full text-left">
                  <thead className="bg-slate-100 text-slate-500">
                    <tr>
                      <th className="px-2 py-1">Row</th>
                      <th className="px-2 py-1">Column</th>
                      <th className="px-2 py-1">Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.errors.map((e, i) => (
                      <tr key={i} className="border-t border-slate-100">
                        <td className="px-2 py-1">{e.row || "—"}</td>
                        <td className="px-2 py-1">{e.column || "—"}</td>
                        <td className="px-2 py-1">{e.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200"
          >
            Close
          </button>
          <button
            onClick={runImport}
            disabled={!file || uploading}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {uploading ? "Uploading..." : dryRun ? "Validate" : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
