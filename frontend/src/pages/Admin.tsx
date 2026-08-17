import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ApiError, api } from "../api/client";
import type { Resident, User, UserRole } from "../types";

const ROLES: { value: UserRole; label: string }[] = [
  { value: "staff", label: "Staff" },
  { value: "av_bayit", label: "Av/Eim Bayit" },
  { value: "resident", label: "Resident (self-service login)" },
  { value: "admin", label: "Admin" },
];

export default function Admin() {
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

  async function createUser(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCreated(null);
    try {
      const user = await api.post<User>("/auth/register", {
        email,
        password,
        full_name: fullName,
        role,
        resident_id: role === "resident" ? residentId : null,
      });
      setCreated(user);
      setEmail("");
      setFullName("");
      setPassword("");
      setResidentId("");
      setRole("staff");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create user");
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="mb-4 text-2xl font-semibold text-slate-800">Staff Accounts</h1>
      <p className="mb-4 text-sm text-slate-500">
        Create login accounts for staff, Av/Eim Bayit families, residents, and other admins.
      </p>

      <form onSubmit={createUser} className="space-y-3 rounded-lg bg-white p-4 shadow-sm">
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
  );
}
