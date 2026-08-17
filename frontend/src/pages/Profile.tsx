import { useState, type FormEvent } from "react";
import { ApiError, api, logout as apiLogout } from "../api/client";
import { useAuth } from "../hooks/useAuth";

export default function Profile() {
  const { user } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSaved, setProfileSaved] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [changingPassword, setChangingPassword] = useState(false);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setProfileError(null);
    setProfileSaved(false);
    setSavingProfile(true);
    try {
      await api.patch("/auth/me", { full_name: fullName, email });
      setProfileSaved(true);
    } catch (err) {
      setProfileError(err instanceof ApiError ? err.message : "Could not save changes");
    } finally {
      setSavingProfile(false);
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setPasswordError(null);

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords don't match");
      return;
    }

    setChangingPassword(true);
    try {
      await api.post("/auth/me/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      // Changing the password revokes every other session, including the
      // access token this tab is holding — send them back to log in fresh
      // rather than leaving them on a page that's about to start 401ing.
      await apiLogout();
      window.location.href = "/login";
    } catch (err) {
      setPasswordError(err instanceof ApiError ? err.message : "Could not change password");
      setChangingPassword(false);
    }
  }

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold text-slate-800">My Profile</h1>

      <form onSubmit={saveProfile} className="space-y-3 rounded-lg bg-white p-4 shadow-sm">
        <h2 className="font-medium text-slate-700">Account details</h2>
        {profileError && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{profileError}</p>}
        {profileSaved && (
          <p className="rounded bg-green-50 px-3 py-2 text-sm text-green-700">Saved.</p>
        )}
        <label className="block text-sm font-medium text-slate-700">
          Full name
          <input
            required
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value);
              setProfileSaved(false);
            }}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setProfileSaved(false);
            }}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm text-slate-500 capitalize">Role: {user?.role.replace("_", " ")}</label>
        <button
          type="submit"
          disabled={savingProfile}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {savingProfile ? "Saving..." : "Save changes"}
        </button>
      </form>

      <form onSubmit={changePassword} className="space-y-3 rounded-lg bg-white p-4 shadow-sm">
        <h2 className="font-medium text-slate-700">Change password</h2>
        {passwordError && (
          <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{passwordError}</p>
        )}
        <label className="block text-sm font-medium text-slate-700">
          Current password
          <input
            type="password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          New password
          <input
            type="password"
            required
            minLength={8}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Confirm new password
          <input
            type="password"
            required
            minLength={8}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <p className="text-xs text-slate-500">
          Changing your password will sign you out of every other device.
        </p>
        <button
          type="submit"
          disabled={changingPassword}
          className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
        >
          {changingPassword ? "Changing..." : "Change password"}
        </button>
      </form>
    </div>
  );
}
