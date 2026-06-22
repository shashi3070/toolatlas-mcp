import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";
import { analyticsApi, proxiesApi, toolsApi, type CallDetail, type CallRecord, type CallStats, type Proxy, type Tool } from "../api/client";

const EVENT_ICONS: Record<string, string> = {
  request_received: "📥",
  proxy_lookup: "🔗",
  tool_resolution: "⚙️",
  tool_disabled: "🚫",
  server_call_start: "➡️",
  server_response: "⬅️",
  call_completed: "✅",
};

const EVENT_LABELS: Record<string, string> = {
  request_received: "Client Request",
  proxy_lookup: "Proxy Resolution",
  tool_resolution: "Tool Resolution",
  tool_disabled: "Tool Disabled",
  server_call_start: "Server Forward",
  server_response: "Server Response",
  call_completed: "Completed",
};

function TraceModal({ call, onClose }: { call: CallDetail | null; onClose: () => void }) {
  if (!call) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl border w-full max-w-3xl max-h-[90vh] overflow-y-auto mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b">
          <h3 className="font-bold text-lg">Trace Detail</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">&times;</button>
        </div>

        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm bg-slate-50 rounded-lg p-4">
            <div><span className="text-slate-500">Tool</span><p className="font-medium">{call.tool_name}</p></div>
            <div><span className="text-slate-500">Duration</span><p className="font-medium">{call.duration_ms.toFixed(0)} ms</p></div>
            <div>
              <span className="text-slate-500">Status</span>
              <p><span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${call.success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                {call.success ? "Success" : "Failed"}
              </span></p>
            </div>
            {call.trace_id && <div><span className="text-slate-500">Trace ID</span><p className="font-mono text-xs truncate">{call.trace_id}</p></div>}
            {call.error_message && (
              <div className="col-span-2">
                <span className="text-slate-500">Error</span>
                <p className="text-red-600 text-xs mt-1 bg-red-50 rounded p-2">{call.error_message}</p>
              </div>
            )}
          </div>

          {call.request_args && Object.keys(call.request_args).length > 0 && (
            <div>
              <h4 className="font-semibold text-sm mb-2 text-slate-700">Request Arguments</h4>
              <pre className="bg-slate-900 text-slate-100 text-xs rounded-lg p-3 overflow-x-auto max-h-40">{JSON.stringify(call.request_args, null, 2)}</pre>
            </div>
          )}

          {call.events && call.events.length > 0 && (
            <div>
              <h4 className="font-semibold text-sm mb-3 text-slate-700">Call Flow</h4>
              <div className="relative">
                <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-200" />
                <div className="space-y-0">
                  {call.events.map((ev, i) => (
                    <div key={i} className="relative flex gap-4 pb-4">
                      <div className="relative z-10 flex items-center justify-center w-8 h-8 rounded-full bg-white border-2 border-slate-200 text-xs shrink-0">
                        {EVENT_ICONS[ev.type] || "●"}
                      </div>
                      <div className="min-w-0 flex-1 pt-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{EVENT_LABELS[ev.type] || ev.type}</span>
                          {ev.details?.duration_ms !== undefined && (
                            <span className="text-xs text-slate-400">({Number(ev.details.duration_ms).toFixed(0)}ms)</span>
                          )}
                        </div>
                        <p className="text-sm text-slate-700 mt-0.5">{ev.description}</p>
                        {ev.details && Object.keys(ev.details).length > 0 && Object.keys(ev.details).some(k => k !== "duration_ms" && k !== "success") && (
                          <pre className="mt-1 bg-slate-100 text-xs rounded p-2 overflow-x-auto max-h-24 text-slate-600">{JSON.stringify(Object.fromEntries(
                            Object.entries(ev.details).filter(([k]) => k !== "duration_ms" && k !== "success")
                          ), null, 2)}</pre>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {call.response_summary && (
            <div>
              <h4 className="font-semibold text-sm mb-2 text-slate-700">Response</h4>
              <pre className="bg-slate-900 text-slate-100 text-xs rounded-lg p-3 overflow-x-auto max-h-40">{call.response_summary}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Analytics() {
  const [stats, setStats] = useState<CallStats | null>(null);
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [selectedCall, setSelectedCall] = useState<CallDetail | null>(null);
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [allTools, setAllTools] = useState<Tool[]>([]);

  const [filterProxy, setFilterProxy] = useState("");
  const [filterTool, setFilterTool] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    analyticsApi.stats().then(setStats).catch(() => null);
    analyticsApi.calls({ limit: 50 }).then(setCalls).catch(() => null);
    proxiesApi.list().then(setProxies).catch(() => null);
    toolsApi.list().then(setAllTools).catch(() => null);
  }, []);

  const filtered = calls.filter((c) => {
    if (filterProxy && !c.trace_id?.includes(filterProxy) && c.proxy_id !== filterProxy) return false;
    if (filterTool && c.tool_name !== filterTool) return false;
    if (search && !c.tool_name.toLowerCase().includes(search.toLowerCase()) && !(c.error_message || "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Analytics</h2>

      {stats && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <p className="text-sm text-slate-500">Total Calls</p>
            <p className="text-2xl font-bold">{stats.total_calls}</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <p className="text-sm text-slate-500">Successful</p>
            <p className="text-2xl font-bold text-green-600">{stats.successful_calls}</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <p className="text-sm text-slate-500">Avg Latency</p>
            <p className="text-2xl font-bold">{stats.avg_latency_ms.toFixed(0)} ms</p>
          </div>
        </div>
      )}

      {stats && stats.top_tools.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-5 mb-6">
          <h3 className="font-semibold mb-4">Top Tools</h3>
          <div className="space-y-2">
            {stats.top_tools.map((t) => (
              <div key={t.name} className="flex items-center justify-between text-sm">
                <span>{t.name}</span>
                <span className="bg-slate-100 px-2 py-0.5 rounded-full text-xs font-medium">{t.count} calls</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <h3 className="font-semibold">Recent Calls</h3>
          <span className="text-xs text-slate-400">{filtered.length} of {calls.length}</span>
        </div>
        <div className="px-5 pb-3 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[180px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search tools..." className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm" />
          </div>
          <select value={filterProxy} onChange={(e) => setFilterProxy(e.target.value)} className="border rounded-lg px-3 py-2 text-sm bg-white min-w-[150px]">
            <option value="">All Proxies</option>
            {proxies.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select value={filterTool} onChange={(e) => setFilterTool(e.target.value)} className="border rounded-lg px-3 py-2 text-sm bg-white min-w-[150px]">
            <option value="">All Tools</option>
            {allTools.map((t) => <option key={t.id} value={t.name}>{t.name}</option>)}
          </select>
          {(search || filterProxy || filterTool) && (
            <button onClick={() => { setSearch(""); setFilterProxy(""); setFilterTool(""); }} className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1">
              <X size={14} /> Clear
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50 text-left">
                <th className="px-4 py-3 font-medium">Trace</th>
                <th className="px-4 py-3 font-medium">Tool</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Error</th>
                <th className="px-4 py-3 font-medium">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr
                  key={c.id}
                  className="border-b hover:bg-slate-50 cursor-pointer"
                  onClick={() => analyticsApi.callDetail(c.id).then(setSelectedCall).catch(() => null)}
                >
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded text-slate-500">
                      {c.trace_id ? c.trace_id.slice(0, 8) : "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-medium">{c.tool_name}</td>
                  <td className="px-4 py-3 text-slate-600">{c.duration_ms.toFixed(0)} ms</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${c.success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                      {c.success ? "Success" : "Failed"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs max-w-xs truncate">{c.error_message || "—"}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">{c.timestamp ? new Date(c.timestamp).toLocaleString() : "—"}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400">{calls.length === 0 ? "No tool calls recorded" : "No calls match filters."}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <TraceModal call={selectedCall} onClose={() => setSelectedCall(null)} />
    </div>
  );
}
