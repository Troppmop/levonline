import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ResidentStatus, RoomWithResidents } from "../types";

function groupByFloor(rooms: RoomWithResidents[]) {
  const byFloor = new Map<number, RoomWithResidents[]>();
  for (const room of rooms) {
    const list = byFloor.get(room.floor) ?? [];
    list.push(room);
    byFloor.set(room.floor, list);
  }
  return [...byFloor.entries()].sort(([a], [b]) => a - b);
}

export default function PresenceBoard() {
  const [rooms, setRooms] = useState<RoomWithResidents[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await api.get<RoomWithResidents[]>("/residents/presence");
      setRooms(data);
    } catch {
      setError("Could not load presence board");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggleStatus(residentId: string, current: ResidentStatus) {
    const next: ResidentStatus = current === "home" ? "away" : "home";
    await api.patch(`/residents/${residentId}/status`, { status: next });
    load();
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!rooms) return <p className="text-slate-500">Loading presence board...</p>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold text-slate-800">Presence Tracker</h1>
      {groupByFloor(rooms).map(([floor, floorRooms]) => (
        <section key={floor}>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Floor {floor}</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {floorRooms.map((room) => (
              <div key={room.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-2 font-medium text-slate-700">Room {room.room_number}</h3>
                {room.residents.length === 0 && <p className="text-xs text-slate-400">Vacant</p>}
                <ul className="space-y-1">
                  {room.residents.map((resident) => (
                    <li key={resident.id} className="flex items-center justify-between text-sm">
                      <span>
                        {resident.first_name} {resident.last_name}
                      </span>
                      <button
                        onClick={() => toggleStatus(resident.id, resident.status)}
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          resident.status === "home"
                            ? "bg-green-100 text-green-700"
                            : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {resident.status === "home" ? "Home" : "Away"}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
