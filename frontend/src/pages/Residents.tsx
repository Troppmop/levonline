import { Fragment, useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { Resident, Room } from "../types";

export default function Residents() {
  const { user } = useAuth();
  const canEdit = user?.role === "admin" || user?.role === "staff";
  const [residents, setResidents] = useState<Resident[] | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  async function load() {
    const [residentData, roomData] = await Promise.all([
      api.get<Resident[]>("/residents"),
      api.get<Room[]>("/rooms"),
    ]);
    setResidents(residentData);
    setRooms(roomData);
  }

  useEffect(() => {
    load();
  }, []);

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

  async function deactivate(residentId: string) {
    await api.post(`/residents/${residentId}/deactivate`);
    setEditingId(null);
    load();
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold text-slate-800">Resident Profiles</h1>

      {canEdit && (
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
                  <td colSpan={5} className="px-4 py-3">
                    <ResidentEditPanel
                      resident={r}
                      rooms={rooms}
                      onAssignRoom={(roomId) => assignRoom(r.id, roomId)}
                      onSetDeposit={(amount, paid) => setDeposit(r.id, amount, paid)}
                      onDeactivate={() => deactivate(r.id)}
                    />
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResidentEditPanel({
  resident,
  rooms,
  onAssignRoom,
  onSetDeposit,
  onDeactivate,
}: {
  resident: Resident;
  rooms: Room[];
  onAssignRoom: (roomId: string) => void;
  onSetDeposit: (amount: string, paid: boolean) => void;
  onDeactivate: () => void;
}) {
  const [depositAmount, setDepositAmount] = useState(resident.security_deposit_amount);
  const [depositPaid, setDepositPaid] = useState(resident.security_deposit_paid);

  return (
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
        <input
          type="checkbox"
          checked={depositPaid}
          onChange={(e) => setDepositPaid(e.target.checked)}
        />
        Paid
      </label>

      <button
        onClick={() => onSetDeposit(depositAmount, depositPaid)}
        className="rounded bg-slate-200 px-3 py-1.5 text-xs hover:bg-slate-300"
      >
        Save Deposit
      </button>

      <button
        onClick={onDeactivate}
        className="ml-auto rounded bg-red-100 px-3 py-1.5 text-xs text-red-700 hover:bg-red-200"
      >
        Deactivate / Moved Out
      </button>
    </div>
  );
}
