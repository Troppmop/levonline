import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Room } from "../types";

export default function Rooms() {
  const queryClient = useQueryClient();
  const { data: rooms } = useQuery({
    queryKey: ["rooms"],
    queryFn: () => api.get<Room[]>("/rooms"),
  });

  const [floor, setFloor] = useState("1");
  const [roomNumber, setRoomNumber] = useState("");
  const [capacity, setCapacity] = useState("1");
  const [error, setError] = useState<string | null>(null);

  const createRoom = useMutation({
    mutationFn: () =>
      api.post("/rooms", {
        floor: Number(floor),
        room_number: roomNumber,
        capacity: Number(capacity) || 1,
      }),
    onSuccess: () => {
      setRoomNumber("");
      queryClient.invalidateQueries({ queryKey: ["rooms"] });
    },
    onError: () => setError("Could not create room — check the floor/room number."),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!roomNumber.trim()) return;
    createRoom.mutate();
  }

  return (
    <div>
      <p className="mb-4 text-sm text-slate-500">
        Rooms drive the Presence Tracker layout — create one per physical room, grouped by floor.
      </p>

      <form onSubmit={handleSubmit} className="mb-6 flex flex-wrap items-end gap-2 rounded-lg bg-white p-4 shadow-sm">
        <label className="text-sm text-slate-600">
          Floor
          <input
            type="number"
            min={0}
            value={floor}
            onChange={(e) => setFloor(e.target.value)}
            className="mt-1 block w-20 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-sm text-slate-600">
          Room number
          <input
            value={roomNumber}
            onChange={(e) => setRoomNumber(e.target.value)}
            placeholder="e.g. 101"
            className="mt-1 block w-32 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-sm text-slate-600">
          Capacity
          <input
            type="number"
            min={1}
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
            className="mt-1 block w-20 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <button type="submit" className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white">
          Add Room
        </button>
        {error && <span className="text-sm text-red-600">{error}</span>}
      </form>

      <table className="w-full overflow-hidden rounded-lg bg-white text-sm shadow-sm">
        <thead className="bg-slate-100 text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-4 py-2">Floor</th>
            <th className="px-4 py-2">Room</th>
            <th className="px-4 py-2">Capacity</th>
          </tr>
        </thead>
        <tbody>
          {rooms
            ?.slice()
            .sort((a, b) => a.floor - b.floor || a.display_order - b.display_order)
            .map((room) => (
              <tr key={room.id} className="border-t border-slate-100">
                <td className="px-4 py-2">{room.floor}</td>
                <td className="px-4 py-2 font-medium">{room.room_number}</td>
                <td className="px-4 py-2">{room.capacity}</td>
              </tr>
            ))}
        </tbody>
      </table>
      {rooms?.length === 0 && <p className="mt-4 text-slate-500">No rooms yet — add the first one above.</p>}
    </div>
  );
}
