import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import type { Announcement, Resident, ResidentStatus } from "../../types";

const CATEGORY_LABEL: Record<Announcement["category"], string> = {
  general: "Announcement",
  tefillah_times: "Tefillah Times",
  emergency: "Emergency",
};

export default function ResidentHome() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { data: me } = useQuery({
    queryKey: ["residents", "me"],
    queryFn: () => api.get<Resident>("/residents/me"),
  });

  const { data: announcements } = useQuery({
    queryKey: ["announcements"],
    queryFn: () => api.get<Announcement[]>("/announcements"),
  });

  const toggleStatus = useMutation({
    mutationFn: (status: ResidentStatus) => api.patch<Resident>("/residents/me/status", { status }),
    onSuccess: (updated) => queryClient.setQueryData(["residents", "me"], updated),
  });

  return (
    <div className="space-y-6 pb-4">
      <div className="rounded-xl bg-white p-5 shadow-sm">
        <p className="text-sm text-slate-500">Welcome back,</p>
        <h1 className="text-xl font-semibold text-slate-800">{user?.full_name}</h1>

        <div className="mt-4 flex items-center justify-between rounded-lg bg-slate-50 p-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Your status</p>
            <p className="text-lg font-semibold text-slate-800 capitalize">{me?.status ?? "..."}</p>
          </div>
          <button
            disabled={!me || toggleStatus.isPending}
            onClick={() => me && toggleStatus.mutate(me.status === "home" ? "away" : "home")}
            className={`rounded-full px-5 py-2.5 text-sm font-semibold text-white shadow-sm active:scale-95 ${
              me?.status === "home" ? "bg-amber-500" : "bg-green-600"
            }`}
          >
            Mark {me?.status === "home" ? "Away" : "Home"}
          </button>
        </div>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Daily Feed</h2>
        <div className="space-y-2">
          {announcements?.map((a) => (
            <div key={a.id} className="rounded-lg bg-white p-4 shadow-sm">
              <div className="mb-1 flex items-center gap-2">
                {a.pinned && <span className="text-amber-500">📌</span>}
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ${
                    a.category === "emergency"
                      ? "bg-red-100 text-red-700"
                      : a.category === "tefillah_times"
                        ? "bg-indigo-100 text-indigo-700"
                        : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {CATEGORY_LABEL[a.category]}
                </span>
              </div>
              <p className="font-medium text-slate-800">{a.title}</p>
              <p className="text-sm text-slate-600">{a.body}</p>
            </div>
          ))}
          {announcements?.length === 0 && (
            <p className="rounded-lg bg-white p-4 text-sm text-slate-500 shadow-sm">
              No announcements right now.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
