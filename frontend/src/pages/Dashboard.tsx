import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { DamageReport, InventoryItem, Resident } from "../types";

function StatTile({
  label,
  value,
  to,
  tone = "default",
}: {
  label: string;
  value: string;
  to: string;
  tone?: "default" | "warning";
}) {
  return (
    <Link
      to={to}
      className={`block rounded-xl p-4 shadow-sm ${tone === "warning" ? "bg-red-50" : "bg-white"}`}
    >
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone === "warning" ? "text-red-700" : "text-slate-800"}`}>
        {value}
      </p>
    </Link>
  );
}

export default function Dashboard() {
  const { data: residents } = useQuery({
    queryKey: ["residents", "all", 500],
    queryFn: () => api.get<Resident[]>("/residents?limit=500"),
  });

  const { data: lowStock } = useQuery({
    queryKey: ["inventory", "low-stock"],
    queryFn: () => api.get<InventoryItem[]>("/inventory/low-stock"),
  });

  const { data: reports } = useQuery({
    queryKey: ["maintenance", "reports", "all", 500],
    queryFn: () => api.get<DamageReport[]>("/maintenance/reports?limit=500"),
  });

  const homeCount = residents?.filter((r) => r.status === "home").length ?? 0;
  const totalCount = residents?.length ?? 0;
  const openTickets = reports?.filter((r) => r.status !== "closed").length ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-800">Live Dashboard</h1>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Home / Total" value={`${homeCount}/${totalCount}`} to="/presence" />
        <StatTile
          label="Low Stock Items"
          value={String(lowStock?.length ?? 0)}
          to="/inventory"
          tone={(lowStock?.length ?? 0) > 0 ? "warning" : "default"}
        />
        <StatTile
          label="Open Tickets"
          value={String(openTickets)}
          to="/maintenance"
          tone={openTickets > 0 ? "warning" : "default"}
        />
        <StatTile label="Residents" value={String(totalCount)} to="/residents" />
      </div>
    </div>
  );
}
