import type { ReactNode } from "react";
import { Link, Navigate, NavLink, Route, Routes } from "react-router-dom";
import BottomNav, { type BottomNavItem } from "./components/BottomNav";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import ResidentLayout from "./layouts/ResidentLayout";
import Admin from "./pages/Admin";
import Announcements from "./pages/Announcements";
import Dashboard from "./pages/Dashboard";
import Inventory from "./pages/Inventory";
import Login from "./pages/Login";
import Maintenance from "./pages/Maintenance";
import Meals from "./pages/Meals";
import PresenceBoard from "./pages/PresenceBoard";
import Profile from "./pages/Profile";
import Register from "./pages/Register";
import RegistrationRequests from "./pages/RegistrationRequests";
import ResidentHome from "./pages/resident/ResidentHome";
import ResidentMeals from "./pages/resident/ResidentMeals";
import ResidentReport from "./pages/resident/ResidentReport";
import Residents from "./pages/Residents";
import Rooms from "./pages/Rooms";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/presence", label: "Presence" },
  { to: "/residents", label: "Residents" },
  { to: "/rooms", label: "Rooms" },
  { to: "/inventory", label: "Inventory" },
  { to: "/maintenance", label: "Maintenance" },
  { to: "/meals", label: "Meals" },
  { to: "/announcements", label: "Announcements" },
];

const BOTTOM_NAV_BY_ROLE: Record<"admin" | "staff" | "av_bayit", BottomNavItem[]> = {
  admin: [
    { to: "/dashboard", label: "Dashboard", icon: "📊" },
    { to: "/presence", label: "Presence", icon: "🏠" },
    { to: "/maintenance", label: "Tickets", icon: "🛠️" },
    { to: "/registrations", label: "Requests", icon: "📝" },
    { to: "/admin", label: "Staff", icon: "👤" },
  ],
  staff: [
    { to: "/dashboard", label: "Dashboard", icon: "📊" },
    { to: "/presence", label: "Presence", icon: "🏠" },
    { to: "/maintenance", label: "Tickets", icon: "🛠️" },
    { to: "/inventory", label: "Inventory", icon: "📦" },
    { to: "/registrations", label: "Requests", icon: "📝" },
  ],
  av_bayit: [
    { to: "/meals", label: "Meals", icon: "🍽️" },
    { to: "/residents", label: "Soldiers", icon: "🎖️" },
    { to: "/announcements", label: "Announce", icon: "📣" },
  ],
};

function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navItems = [...NAV_ITEMS];
  if (user?.role === "admin" || user?.role === "staff") {
    navItems.push({ to: "/registrations", label: "Registrations" });
  }
  if (user?.role === "admin") {
    navItems.push({ to: "/admin", label: "Staff" });
  }
  const bottomItems =
    user?.role === "admin" || user?.role === "staff" || user?.role === "av_bayit"
      ? BOTTOM_NAV_BY_ROLE[user.role]
      : [];

  return (
    <div className="min-h-screen bg-slate-50 pb-16 sm:pb-0">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <span className="font-semibold text-slate-800">Lev LaChayal</span>
          <nav className="hidden flex-wrap gap-4 text-sm sm:flex">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  isActive ? "font-medium text-indigo-600" : "text-slate-600 hover:text-slate-900"
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <Link to="/profile" className="hidden hover:text-indigo-600 sm:inline">
              {user?.full_name}
            </Link>
            <button onClick={() => logout()} className="text-indigo-600 hover:underline">
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      <BottomNav items={bottomItems} />
    </div>
  );
}

function ProtectedRoute({
  children,
  adminOnly = false,
  staffOrAdminOnly = false,
}: {
  children: ReactNode;
  adminOnly?: boolean;
  staffOrAdminOnly?: boolean;
}) {
  const { user, loading } = useAuth();
  if (loading) return <p className="p-8 text-slate-500">Loading...</p>;
  if (!user) return <Navigate to="/login" replace />;
  // Residents get their own mobile-first portal, not the staff shell.
  if (user.role === "resident") return <Navigate to="/r/home" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/dashboard" replace />;
  if (staffOrAdminOnly && user.role !== "admin" && user.role !== "staff") {
    return <Navigate to="/dashboard" replace />;
  }
  return <Layout>{children}</Layout>;
}

function ResidentProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="p-8 text-slate-500">Loading...</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "resident") return <Navigate to="/dashboard" replace />;
  return <ResidentLayout>{children}</ResidentLayout>;
}

function RoleHome() {
  const { user, loading } = useAuth();
  if (loading) return <p className="p-8 text-slate-500">Loading...</p>;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "resident" ? "/r/home" : "/dashboard"} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Staff / admin / av_bayit shell */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/presence"
          element={
            <ProtectedRoute>
              <PresenceBoard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/residents"
          element={
            <ProtectedRoute>
              <Residents />
            </ProtectedRoute>
          }
        />
        <Route
          path="/rooms"
          element={
            <ProtectedRoute>
              <Rooms />
            </ProtectedRoute>
          }
        />
        <Route
          path="/inventory"
          element={
            <ProtectedRoute>
              <Inventory />
            </ProtectedRoute>
          }
        />
        <Route
          path="/maintenance"
          element={
            <ProtectedRoute>
              <Maintenance />
            </ProtectedRoute>
          }
        />
        <Route
          path="/meals"
          element={
            <ProtectedRoute>
              <Meals />
            </ProtectedRoute>
          }
        />
        <Route
          path="/announcements"
          element={
            <ProtectedRoute>
              <Announcements />
            </ProtectedRoute>
          }
        />
        <Route
          path="/registrations"
          element={
            <ProtectedRoute staffOrAdminOnly>
              <RegistrationRequests />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute adminOnly>
              <Admin />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />

        {/* Resident mobile portal */}
        <Route
          path="/r/home"
          element={
            <ResidentProtectedRoute>
              <ResidentHome />
            </ResidentProtectedRoute>
          }
        />
        <Route
          path="/r/profile"
          element={
            <ResidentProtectedRoute>
              <Profile />
            </ResidentProtectedRoute>
          }
        />
        <Route
          path="/r/report"
          element={
            <ResidentProtectedRoute>
              <ResidentReport />
            </ResidentProtectedRoute>
          }
        />
        <Route
          path="/r/meals"
          element={
            <ResidentProtectedRoute>
              <ResidentMeals />
            </ResidentProtectedRoute>
          }
        />

        <Route path="/" element={<RoleHome />} />
      </Routes>
    </AuthProvider>
  );
}
