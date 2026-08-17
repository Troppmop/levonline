import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { DamageReport, MaintenanceStatus } from "../types";

const STATUS_FLOW: MaintenanceStatus[] = ["new", "acknowledged", "in_progress", "closed"];
const STATUS_LABEL: Record<MaintenanceStatus, string> = {
  new: "New",
  acknowledged: "Acknowledged",
  in_progress: "In Progress",
  closed: "Closed",
};

export const REPORT_LOCATIONS = [
  "Floor 1 Kitchen",
  "Floor 2 Kitchen",
  "Floor 3 Kitchen",
  "Basement",
  "Common Area",
  "Stairwell / Hallway",
  "Bathroom",
  "Laundry Room",
  "Kiddush Supply Room",
  "Other",
];

export default function Maintenance() {
  const queryClient = useQueryClient();
  const { data: reports } = useQuery({
    queryKey: ["maintenance", "reports"],
    queryFn: () => api.get<DamageReport[]>("/maintenance/reports"),
  });

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [locationDetail, setLocationDetail] = useState("");
  const [customLocation, setCustomLocation] = useState("");

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["maintenance", "reports"] });
  }

  const createReport = useMutation({
    mutationFn: () =>
      api.post("/maintenance/reports", {
        title,
        description,
        location_detail: locationDetail === "Other" ? customLocation : locationDetail,
      }),
    onSuccess: () => {
      setTitle("");
      setDescription("");
      setLocationDetail("");
      setCustomLocation("");
      invalidate();
    },
  });

  const advanceStatus = useMutation({
    mutationFn: (report: DamageReport) => {
      const idx = STATUS_FLOW.indexOf(report.status);
      const next = STATUS_FLOW[Math.min(idx + 1, STATUS_FLOW.length - 1)];
      return api.patch(`/maintenance/reports/${report.id}/status`, { status: next });
    },
    onSuccess: invalidate,
  });

  const uploadPhoto = useMutation({
    mutationFn: ({ reportId, file }: { reportId: string; file: File }) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.upload(`/maintenance/reports/${reportId}/photos`, formData);
    },
    onSuccess: invalidate,
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const effectiveLocation = locationDetail === "Other" ? customLocation : locationDetail;
    if (!title.trim() || !effectiveLocation.trim()) return;
    createReport.mutate();
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold text-slate-800">Maintenance &amp; Damage Reports</h1>

      <form
        onSubmit={handleSubmit}
        className="mb-6 flex flex-col gap-2 rounded-lg bg-white p-4 shadow-sm sm:flex-row sm:flex-wrap"
      >
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Issue title"
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          required
          value={locationDetail}
          onChange={(e) => setLocationDetail(e.target.value)}
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Select location...</option>
          {REPORT_LOCATIONS.map((loc) => (
            <option key={loc} value={loc}>
              {loc}
            </option>
          ))}
        </select>
        {locationDetail === "Other" && (
          <input
            required
            value={customLocation}
            onChange={(e) => setCustomLocation(e.target.value)}
            placeholder="Describe the location"
            className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
          />
        )}
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
          <ReportCard
            key={report.id}
            report={report}
            onAdvance={() => advanceStatus.mutate(report)}
            onUploadPhoto={(file) => uploadPhoto.mutate({ reportId: report.id, file })}
          />
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
  onAdvance: () => void;
  onUploadPhoto: (file: File) => void;
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
            <button onClick={onAdvance} className="rounded bg-slate-200 px-3 py-1 text-xs hover:bg-slate-300">
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
              if (file) onUploadPhoto(file);
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
