import type { ReactNode } from "react";
import BottomNav, { type BottomNavItem } from "../components/BottomNav";
import { useAuth } from "../hooks/useAuth";

const RESIDENT_NAV: BottomNavItem[] = [
  { to: "/r/home", label: "Home", icon: "🏠" },
  { to: "/r/report", label: "Report", icon: "🛠️" },
  { to: "/r/meals", label: "Meals", icon: "🍽️" },
];

export default function ResidentLayout({ children }: { children: ReactNode }) {
  const { logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50 pb-16">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
        <span className="font-semibold text-slate-800">Lev LaChayal</span>
        <button onClick={() => logout()} className="text-sm text-indigo-600">
          Sign out
        </button>
      </header>
      <main className="mx-auto max-w-lg px-4 py-4">{children}</main>
      <BottomNav items={RESIDENT_NAV} />
    </div>
  );
}
