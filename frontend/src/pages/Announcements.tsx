import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { Announcement, AnnouncementCategory } from "../types";

const CATEGORIES: { value: AnnouncementCategory; label: string }[] = [
  { value: "general", label: "General" },
  { value: "tefillah_times", label: "Tefillah Times" },
  { value: "emergency", label: "Emergency" },
];

export default function Announcements() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState<AnnouncementCategory>("general");
  const [pinned, setPinned] = useState(false);

  const { data: announcements } = useQuery({
    queryKey: ["announcements"],
    queryFn: () => api.get<Announcement[]>("/announcements"),
  });

  const create = useMutation({
    mutationFn: () => api.post<Announcement>("/announcements", { title, body, category, pinned }),
    onSuccess: () => {
      setTitle("");
      setBody("");
      setPinned(false);
      queryClient.invalidateQueries({ queryKey: ["announcements"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/announcements/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["announcements"] }),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;
    create.mutate();
  }

  const isAvBayit = user?.role === "av_bayit";

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold text-slate-800">Announcements</h1>
      {isAvBayit && (
        <p className="mb-4 text-sm text-slate-500">
          Posts here go to your assigned residents plus everyone sees general house announcements.
        </p>
      )}

      <form onSubmit={handleSubmit} className="mb-6 space-y-2 rounded-lg bg-white p-4 shadow-sm">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Message"
          rows={2}
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <div className="flex flex-wrap items-center gap-3">
          {!isAvBayit && (
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as AnnouncementCategory)}
              className="rounded border border-slate-300 px-2 py-1.5 text-sm"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          )}
          <label className="flex items-center gap-1 text-sm text-slate-600">
            <input type="checkbox" checked={pinned} onChange={(e) => setPinned(e.target.checked)} />
            Pin to top
          </label>
          <button
            type="submit"
            className="ml-auto rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white"
          >
            Post
          </button>
        </div>
      </form>

      <div className="space-y-2">
        {announcements?.map((a) => (
          <div key={a.id} className="flex items-start justify-between rounded-lg bg-white p-4 shadow-sm">
            <div>
              <div className="mb-1 flex items-center gap-2">
                {a.pinned && <span className="text-amber-500">📌</span>}
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] uppercase text-slate-600">
                  {a.category.replace("_", " ")}
                </span>
                {a.audience_av_bayit_id && (
                  <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] text-indigo-600">
                    Group only
                  </span>
                )}
              </div>
              <p className="font-medium text-slate-800">{a.title}</p>
              <p className="text-sm text-slate-600">{a.body}</p>
            </div>
            {(user?.role === "admin" || user?.role === "staff") && (
              <button
                onClick={() => remove.mutate(a.id)}
                className="ml-3 shrink-0 text-xs text-red-600 hover:underline"
              >
                Delete
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
