import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard, Server, Shuffle, Wrench, BookOpen, BarChart3, Share2,
} from "lucide-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/graph", label: "Graph", icon: Share2 },
  { to: "/servers", label: "Servers", icon: Server },
  { to: "/proxies", label: "Proxies", icon: Shuffle },
  { to: "/tools", label: "Tools", icon: Wrench },
  { to: "/glossary", label: "Glossary", icon: BookOpen },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
];

export default function Layout() {
  return (
    <div className="flex h-screen">
      <aside className="w-56 bg-blue-950 text-white flex flex-col shrink-0">
        <div className="p-4 border-b border-blue-900">
          <h1 className="text-lg font-bold tracking-tight">ToolAtlas</h1>
          <p className="text-xs text-blue-300">MCP Control Plane</p>
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
                    ? "bg-blue-900 text-white font-medium"
                    : "text-blue-300 hover:bg-blue-900 hover:text-white"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-blue-900 text-xs text-blue-300">
          v3.0.3
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6 bg-slate-50">
        <Outlet />
      </main>
    </div>
  );
}
