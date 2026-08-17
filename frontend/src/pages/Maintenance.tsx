import { useEffect, useRef, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { DamageReport, MaintenanceStatus } from "../types";

const STATUS_FLOW: MaintenanceStatus[] = ["new", "acknowledged", "in_progress", "closed"];
const STATUS_LABEL: Record<MaintenanceStatus, string> = {
  new: "New",
  acknowledged: "Acknowledged",
  in_progress: "In Progress",
  closed: "Closed",
};

export default function Maintenance() {
  const [reports, setReports] = useState<DamageReport[] | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [locationDetail, setLocationDetail] = useState("");

  async function load() {
    const data = await api.get<DamageReport[]>("/maintenance/reports");
    setReports(data);
  }

  useEffect(() => {
    load();
  }, []);

  async function createReport(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !locationDetail.trim()) return;
    await api.post("/maintenance/reports", { title, description, location_detail: locationDetail });
    setTitle("");
    setDescription("");
    setLocationDetail("");
    load();
  }

  async function advanceStatus(report: DamageReport) {
    const idx = STATUS_FLOW.indexOf(report.status);
    const next = STATUS_FLOW[Math.min(idx + 1, STATUS_FLOW.length - 1)];
    if (next === report.status) return;
    await api.patch(`/maintenance/reports/${report.id}/status`, { status: next });
    load();
  }

  async function uploadPhoto(reportId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    await api.upload(`/maintenance/reports/${reportId}/photos`, formData);
    load();
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold text-slate-800">Maintenance &amp; Damage Reports</h1>

      <form
        onSubmit={createReport}
        className="mb-6 flex flex-col gap-2 rounded-lg bg-white p-4 shadow-sm sm:flex-row"
      >
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Issue title"
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          required
          value={locationDetail}
          onChange={(e) => setLocationDetail(e.target.value)}
          placeholder="Location (e.g. Floor 1 Kitchen, Room 204)"
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description"
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <button type="submit" className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white">
          Report
        </button>
      </form>

      <div className="space-y-3">
        {reports?.map((report) => (
          <ReportCard key={report.id} report={report} onAdvance={advanceStatus} onUploadPhoto={uploadPhoto} />
        ))}
      </div>
      {reports?.length === 0 && <p className="text-slate-500">No damage reports yet.</p>}
    </div>
  );
}

function ReportCard({
  report,
  onAdvance,
  onUploadPhoto,
}: {
  report: DamageReport;
  onAdvance: (report: DamageReport) => void;
  onUploadPhoto: (reportId: string, file: File) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium text-slate-800">{report.title}</p>
          {report.location_detail && (
            <p className="text-xs font-medium text-indigo-600">📍 {report.location_detail}</p>
          )}
          <p className="text-sm text-slate-500">{report.description}</p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              report.status === "closed"
                ? "bg-slate-200 text-slate-600"
                : report.status === "new"
                  ? "bg-red-100 text-red-700"
                  : "bg-amber-100 text-amber-700"
            }`}
          >
            {STATUS_LABEL[report.status]}
          </span>
          {report.status !== "closed" && (
            <button
              onClick={() => onAdvance(report)}
              className="rounded bg-slate-200 px-3 py-1 text-xs hover:bg-slate-300"
            >
              Advance
            </button>
          )}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="rounded bg-slate-200 px-3 py-1 text-xs hover:bg-slate-300"
          >
            Add Photo
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUploadPhoto(report.id, file);
              e.target.value = "";
            }}
          />
        </div>
      </div>
      {report.photo_urls.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {report.photo_urls.map((url) => (
            <a key={url} href={url} target="_blank" rel="noreferrer">
              <img src={url} alt="Damage report" className="h-16 w-16 rounded object-cover" />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
