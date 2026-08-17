import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import BottomNav, { type BottomNavItem } from "../components/BottomNav";
import { useAuth } from "../hooks/useAuth";

const RESIDENT_NAV: BottomNavItem[] = [
  { to: "/r/home", label: "Home", icon: "🏠" },
  { to: "/r/report", label: "Report", icon: "🛠️" },
  { to: "/r/meals", label: "Meals", icon: "🍽️" },
];

export default function ResidentLayout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50 pb-16">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
        <span className="font-semibold text-slate-800">Lev LaChayal</span>
        <div className="flex items-center gap-3 text-sm">
          <Link to="/r/profile" className="text-slate-600 hover:text-indigo-600">
            {user?.full_name}
          </Link>
          <button onClick={() => logout()} className="text-indigo-600">
            Sign out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-lg px-4 py-4">{children}</main>
      <BottomNav items={RESIDENT_NAV} />
    </div>
  );
}
