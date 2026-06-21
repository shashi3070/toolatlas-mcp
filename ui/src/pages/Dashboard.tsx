import { useEffect, useState } from "react";
import { Server, Shuffle, Wrench, PhoneCall } from "lucide-react";
import { analyticsApi, proxiesApi, serversApi, toolsApi } from "../api/client";

export default function Dashboard() {
  const [stats, setStats] = useState({ servers: 0, proxies: 0, tools: 0, calls: 0 });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Promise.all([
      serversApi.list().then((s) => setStats((p) => ({ ...p, servers: s.length }))),
      proxiesApi.list().then((s) => setStats((p) => ({ ...p, proxies: s.length }))),
      toolsApi.list().then((s) => setStats((p) => ({ ...p, tools: s.length }))),
      analyticsApi.stats().then((s) => setStats((p) => ({ ...p, calls: s.total_calls }))),
    ]).then(() => setLoaded(true));
  }, []);

  const cards = [
    { label: "Servers", value: stats.servers, icon: Server, color: "bg-blue-500" },
    { label: "Proxies", value: stats.proxies, icon: Shuffle, color: "bg-emerald-500" },
    { label: "Tools", value: stats.tools, icon: Wrench, color: "bg-amber-500" },
    { label: "Tool Calls", value: stats.calls, icon: PhoneCall, color: "bg-violet-500" },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      {!loaded ? (
        <p className="text-slate-400">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {cards.map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white rounded-xl shadow-sm border p-5 flex items-center gap-4">
              <div className={`${color} rounded-lg p-3 text-white`}>
                <Icon size={24} />
              </div>
              <div>
                <p className="text-sm text-slate-500">{label}</p>
                <p className="text-2xl font-bold">{value}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
