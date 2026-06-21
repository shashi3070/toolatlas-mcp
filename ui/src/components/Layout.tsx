import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard, Server, Shuffle, Wrench, BookOpen, BarChart3,
} from "lucide-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/servers", label: "Servers", icon: Server },
  { to: "/proxies", label: "Proxies", icon: Shuffle },
  { to: "/tools", label: "Tools", icon: Wrench },
  { to: "/glossary", label: "Glossary", icon: BookOpen },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
];

export default function Layout() {
  return (
    <div className="flex h-screen">
      <aside className="w-56 bg-slate-900 text-white flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-lg font-bold tracking-tight">ToolAtlas</h1>
          <p className="text-xs text-slate-400">MCP Control Plane</p>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-slate-700 text-white font-medium"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-slate-700 text-xs text-slate-500">
          v0.1.0
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
