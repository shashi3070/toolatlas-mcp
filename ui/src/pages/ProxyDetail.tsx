import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Link2, Unlink, ToggleLeft, ToggleRight, X, Search } from "lucide-react";
import { proxiesApi, serversApi, type Server, type Tool } from "../api/client";
import Loading from "../components/Loading";

export default function ProxyDetail() {
  const { id } = useParams<{ id: string }>();
  const [proxy, setProxy] = useState<any>(null);
  const [linked, setLinked] = useState<Server[]>([]);
  const [allServers, setAllServers] = useState<Server[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [showToolModal, setShowToolModal] = useState(false);
  const [selectedServerId, setSelectedServerId] = useState("");
  const [serverTools, setServerTools] = useState<Tool[]>([]);
  const [checkedTools, setCheckedTools] = useState<Set<string>>(new Set());
  const [toolSearch, setToolSearch] = useState("");

  const filteredTools = useMemo(
    () => serverTools.filter((t) => t.name.toLowerCase().includes(toolSearch.toLowerCase())),
    [serverTools, toolSearch],
  );

  const load = async () => {
    if (!id) return;
    const [p, ll, all, t] = await Promise.all([
      proxiesApi.get(id),
      proxiesApi.servers(id),
      serversApi.list(),
      proxiesApi.tools(id),
    ]);
    setProxy(p);
    setLinked(ll);
    setAllServers(all);
    setTools(t);
  };

  useEffect(() => { load(); }, [id]);

  const openToolModal = async (serverId: string) => {
    setSelectedServerId(serverId);
    const tools = await serversApi.discover(serverId);
    setServerTools(tools);
    setCheckedTools(new Set(tools.map((t) => t.id)));
    setToolSearch("");
    setShowToolModal(true);
  };

  const confirmLink = async () => {
    const names = serverTools.filter((t) => checkedTools.has(t.id)).map((t) => t.name);
    await proxiesApi.linkServer(id!, selectedServerId, names);
    setShowToolModal(false);
    load();
  };

  const unlinkServer = async (serverId: string) => {
    await proxiesApi.unlinkServer(id!, serverId);
    load();
  };

  const toggleTool = async (toolId: string, enabled: boolean) => {
    await proxiesApi.updateToolSetting(id!, toolId, { enabled });
    load();
  };

  const updateDescription = async (toolId: string, custom_description: string) => {
    await proxiesApi.updateToolSetting(id!, toolId, { custom_description });
    load();
  };

  const updateAlias = async (toolId: string, alias: string) => {
    await proxiesApi.updateToolSetting(id!, toolId, { alias });
    load();
  };

  if (!proxy) return <Loading />;

  const unlinked = allServers.filter((s) => !linked.find((l) => l.id === s.id));

  return (
    <div>
      <Link to="/proxies" className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-4">
        <ArrowLeft size={14} /> Back to Proxies
      </Link>

      <div className="mb-6">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-bold">{proxy.name}</h2>
          <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-mono">{proxy.slug}</span>
        </div>
        <p className="text-sm text-slate-500 mt-0.5">{proxy.description}</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><Link2 size={16} /> Linked Servers</h3>
          {linked.map((s) => (
            <div key={s.id} className="flex items-center justify-between py-2 border-b last:border-0">
              <span>{s.name}</span>
              <button onClick={() => unlinkServer(s.id)} className="text-sm text-red-600 hover:text-red-800 flex items-center gap-1">
                <Unlink size={14} /> Unlink
              </button>
            </div>
          ))}
          {linked.length === 0 && <p className="text-sm text-slate-400">No servers linked</p>}

          {unlinked.length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <label className="block text-sm font-medium text-slate-700 mb-2">Add Server</label>
              <div className="flex gap-2">
                <select id="serverSelect" className="flex-1 border rounded-lg px-3 py-2 text-sm" defaultValue="">
                  <option value="" disabled>Select server...</option>
                  {unlinked.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                <button onClick={() => {
                  const sel = document.getElementById("serverSelect") as HTMLSelectElement;
                  if (sel.value) openToolModal(sel.value);
                }} className="bg-blue-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-blue-700">Link</button>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><Link2 size={16} /> Stats</h3>
          <ProxyStats proxyId={id!} />
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-5 mt-6">
        <h3 className="font-semibold mb-4">Tools</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-slate-50 text-left">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Alias</th>
              <th className="px-4 py-3 font-medium">Server</th>
              <th className="px-4 py-3 font-medium">Description</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {tools.map((t) => (
              <tr key={t.id} className="border-b hover:bg-slate-50">
                <td className="px-4 py-3">
                  <div className="font-medium text-sm">{t.original_name}</div>
                  <div className="text-xs text-slate-400">{t.server_name}</div>
                </td>
                <td className="px-4 py-3">
                  <input
                    defaultValue={t.alias || ""}
                    placeholder="(same as name)"
                    onBlur={(e) => {
                      const val = e.target.value.trim();
                      if (val !== (t.alias || "")) updateAlias(t.id, val);
                    }}
                    className="w-full border-transparent hover:border-slate-200 focus:border-slate-300 rounded px-1 py-0.5 text-sm font-mono"
                  />
                </td>
                <td className="px-4 py-3 text-slate-600 text-sm">{t.server_name}</td>
                <td className="px-4 py-3 text-slate-600 max-w-xs truncate">
                  <input
                    defaultValue={t.description}
                    onBlur={(e) => {
                      if (e.target.value !== t.description) updateDescription(t.id, e.target.value);
                    }}
                    className="w-full border-transparent hover:border-slate-200 focus:border-slate-300 rounded px-1 py-0.5 text-sm"
                  />
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${t.enabled ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {t.enabled ? "Enabled" : "Disabled"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => toggleTool(t.id, !t.enabled)} className="text-sm text-slate-500 hover:text-slate-700">
                    {t.enabled ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
                  </button>
                </td>
              </tr>
            ))}
            {tools.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400">No tools available</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {showToolModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h3 className="font-semibold">Select tools from {allServers.find((s) => s.id === selectedServerId)?.name}</h3>
              <button onClick={() => setShowToolModal(false)} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
            </div>

            <div className="px-6 pt-4 pb-2 flex items-center gap-2">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search tools..."
                  value={toolSearch}
                  onChange={(e) => setToolSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={() => setCheckedTools(new Set(filteredTools.map((t) => t.id)))}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                Select All
              </button>
              <button
                onClick={() => setCheckedTools(new Set())}
                className="text-xs text-slate-500 hover:text-slate-700 font-medium"
              >
                Deselect All
              </button>
            </div>

            <div className="px-6 pb-1 text-xs text-slate-400">
              {checkedTools.size} of {serverTools.length} tools selected
              {toolSearch && filteredTools.length < serverTools.length && ` (${filteredTools.length} matching)`}
            </div>

            <div className="px-6 py-2 overflow-y-auto flex-1 space-y-1">
              {filteredTools.map((t) => (
                <label key={t.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checkedTools.has(t.id)}
                    onChange={(e) => {
                      const next = new Set(checkedTools);
                      e.target.checked ? next.add(t.id) : next.delete(t.id);
                      setCheckedTools(next);
                    }}
                    className="rounded border-slate-300"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium">{t.name}</div>
                    <div className="text-xs text-slate-500 truncate">{t.description}</div>
                  </div>
                </label>
              ))}
              {filteredTools.length === 0 && (
                <p className="text-sm text-slate-400 text-center py-4">No tools match your search</p>
              )}
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t">
              <button onClick={() => setShowToolModal(false)} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800">Cancel</button>
              <button onClick={confirmLink} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Link ({checkedTools.size} tool{checkedTools.size !== 1 ? "s" : ""})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ProxyStats({ proxyId }: { proxyId: string }) {
  const [stats, setStats] = useState<any>(null);
  useEffect(() => {
    proxiesApi.stats(proxyId).then(setStats).catch(() => setStats(null));
  }, [proxyId]);

  if (!stats) return <p className="text-sm text-slate-400">No data yet</p>;

  return (
    <div className="space-y-3">
      <div className="flex justify-between text-sm"><span className="text-slate-500">Total calls</span><span className="font-medium">{stats.total_calls}</span></div>
      <div className="flex justify-between text-sm"><span className="text-slate-500">Successful</span><span className="font-medium text-green-600">{stats.successful_calls}</span></div>
      <div className="flex justify-between text-sm"><span className="text-slate-500">Avg latency</span><span className="font-medium">{stats.avg_latency_ms.toFixed(0)} ms</span></div>
    </div>
  );
}
