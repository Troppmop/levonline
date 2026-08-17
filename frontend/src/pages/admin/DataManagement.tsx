import { useRef, useState, type DragEvent } from "react";
import { ApiError, api } from "../../api/client";

interface RowError {
  row: number;
  column: string | null;
  message: string;
}

interface TableResult {
  inserted_count: number;
  updated_count: number;
  errors: RowError[];
}

interface ImportAllResponse {
  dry_run: boolean;
  tables: Record<string, TableResult>;
}

export default function DataManagement() {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);

  async function exportAll() {
    setExportError(null);
    setExporting(true);
    try {
      await api.download("/admin/export-all", "lev-lachayal-full-export.xlsx");
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div>
      <p className="mb-4 text-sm text-slate-500">
        Export the whole database as one Excel workbook (one tab per table), make your edits, then import
        that same file back to apply the changes.
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <button
          onClick={exportAll}
          disabled={exporting}
          className="rounded-lg bg-slate-800 px-6 py-8 text-lg font-semibold text-white shadow-sm hover:bg-slate-900 disabled:opacity-50"
        >
          ⬇ {exporting ? "Exporting..." : "Export Workbook"}
        </button>
        <button
          onClick={() => setShowImport(true)}
          className="rounded-lg bg-indigo-600 px-6 py-8 text-lg font-semibold text-white shadow-sm hover:bg-indigo-700"
        >
          ⬆ Import Workbook
        </button>
      </div>

      {exportError && <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{exportError}</p>}

      {showImport && <ImportModal onClose={() => setShowImport(false)} />}
    </div>
  );
}

function ImportModal({ onClose }: { onClose: () => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dryRun, setDryRun] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ImportAllResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runImport() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.upload<ImportAllResponse>(
        `/admin/import-all?dry_run=${dryRun}`,
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

  const totalErrors = result
    ? Object.values(result.tables).reduce((sum, t) => sum + t.errors.length, 0)
    : 0;

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-lg bg-white p-5 shadow-lg">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">Import Workbook</h2>
        <p className="mb-3 text-sm text-slate-500">
          Use the file you got from Export Workbook — edit whichever tabs you need, keep the rest as-is, and
          upload the whole thing back. Every tab is applied together: if anything on any tab fails, nothing
          is saved.
        </p>

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="cursor-pointer rounded-lg border-2 border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 hover:border-indigo-400"
        >
          {file ? (
            <span className="font-medium text-slate-700">{file.name}</span>
          ) : (
            <span>Drag & drop the exported .xlsx workbook here, or click to choose it</span>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
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
                totalErrors > 0 ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"
              }`}
            >
              {totalErrors > 0
                ? `${totalErrors} row(s) failed validation across the workbook — nothing was saved.`
                : result.dry_run
                  ? "Dry run passed — nothing was saved yet."
                  : "Import applied successfully."}
            </p>

            <div className="overflow-hidden rounded border border-slate-200 text-xs">
              <table className="w-full text-left">
                <thead className="bg-slate-100 text-slate-500">
                  <tr>
                    <th className="px-2 py-1">Table</th>
                    <th className="px-2 py-1">Inserted</th>
                    <th className="px-2 py-1">Updated</th>
                    <th className="px-2 py-1">Errors</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.tables).map(([table, r]) => (
                    <tr key={table} className="border-t border-slate-100">
                      <td className="px-2 py-1 font-medium">{table}</td>
                      <td className="px-2 py-1">{r.inserted_count}</td>
                      <td className="px-2 py-1">{r.updated_count}</td>
                      <td className="px-2 py-1">{r.errors.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalErrors > 0 && (
              <div className="max-h-48 overflow-y-auto rounded border border-slate-200 text-xs">
                <table className="w-full text-left">
                  <thead className="sticky top-0 bg-slate-100 text-slate-500">
                    <tr>
                      <th className="px-2 py-1">Table</th>
                      <th className="px-2 py-1">Row</th>
                      <th className="px-2 py-1">Column</th>
                      <th className="px-2 py-1">Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(result.tables).flatMap(([table, r]) =>
                      r.errors.map((e, i) => (
                        <tr key={`${table}-${i}`} className="border-t border-slate-100">
                          <td className="px-2 py-1 font-medium">{table}</td>
                          <td className="px-2 py-1">{e.row || "—"}</td>
                          <td className="px-2 py-1">{e.column || "—"}</td>
                          <td className="px-2 py-1">{e.message}</td>
                        </tr>
                      ))
                    )}
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
