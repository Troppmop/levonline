import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState, type FormEvent } from "react";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { Resident, Room } from "../types";

function rentBalance(resident: Resident): number {
  return Number(resident.rent_amount_due) - Number(resident.rent_amount_paid);
}

export default function Residents() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const canEdit = user?.role === "admin" || user?.role === "staff";
  const [tab, setTab] = useState<"active" | "former">("active");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [offboardingResident, setOffboardingResident] = useState<Resident | null>(null);

  const { data: residents } = useQuery({
    queryKey: ["residents", tab],
    queryFn: () => api.get<Resident[]>(`/residents?archived=${tab === "former"}`),
  });

  const { data: rooms } = useQuery({
    queryKey: ["rooms"],
    queryFn: () => api.get<Room[]>("/rooms"),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["residents"] });
  }

  const createResident = useMutation({
    mutationFn: () => api.post("/residents", { first_name: firstName, last_name: lastName }),
    onSuccess: () => {
      setFirstName("");
      setLastName("");
      invalidate();
    },
  });

  const assignRoom = useMutation({
    mutationFn: ({ residentId, roomId }: { residentId: string; roomId: string }) =>
      api.patch(`/residents/${residentId}`, { room_id: roomId || null }),
    onSuccess: invalidate,
  });

  const saveDetails = useMutation({
    mutationFn: ({ residentId, changes }: { residentId: string; changes: Record<string, unknown> }) =>
      api.patch(`/residents/${residentId}`, changes),
    onSuccess: invalidate,
  });

  const offboard = useMutation({
    mutationFn: (checklist: {
      key_returned: boolean;
      biometric_cleared: boolean;
      balance_settled: boolean;
      note: string;
    }) => api.post(`/residents/${offboardingResident!.id}/offboard`, checklist),
    onSuccess: () => {
      setOffboardingResident(null);
      setEditingId(null);
      invalidate();
    },
  });

  function handleCreateSubmit(e: FormEvent) {
    e.preventDefault();
    if (!firstName.trim() || !lastName.trim()) return;
    createResident.mutate();
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold text-slate-800">Resident Profiles</h1>

      <div className="mb-4 flex gap-2 border-b border-slate-200">
        <button
          onClick={() => setTab("active")}
          className={`px-3 py-2 text-sm font-medium ${
            tab === "active" ? "border-b-2 border-indigo-600 text-indigo-600" : "text-slate-500"
          }`}
        >
          Active Residents
        </button>
        <button
          onClick={() => setTab("former")}
          className={`px-3 py-2 text-sm font-medium ${
            tab === "former" ? "border-b-2 border-indigo-600 text-indigo-600" : "text-slate-500"
          }`}
        >
          Former / Retired Residents
        </button>
      </div>

      {canEdit && tab === "active" && (
        <form
          onSubmit={handleCreateSubmit}
          className="mb-6 flex flex-col gap-2 rounded-lg bg-white p-4 shadow-sm sm:flex-row"
        >
          <input
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            placeholder="First name"
            className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            placeholder="Last name"
            className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
          />
          <button type="submit" className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white">
            Add Resident
          </button>
        </form>
      )}

      <table className="w-full overflow-hidden rounded-lg bg-white text-sm shadow-sm">
        <thead className="bg-slate-100 text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-4 py-2">Name</th>
            <th className="px-4 py-2">Room</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Security Deposit</th>
            <th className="px-4 py-2">Rent Balance</th>
            {canEdit && <th className="px-4 py-2"></th>}
          </tr>
        </thead>
        <tbody>
          {residents?.map((r) => (
            <Fragment key={r.id}>
              <tr className="border-t border-slate-100">
                <td className="px-4 py-2 font-medium">
                  {r.first_name} {r.last_name}
                  {!r.in_country && (
                    <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-700">
                      Out of country
                    </span>
                  )}
                </td>
                <td className="px-4 py-2">{r.room ? r.room.room_number : "Unassigned"}</td>
                <td className="px-4 py-2 capitalize">{r.status}</td>
                <td className="px-4 py-2">
                  ${r.security_deposit_amount} {r.security_deposit_paid ? "(paid)" : "(unpaid)"}
                </td>
                <td className="px-4 py-2">
                  <span className={rentBalance(r) > 0 ? "font-medium text-red-600" : "text-slate-500"}>
                    ${rentBalance(r).toFixed(2)}
                  </span>
                </td>
                {canEdit && (
                  <td className="px-4 py-2">
                    <button
                      onClick={() => setEditingId(editingId === r.id ? null : r.id)}
                      className="text-xs text-indigo-600 hover:underline"
                    >
                      {editingId === r.id ? "Close" : "Edit"}
                    </button>
                  </td>
                )}
              </tr>
              {canEdit && editingId === r.id && (
                <tr className="border-t border-slate-100 bg-slate-50">
                  <td colSpan={6} className="px-4 py-3">
                    <ResidentEditPanel
                      resident={r}
                      rooms={rooms ?? []}
                      saving={saveDetails.isPending}
                      onAssignRoom={(roomId) => assignRoom.mutate({ residentId: r.id, roomId })}
                      onSave={(changes) => saveDetails.mutate({ residentId: r.id, changes })}
                      onOffboard={() => setOffboardingResident(r)}
                    />
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
      {residents?.length === 0 && (
        <p className="mt-4 text-slate-500">
          {tab === "active" ? "No active residents." : "No former residents yet."}
        </p>
      )}

      {offboardingResident && (
        <OffboardModal
          resident={offboardingResident}
          submitting={offboard.isPending}
          onCancel={() => setOffboardingResident(null)}
          onConfirm={(checklist) => offboard.mutate(checklist)}
        />
      )}
    </div>
  );
}

function ResidentEditPanel({
  resident,
  rooms,
  saving,
  onAssignRoom,
  onSave,
  onOffboard,
}: {
  resident: Resident;
  rooms: Room[];
  saving: boolean;
  onAssignRoom: (roomId: string) => void;
  onSave: (changes: Record<string, unknown>) => void;
  onOffboard: () => void;
}) {
  const [depositAmount, setDepositAmount] = useState(resident.security_deposit_amount);
  const [depositPaid, setDepositPaid] = useState(resident.security_deposit_paid);
  const [rentDue, setRentDue] = useState(resident.rent_amount_due);
  const [rentPaid, setRentPaid] = useState(resident.rent_amount_paid);
  const [contractSigned, setContractSigned] = useState(resident.contract_signed);
  const [hasHoraatKeva, setHasHoraatKeva] = useState(resident.has_horaat_keva);
  const [inCountry, setInCountry] = useState(resident.in_country);
  const [moveInDate, setMoveInDate] = useState(resident.move_in_date ?? "");
  const [moveOutDate, setMoveOutDate] = useState(resident.move_out_date ?? "");
  const [notes, setNotes] = useState(resident.notes ?? "");

  function handleSave() {
    onSave({
      security_deposit_amount: depositAmount || "0",
      security_deposit_paid: depositPaid,
      rent_amount_due: rentDue || "0",
      rent_amount_paid: rentPaid || "0",
      contract_signed: contractSigned,
      has_horaat_keva: hasHoraatKeva,
      in_country: inCountry,
      move_in_date: moveInDate || null,
      move_out_date: moveOutDate || null,
      notes: notes || null,
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-xs text-slate-600">
          Room
          <select
            defaultValue={resident.room_id ?? ""}
            onChange={(e) => onAssignRoom(e.target.value)}
            className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">Unassigned</option>
            {rooms.map((room) => (
              <option key={room.id} value={room.id}>
                Floor {room.floor} — Room {room.room_number}
              </option>
            ))}
          </select>
        </label>

        <label className="text-xs text-slate-600">
          Move-in date
          <input
            type="date"
            value={moveInDate}
            onChange={(e) => setMoveInDate(e.target.value)}
            className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        <label className="text-xs text-slate-600">
          Move-out date
          <input
            type="date"
            value={moveOutDate}
            onChange={(e) => setMoveOutDate(e.target.value)}
            className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <label className="text-xs text-slate-600">
          Deposit amount
          <input
            value={depositAmount}
            onChange={(e) => setDepositAmount(e.target.value)}
            className="mt-1 block w-28 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input type="checkbox" checked={depositPaid} onChange={(e) => setDepositPaid(e.target.checked)} />
          Deposit paid
        </label>

        <label className="text-xs text-slate-600">
          Rent due
          <input
            value={rentDue}
            onChange={(e) => setRentDue(e.target.value)}
            className="mt-1 block w-28 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs text-slate-600">
          Rent paid
          <input
            value={rentPaid}
            onChange={(e) => setRentPaid(e.target.value)}
            className="mt-1 block w-28 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={contractSigned}
            onChange={(e) => setContractSigned(e.target.checked)}
          />
          Contract signed
        </label>
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={hasHoraatKeva}
            onChange={(e) => setHasHoraatKeva(e.target.checked)}
          />
          Horaat Keva on file
        </label>
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input type="checkbox" checked={inCountry} onChange={(e) => setInCountry(e.target.checked)} />
          Currently in the country
        </label>
      </div>

      <label className="block text-xs text-slate-600">
        Comments (allergies, important notes, etc.)
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
      </label>

      <div className="flex items-center gap-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded bg-indigo-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>

        {!resident.is_archived && (
          <button
            onClick={onOffboard}
            className="ml-auto rounded bg-red-100 px-3 py-1.5 text-xs text-red-700 hover:bg-red-200"
          >
            Offboard Resident
          </button>
        )}
      </div>
    </div>
  );
}

function OffboardModal({
  resident,
  submitting,
  onCancel,
  onConfirm,
}: {
  resident: Resident;
  submitting: boolean;
  onCancel: () => void;
  onConfirm: (checklist: {
    key_returned: boolean;
    biometric_cleared: boolean;
    balance_settled: boolean;
    note: string;
  }) => void;
}) {
  const [keyReturned, setKeyReturned] = useState(false);
  const [biometricCleared, setBiometricCleared] = useState(false);
  const [balanceSettled, setBalanceSettled] = useState(rentBalance(resident) <= 0);
  const [note, setNote] = useState("");

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-lg">
        <h2 className="text-lg font-semibold text-slate-800">
          Offboard {resident.first_name} {resident.last_name}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          This moves the resident to Former / Retired and records the checklist below in their activity log.
        </p>

        <div className="mt-4 space-y-2">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={keyReturned} onChange={(e) => setKeyReturned(e.target.checked)} />
            Room key returned
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={biometricCleared}
              onChange={(e) => setBiometricCleared(e.target.checked)}
            />
            Biometric access cleared
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={balanceSettled}
              onChange={(e) => setBalanceSettled(e.target.checked)}
            />
            Deposit / rent balance settled (remaining: ${rentBalance(resident).toFixed(2)})
          </label>
          <label className="block text-sm text-slate-700">
            Note (optional)
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200"
          >
            Cancel
          </button>
          <button
            onClick={() =>
              onConfirm({
                key_returned: keyReturned,
                biometric_cleared: biometricCleared,
                balance_settled: balanceSettled,
                note,
              })
            }
            disabled={submitting}
            className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            {submitting ? "Saving..." : "Confirm Offboard"}
          </button>
        </div>
      </div>
    </div>
  );
}
