import { useEffect, useState } from "react";
import { Server, Shuffle, Wrench, PhoneCall, Activity, Zap, AlertTriangle } from "lucide-react";
import { dashboardApi, type DashboardSummary } from "../api/client";
import Loading from "../components/Loading";

export default function Dashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    dashboardApi.summary().then(setData).finally(() => setLoaded(true));
  }, []);

  if (!loaded) {
    return (
      <div>
        <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
        <Loading />
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
        <p className="text-red-500">Failed to load dashboard data</p>
      </div>
    );
  }

  const { servers, proxies, tools, calls, latency } = data;

  const cards = [
    { label: "Servers", value: servers.total, sub: `${servers.connected} connected, ${servers.disconnected} down`, icon: Server, color: "bg-blue-500" },
    { label: "Proxies", value: proxies.total, sub: `${servers.total_tools} tools across all`, icon: Shuffle, color: "bg-emerald-500" },
    { label: "Tools", value: tools.total, sub: `${calls.total} total calls`, icon: Wrench, color: "bg-amber-500" },
    { label: "Calls/min", value: calls.per_minute, sub: `${latency.avg_ms.toFixed(0)}ms avg latency`, icon: Activity, color: "bg-violet-500" },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {cards.map(({ label, value, sub, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl shadow-sm border p-5 flex items-center gap-4">
            <div className={`${color} rounded-lg p-3 text-white shrink-0`}>
              <Icon size={24} />
            </div>
            <div className="min-w-0">
              <p className="text-sm text-slate-500">{label}</p>
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs text-slate-400 truncate">{sub}</p>
            </div>
          </div>
        ))}
      </div>

      {servers.disconnected > 0 && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-6">
          <AlertTriangle size={18} className="text-red-500 shrink-0" />
          <p className="text-sm text-red-700">{servers.disconnected} server{servers.disconnected > 1 ? "s" : ""} disconnected</p>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border p-5">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <Zap size={16} className="text-slate-400" />
          System Health
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide">Servers</p>
            <p className="text-lg font-bold">
              {servers.connected}/{servers.total}
              <span className="text-sm font-normal text-slate-400 ml-1">connected</span>
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide">Avg Latency</p>
            <p className="text-lg font-bold">{latency.avg_ms.toFixed(0)} <span className="text-sm font-normal text-slate-400">ms</span></p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide">Tools</p>
            <p className="text-lg font-bold">{tools.total}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide">Cache</p>
            <p className="text-lg font-bold">{(data.cache.hit_rate * 100).toFixed(0)}% <span className="text-sm font-normal text-slate-400">hit</span></p>
          </div>
        </div>
      </div>
    </div>
  );
}
