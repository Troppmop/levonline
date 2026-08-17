import { Fragment, useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { Resident, Room } from "../types";

function rentBalance(resident: Resident): number {
  return Number(resident.rent_amount_due) - Number(resident.rent_amount_paid);
}

export default function Residents() {
  const { user } = useAuth();
  const canEdit = user?.role === "admin" || user?.role === "staff";
  const [tab, setTab] = useState<"active" | "former">("active");
  const [residents, setResidents] = useState<Resident[] | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [offboardingResident, setOffboardingResident] = useState<Resident | null>(null);

  async function load() {
    const [residentData, roomData] = await Promise.all([
      api.get<Resident[]>(`/residents?archived=${tab === "former"}`),
      api.get<Room[]>("/rooms"),
    ]);
    setResidents(residentData);
    setRooms(roomData);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function createResident(e: FormEvent) {
    e.preventDefault();
    if (!firstName.trim() || !lastName.trim()) return;
    await api.post("/residents", { first_name: firstName, last_name: lastName });
    setFirstName("");
    setLastName("");
    load();
  }

  async function assignRoom(residentId: string, roomId: string) {
    await api.patch(`/residents/${residentId}`, { room_id: roomId || null });
    load();
  }

  async function setDeposit(residentId: string, amount: string, paid: boolean) {
    await api.patch(`/residents/${residentId}`, {
      security_deposit_amount: amount || "0",
      security_deposit_paid: paid,
    });
    load();
  }

  async function setRent(residentId: string, due: string, paid: string) {
    await api.patch(`/residents/${residentId}`, {
      rent_amount_due: due || "0",
      rent_amount_paid: paid || "0",
    });
    load();
  }

  async function confirmOffboard(checklist: {
    key_returned: boolean;
    biometric_cleared: boolean;
    balance_settled: boolean;
    note: string;
  }) {
    if (!offboardingResident) return;
    await api.post(`/residents/${offboardingResident.id}/offboard`, checklist);
    setOffboardingResident(null);
    setEditingId(null);
    load();
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
          onSubmit={createResident}
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
                      rooms={rooms}
                      onAssignRoom={(roomId) => assignRoom(r.id, roomId)}
                      onSetDeposit={(amount, paid) => setDeposit(r.id, amount, paid)}
                      onSetRent={(due, paid) => setRent(r.id, due, paid)}
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
          onCancel={() => setOffboardingResident(null)}
          onConfirm={confirmOffboard}
        />
      )}
    </div>
  );
}

function ResidentEditPanel({
  resident,
  rooms,
  onAssignRoom,
  onSetDeposit,
  onSetRent,
  onOffboard,
}: {
  resident: Resident;
  rooms: Room[];
  onAssignRoom: (roomId: string) => void;
  onSetDeposit: (amount: string, paid: boolean) => void;
  onSetRent: (due: string, paid: string) => void;
  onOffboard: () => void;
}) {
  const [depositAmount, setDepositAmount] = useState(resident.security_deposit_amount);
  const [depositPaid, setDepositPaid] = useState(resident.security_deposit_paid);
  const [rentDue, setRentDue] = useState(resident.rent_amount_due);
  const [rentPaid, setRentPaid] = useState(resident.rent_amount_paid);

  return (
    <div className="space-y-3">
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
          Deposit amount
          <input
            value={depositAmount}
            onChange={(e) => setDepositAmount(e.target.value)}
            className="mt-1 block w-28 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>

        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input type="checkbox" checked={depositPaid} onChange={(e) => setDepositPaid(e.target.checked)} />
          Paid
        </label>

        <button
          onClick={() => onSetDeposit(depositAmount, depositPaid)}
          className="rounded bg-slate-200 px-3 py-1.5 text-xs hover:bg-slate-300"
        >
          Save Deposit
        </button>
      </div>

      <div className="flex flex-wrap items-end gap-4">
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

        <button
          onClick={() => onSetRent(rentDue, rentPaid)}
          className="rounded bg-slate-200 px-3 py-1.5 text-xs hover:bg-slate-300"
        >
          Save Rent
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
  onCancel,
  onConfirm,
}: {
  resident: Resident;
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
            className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            Confirm Offboard
          </button>
        </div>
      </div>
    </div>
  );
}
