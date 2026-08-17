import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { MealHostingRecord, MealHostingSummary, MealInvitation, MealType, Resident } from "../types";

function InviteResidentPanel() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [residentId, setResidentId] = useState("");
  const [hostFamilyName, setHostFamilyName] = useState("");
  const [mealDate, setMealDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [mealType, setMealType] = useState<MealType>("shabbat");

  const isAvBayit = user?.role === "av_bayit";

  const { data: residents } = useQuery({
    queryKey: ["residents", "for-invite", isAvBayit],
    queryFn: () => api.get<Resident[]>(`/residents${isAvBayit ? "?assigned_to_me=true" : ""}`),
  });

  const { data: sentInvitations } = useQuery({
    queryKey: ["meals", "invitations", "sent"],
    queryFn: () => api.get<MealInvitation[]>("/meals/invitations/sent"),
  });

  const sendInvite = useMutation({
    mutationFn: () =>
      api.post<MealInvitation>("/meals/invitations", {
        resident_id: residentId,
        host_family_name: hostFamilyName,
        meal_date: mealDate,
        meal_type: mealType,
      }),
    onSuccess: () => {
      setResidentId("");
      queryClient.invalidateQueries({ queryKey: ["meals", "invitations", "sent"] });
    },
  });

  function residentName(id: string) {
    const r = residents?.find((res) => res.id === id);
    return r ? `${r.first_name} ${r.last_name}` : id;
  }

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold text-slate-800">
        {isAvBayit ? "Invite Your Assigned Soldiers" : "Invite a Resident"}
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!residentId || !hostFamilyName.trim()) return;
          sendInvite.mutate();
        }}
        className="grid grid-cols-2 gap-2"
      >
        <select
          value={residentId}
          onChange={(e) => setResidentId(e.target.value)}
          className="col-span-2 rounded border border-slate-300 px-3 py-2 text-sm sm:col-span-1"
        >
          <option value="">Select resident...</option>
          {residents?.map((r) => (
            <option key={r.id} value={r.id}>
              {r.first_name} {r.last_name}
            </option>
          ))}
        </select>
        <input
          value={hostFamilyName}
          onChange={(e) => setHostFamilyName(e.target.value)}
          placeholder="Host family name"
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          type="date"
          value={mealDate}
          onChange={(e) => setMealDate(e.target.value)}
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          value={mealType}
          onChange={(e) => setMealType(e.target.value as MealType)}
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="shabbat">Shabbat</option>
          <option value="yom_tov">Yom Tov</option>
          <option value="weekday">Weekday</option>
        </select>
        <button
          type="submit"
          className="col-span-2 rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white sm:col-span-1"
        >
          Send Invitation
        </button>
      </form>

      {sentInvitations && sentInvitations.length > 0 && (
        <div className="mt-4 space-y-1.5">
          {sentInvitations.map((inv) => (
            <div key={inv.id} className="flex items-center justify-between text-sm">
              <span>
                {residentName(inv.resident_id)} &middot; {inv.meal_date}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                  inv.status === "accepted"
                    ? "bg-green-100 text-green-700"
                    : inv.status === "declined"
                      ? "bg-slate-200 text-slate-600"
                      : "bg-amber-100 text-amber-700"
                }`}
              >
                {inv.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Meals() {
  const { user } = useAuth();
  const [records, setRecords] = useState<MealHostingRecord[] | null>(null);
  const [summary, setSummary] = useState<MealHostingSummary[] | null>(null);
  const [hostFamilyName, setHostFamilyName] = useState("");
  const [guestName, setGuestName] = useState("");
  const [mealDate, setMealDate] = useState(() => new Date().toISOString().slice(0, 10));

  async function load() {
    const [r, s] = await Promise.all([
      api.get<MealHostingRecord[]>("/meals"),
      api.get<MealHostingSummary[]>("/meals/summary"),
    ]);
    setRecords(r);
    setSummary(s);
  }

  useEffect(() => {
    load();
  }, []);

  async function createRecord(e: React.FormEvent) {
    e.preventDefault();
    if (!hostFamilyName.trim() || !guestName.trim()) return;
    await api.post("/meals", {
      host_family_name: hostFamilyName,
      guest_name: guestName,
      meal_date: mealDate,
      meal_type: "shabbat",
      guest_count: 1,
    });
    setHostFamilyName("");
    setGuestName("");
    load();
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h1 className="mb-4 text-2xl font-semibold text-slate-800">Meal Hosting Log</h1>

          <form
            onSubmit={createRecord}
            className="mb-6 grid grid-cols-2 gap-2 rounded-lg bg-white p-4 shadow-sm"
          >
            <input
              value={hostFamilyName}
              onChange={(e) => setHostFamilyName(e.target.value)}
              placeholder="Host family (Av/Eim Bayit)"
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              value={guestName}
              onChange={(e) => setGuestName(e.target.value)}
              placeholder="Who was hosted"
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="date"
              value={mealDate}
              onChange={(e) => setMealDate(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <button type="submit" className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white">
              Log Hosting
            </button>
          </form>

          <div className="space-y-2">
            {records?.map((r) => (
              <div key={r.id} className="rounded-lg bg-white p-3 text-sm shadow-sm">
                <span className="font-medium">{r.host_family_name}</span> hosted{" "}
                <span className="font-medium">{r.guest_name}</span> on {r.meal_date} ({r.meal_type})
              </div>
            ))}
          </div>
        </div>

        <div>
          <h2 className="mb-4 text-lg font-semibold text-slate-800">Hosting Summary</h2>
          <div className="space-y-2">
            {summary?.map((s) => (
              <div key={s.host_family_name} className="rounded-lg bg-white p-3 text-sm shadow-sm">
                <p className="font-medium">{s.host_family_name}</p>
                <p className="text-slate-500">
                  {s.total_meals_hosted} meals &middot; {s.total_guests_hosted} guests
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {(user?.role === "av_bayit" || user?.role === "staff" || user?.role === "admin") && (
        <InviteResidentPanel />
      )}
    </div>
  );
}
