import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { RegistrationRequest, RegistrationStatus, Room } from "../types";

const TABS: { value: RegistrationStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export default function RegistrationRequests() {
  const [tab, setTab] = useState<RegistrationStatus>("pending");
  const queryClient = useQueryClient();

  const { data: requests } = useQuery({
    queryKey: ["registration-requests", tab],
    queryFn: () => api.get<RegistrationRequest[]>(`/registration/requests?status=${tab}`),
  });

  const { data: rooms } = useQuery({
    queryKey: ["rooms"],
    queryFn: () => api.get<Room[]>("/rooms"),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["registration-requests"] });

  const approve = useMutation({
    mutationFn: ({ id, roomId }: { id: string; roomId: string }) =>
      api.post(`/registration/requests/${id}/approve`, { room_id: roomId || null }),
    onSuccess: invalidate,
  });

  const reject = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) =>
      api.post(`/registration/requests/${id}/reject`, { note: note || null }),
    onSuccess: invalidate,
  });

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold text-slate-800">Registration Requests</h1>
      <p className="mb-4 text-sm text-slate-500">
        Review soldiers who self-registered. Approving creates their resident profile and activates their
        login; rejecting leaves no account behind.
      </p>

      <div className="mb-4 flex gap-2 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={`border-b-2 px-3 py-2 text-sm font-medium ${
              tab === t.value
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {requests?.map((r) => (
          <RequestCard
            key={r.id}
            request={r}
            rooms={rooms ?? []}
            onApprove={(roomId) => approve.mutate({ id: r.id, roomId })}
            onReject={(note) => reject.mutate({ id: r.id, note })}
          />
        ))}
        {requests?.length === 0 && (
          <p className="rounded-lg bg-white p-4 text-sm text-slate-500 shadow-sm">
            No {tab} requests.
          </p>
        )}
      </div>
    </div>
  );
}

function RequestCard({
  request,
  rooms,
  onApprove,
  onReject,
}: {
  request: RegistrationRequest;
  rooms: Room[];
  onApprove: (roomId: string) => void;
  onReject: (note: string) => void;
}) {
  const [roomId, setRoomId] = useState("");
  const [note, setNote] = useState("");
  const [rejecting, setRejecting] = useState(false);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium text-slate-800">
            {request.first_name} {request.last_name}
          </p>
          <p className="text-sm text-slate-500">{request.email}</p>
          {request.phone && <p className="text-sm text-slate-500">{request.phone}</p>}
          {request.review_note && (
            <p className="mt-1 text-sm italic text-slate-500">Note: {request.review_note}</p>
          )}
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${
            request.status === "approved"
              ? "bg-green-100 text-green-700"
              : request.status === "rejected"
                ? "bg-slate-200 text-slate-600"
                : "bg-amber-100 text-amber-700"
          }`}
        >
          {request.status}
        </span>
      </div>

      {request.status === "pending" && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
          <select
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">Assign room later</option>
            {rooms.map((room) => (
              <option key={room.id} value={room.id}>
                Floor {room.floor} — Room {room.room_number}
              </option>
            ))}
          </select>
          <button
            onClick={() => onApprove(roomId)}
            className="rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
          >
            Approve
          </button>

          {rejecting ? (
            <>
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Reason (optional)"
                className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
              />
              <button
                onClick={() => onReject(note)}
                className="rounded bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
              >
                Confirm Reject
              </button>
            </>
          ) : (
            <button
              onClick={() => setRejecting(true)}
              className="rounded bg-slate-200 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-300"
            >
              Reject
            </button>
          )}
        </div>
      )}
    </div>
  );
}
