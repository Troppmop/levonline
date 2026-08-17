import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { api } from "../../api/client";
import type { DamageReport, ReportCategory, Room } from "../../types";

const STATUS_LABEL: Record<DamageReport["status"], string> = {
  new: "New",
  acknowledged: "Acknowledged",
  in_progress: "In Progress",
  closed: "Closed",
};

export default function ResidentReport() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<ReportCategory>("damage");
  const [roomId, setRoomId] = useState("");

  const { data: rooms } = useQuery({
    queryKey: ["rooms"],
    queryFn: () => api.get<Room[]>("/rooms"),
  });

  const { data: reports } = useQuery({
    queryKey: ["maintenance", "reports", "mine"],
    queryFn: () => api.get<DamageReport[]>("/maintenance/reports"),
  });

  const createReport = useMutation({
    mutationFn: () =>
      api.post<DamageReport>("/maintenance/reports", {
        title,
        description,
        category,
        room_id: roomId || null,
      }),
    onSuccess: () => {
      setTitle("");
      setDescription("");
      queryClient.invalidateQueries({ queryKey: ["maintenance", "reports", "mine"] });
    },
  });

  const uploadPhoto = useMutation({
    mutationFn: ({ reportId, file }: { reportId: string; file: File }) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.upload<DamageReport>(`/maintenance/reports/${reportId}/photos`, formData);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance", "reports", "mine"] }),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    createReport.mutate();
  }

  return (
    <div className="space-y-6 pb-4">
      <h1 className="text-xl font-semibold text-slate-800">Report an Issue</h1>

      <form onSubmit={handleSubmit} className="space-y-3 rounded-xl bg-white p-4 shadow-sm">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setCategory("damage")}
            className={`flex-1 rounded-lg py-2 text-sm font-medium ${
              category === "damage" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            Maintenance / Damage
          </button>
          <button
            type="button"
            onClick={() => setCategory("cleaning")}
            className={`flex-1 rounded-lg py-2 text-sm font-medium ${
              category === "cleaning" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            Cleaning Request
          </button>
        </div>

        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What's the issue?"
          className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm"
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Details (optional)"
          rows={3}
          className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm"
        />
        <select
          value={roomId}
          onChange={(e) => setRoomId(e.target.value)}
          className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm"
        >
          <option value="">Which room? (optional)</option>
          {rooms?.map((r) => (
            <option key={r.id} value={r.id}>
              Floor {r.floor} — Room {r.room_number}
            </option>
          ))}
        </select>

        <button
          type="submit"
          disabled={createReport.isPending}
          className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white active:scale-95 disabled:opacity-50"
        >
          {createReport.isPending ? "Submitting..." : "Submit Report"}
        </button>
      </form>

      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Your Reports
        </h2>
        <div className="space-y-2">
          {reports?.map((r) => (
            <ReportCard
              key={r.id}
              report={r}
              onUploadPhoto={(file) => uploadPhoto.mutate({ reportId: r.id, file })}
            />
          ))}
          {reports?.length === 0 && (
            <p className="rounded-lg bg-white p-4 text-sm text-slate-500 shadow-sm">
              You haven't reported anything yet.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function ReportCard({ report, onUploadPhoto }: { report: DamageReport; onUploadPhoto: (file: File) => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="font-medium text-slate-800">{report.title}</p>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
          {STATUS_LABEL[report.status]}
        </span>
      </div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{report.category}</p>
      {report.description && <p className="text-sm text-slate-600">{report.description}</p>}

      <div className="mt-2 flex flex-wrap items-center gap-2">
        {report.photo_urls.map((url) => (
          <a key={url} href={url} target="_blank" rel="noreferrer">
            <img src={url} alt="Report attachment" className="h-14 w-14 rounded object-cover" />
          </a>
        ))}
        <button
          onClick={() => fileInputRef.current?.click()}
          className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600"
        >
          📷 Add Photo
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUploadPhoto(file);
            e.target.value = "";
          }}
        />
      </div>
    </div>
  );
}
