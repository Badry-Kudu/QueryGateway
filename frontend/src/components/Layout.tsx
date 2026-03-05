import { Database, Globe, LayoutDashboard, Shield } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/connections", label: "Connections", icon: Database },
  { to: "/auth", label: "Auth Methods", icon: Shield },
  { to: "/endpoints", label: "API Endpoints", icon: Globe },
];

export function Layout() {
  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col border-r bg-muted/20">
        <div className="border-b px-4 py-5">
          <h1 className="text-base font-bold tracking-tight">DB2API</h1>
          <p className="mt-0.5 text-xs text-muted-foreground">Admin Console</p>
        </div>
        <nav className="flex-1 space-y-1 px-2 py-4">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t px-4 py-3 text-xs text-muted-foreground">v0.4.0 · Phase 4</div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
