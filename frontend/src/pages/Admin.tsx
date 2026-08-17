import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { ApiError, api } from "../api/client";
import Avatar from "../components/Avatar";
import DataManagement from "./admin/DataManagement";
import Rooms from "./Rooms";
import type { Resident, User, UserRole } from "../types";

const ROLES: { value: UserRole; label: string }[] = [
  { value: "staff", label: "Staff" },
  { value: "av_bayit", label: "Av/Eim Bayit" },
  { value: "resident", label: "Resident (self-service login)" },
  { value: "admin", label: "Admin" },
];

export default function Admin() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"staff" | "rooms" | "data">("staff");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("staff");
  const [residentId, setResidentId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<User | null>(null);

  const { data: residents } = useQuery({
    queryKey: ["residents", "for-admin"],
    queryFn: () => api.get<Resident[]>("/residents?limit=500"),
    enabled: role === "resident",
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users"),
    enabled: tab === "staff",
  });

  const createUser = useMutation({
    mutationFn: () =>
      api.post<User>("/auth/register", {
        email,
        password,
        full_name: fullName,
        role,
        resident_id: role === "resident" ? residentId : null,
      }),
    onSuccess: (user) => {
      setCreated(user);
      setEmail("");
      setFullName("");
      setPassword("");
      setResidentId("");
      setRole("staff");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not create user"),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCreated(null);
    createUser.mutate();
  }

  return (
    <div className={tab === "staff" ? "max-w-2xl" : "max-w-4xl"}>
      <h1 className="mb-4 text-2xl font-semibold text-slate-800">Admin Settings</h1>

      <div className="mb-4 flex gap-2 border-b border-slate-200">
        <button
          onClick={() => setTab("staff")}
          className={`px-3 py-2 text-sm font-medium ${
            tab === "staff" ? "border-b-2 border-indigo-600 text-indigo-600" : "text-slate-500"
          }`}
        >
          Staff Accounts
        </button>
        <button
          onClick={() => setTab("rooms")}
          className={`px-3 py-2 text-sm font-medium ${
            tab === "rooms" ? "border-b-2 border-indigo-600 text-indigo-600" : "text-slate-500"
          }`}
        >
          Rooms
        </button>
        <button
          onClick={() => setTab("data")}
          className={`px-3 py-2 text-sm font-medium ${
            tab === "data" ? "border-b-2 border-indigo-600 text-indigo-600" : "text-slate-500"
          }`}
        >
          Data Management (Import / Export)
        </button>
      </div>

      {tab === "rooms" && <Rooms />}
      {tab === "data" && <DataManagement />}

      {tab === "staff" && (
        <div className="space-y-6">
          <div>
            <p className="mb-4 text-sm text-slate-500">
              Create login accounts for staff, Av/Eim Bayit families, residents, and other admins.
            </p>

            <form onSubmit={handleSubmit} className="space-y-3 rounded-lg bg-white p-4 shadow-sm">
              {error && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
              {created && (
                <p className="rounded bg-green-50 px-3 py-2 text-sm text-green-700">
                  Created {created.full_name} ({created.email}) as {created.role}.
                </p>
              )}
              <label className="block text-sm font-medium text-slate-700">
                Full name
                <input
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Email
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Temporary password
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Role
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </label>
              {role === "resident" && (
                <label className="block text-sm font-medium text-slate-700">
                  Which resident profile does this login belong to?
                  <select
                    required
                    value={residentId}
                    onChange={(e) => setResidentId(e.target.value)}
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  >
                    <option value="">Select resident...</option>
                    {residents?.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.first_name} {r.last_name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <button type="submit" className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white">
                Create Account
              </button>
            </form>
          </div>

          <div>
            <h2 className="mb-3 text-lg font-semibold text-slate-800">Existing Accounts</h2>
            <div className="space-y-2">
              {users?.map((u) => (
                <UserRow key={u.id} user={u} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function UserRow({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadAvatar = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.upload<User>(`/users/${user.id}/avatar`, formData);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div className="flex items-center justify-between rounded-lg bg-white p-3 shadow-sm">
      <div className="flex items-center gap-3">
        <Avatar name={user.full_name} url={user.avatar_url} />
        <div>
          <p className="text-sm font-medium text-slate-800">{user.full_name}</p>
          <p className="text-xs capitalize text-slate-500">
            {user.email} &middot; {user.role.replace("_", " ")}
          </p>
        </div>
      </div>
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={uploadAvatar.isPending}
        className="rounded bg-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-300 disabled:opacity-50"
      >
        {uploadAvatar.isPending ? "Uploading..." : user.avatar_url ? "Change Photo" : "Upload Photo"}
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) uploadAvatar.mutate(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
