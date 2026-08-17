import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { MealInvitation, MealInvitationStatus } from "../../types";

const STATUS_STYLE: Record<MealInvitationStatus, string> = {
  pending: "bg-amber-100 text-amber-700",
  accepted: "bg-green-100 text-green-700",
  declined: "bg-slate-200 text-slate-600",
};

export default function ResidentMeals() {
  const queryClient = useQueryClient();

  const { data: invitations } = useQuery({
    queryKey: ["meals", "invitations", "mine"],
    queryFn: () => api.get<MealInvitation[]>("/meals/invitations/mine"),
  });

  const respond = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "accepted" | "declined" }) =>
      api.patch<MealInvitation>(`/meals/invitations/${id}/respond`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["meals", "invitations", "mine"] }),
  });

  const pending = invitations?.filter((i) => i.status === "pending") ?? [];
  const answered = invitations?.filter((i) => i.status !== "pending") ?? [];

  return (
    <div className="space-y-6 pb-4">
      <h1 className="text-xl font-semibold text-slate-800">Meal Invitations</h1>

      {pending.length > 0 && (
        <div className="space-y-2">
          {pending.map((inv) => (
            <div key={inv.id} className="rounded-xl bg-white p-4 shadow-sm">
              <p className="font-medium text-slate-800">{inv.host_family_name}</p>
              <p className="text-sm text-slate-500">
                {inv.meal_date} &middot; {inv.meal_type}
              </p>
              {inv.notes && <p className="mt-1 text-sm text-slate-600">{inv.notes}</p>}
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => respond.mutate({ id: inv.id, status: "accepted" })}
                  className="flex-1 rounded-lg bg-green-600 py-2 text-sm font-semibold text-white active:scale-95"
                >
                  Accept
                </button>
                <button
                  onClick={() => respond.mutate({ id: inv.id, status: "declined" })}
                  className="flex-1 rounded-lg bg-slate-200 py-2 text-sm font-semibold text-slate-700 active:scale-95"
                >
                  Decline
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {pending.length === 0 && (
        <p className="rounded-lg bg-white p-4 text-sm text-slate-500 shadow-sm">
          No pending invitations right now.
        </p>
      )}

      {answered.length > 0 && (
        <div>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">History</h2>
          <div className="space-y-2">
            {answered.map((inv) => (
              <div key={inv.id} className="flex items-center justify-between rounded-lg bg-white p-3 shadow-sm">
                <div>
                  <p className="text-sm font-medium text-slate-800">{inv.host_family_name}</p>
                  <p className="text-xs text-slate-500">
                    {inv.meal_date} &middot; {inv.meal_type}
                  </p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLE[inv.status]}`}>
                  {inv.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
