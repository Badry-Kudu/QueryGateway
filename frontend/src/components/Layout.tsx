import {
  Activity,
  Clock,
  Cog,
  Database,
  Globe,
  LayoutDashboard,
  LogOut,
  Shield,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/connections", label: "Connections", icon: Database },
  { to: "/auth", label: "Auth Methods", icon: Shield },
  { to: "/endpoints", label: "API Endpoints", icon: Globe },
  { to: "/schedules", label: "Schedules", icon: Clock },
  { to: "/settings", label: "Settings", icon: Cog },
  { to: "/health", label: "Health", icon: Activity },
];

export function Layout() {
  const { clearToken } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    clearToken();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col border-r bg-muted/20">
        <div className="border-b px-4 py-5">
          <h1 className="text-base font-bold tracking-tight">QueryGateway</h1>
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
        <div className="border-t px-2 py-3">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2.5 text-muted-foreground hover:text-foreground"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4 shrink-0" />
            Sign out
          </Button>
          <p className="mt-2 px-3 text-xs text-muted-foreground">v0.6.0 · Phase 6</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
