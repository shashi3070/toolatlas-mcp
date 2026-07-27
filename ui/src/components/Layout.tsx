import { NavLink, Outlet, useSearchParams } from "react-router-dom";
import {
  LayoutDashboard, Server, Shuffle, Wrench, BookOpen, BarChart3, Share2,
} from "lucide-react";
import { primary } from "../theme";

declare global {
  interface Window {
    __TOOLATLAS_TOP_TABS__?: boolean;
  }
}

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/graph", label: "Graph", icon: Share2 },
  { to: "/servers", label: "Servers", icon: Server },
  { to: "/proxies", label: "Proxies", icon: Shuffle },
  { to: "/tools", label: "Tools", icon: Wrench },
  { to: "/glossary", label: "Glossary", icon: BookOpen },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
];

const topTabs = window.__TOOLATLAS_TOP_TABS__ || false;

function NavLinks() {
  return (
    <>
      {navItems.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            topTabs
              ? `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? `font-medium`
                    : `text-slate-600 hover:bg-slate-100 hover:text-slate-900`
                }`
              : `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? `text-white font-medium`
                    : `hover:text-white`
                }`
          }
          style={({ isActive }) => {
            if (topTabs) {
              return isActive
                ? { backgroundColor: primary("100"), color: primary("700") }
                : {};
            }
            return isActive
              ? { backgroundColor: primary("900") }
              : { color: primary("300") };
          }}
        >
          <Icon size={18} />
          {label}
        </NavLink>
      ))}
    </>
  );
}

export default function Layout() {
  const [searchParams] = useSearchParams();
  const embed = searchParams.get("embed") === "true";

  if (topTabs) {
    return (
      <div className="flex flex-col h-screen">
        <header className="bg-white border-b border-slate-200 shrink-0">
          {!embed && (
            <div className="px-4 py-3 border-b border-slate-200">
              <h1 className="text-lg font-bold tracking-tight text-slate-800">ToolAtlas</h1>
              <p className="text-xs text-slate-500">MCP Control Plane</p>
            </div>
          )}
          <nav className="flex items-center gap-1 p-2 overflow-x-auto">
            <NavLinks />
          </nav>
        </header>
        <main className="flex-1 overflow-auto p-6 bg-slate-50">
          <Outlet />
        </main>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <aside
        className="w-56 text-white flex flex-col shrink-0"
        style={{ backgroundColor: primary("950") }}
      >
        <div className="p-4 border-b" style={{ borderColor: primary("900") }}>
          <h1 className="text-lg font-bold tracking-tight">ToolAtlas</h1>
          <p className="text-xs" style={{ color: primary("300") }}>MCP Control Plane</p>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          <NavLinks />
        </nav>
        <div className="p-3 border-t text-xs" style={{ borderColor: primary("900"), color: primary("300") }}>
          v3.0.4
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6 bg-slate-50">
        <Outlet />
      </main>
    </div>
  );
}
