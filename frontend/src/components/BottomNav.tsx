import { NavLink } from "react-router-dom";

export interface BottomNavItem {
  to: string;
  label: string;
  icon: string; // single emoji glyph — keeps this dependency-free for an MVP
}

/** Fixed bottom navigation shown on mobile viewports; items vary by role
 * (see the per-role item lists passed in from each layout). Hidden at the
 * `sm` breakpoint and up, where the top nav takes over. */
export default function BottomNav({ items }: { items: BottomNavItem[] }) {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20 flex border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] sm:hidden"
      aria-label="Primary"
    >
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] ${
              isActive ? "text-indigo-600" : "text-slate-500"
            }`
          }
        >
          <span className="text-xl leading-none">{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
