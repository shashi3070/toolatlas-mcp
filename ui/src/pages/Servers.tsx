import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Wifi, RefreshCw, CheckCircle, XCircle } from "lucide-react";
import { serversApi, type Server, type Tool } from "../api/client";

export default function Servers() {
  const [servers, setServers] = useState<Server[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Server | null>(null);
  const [name, setName] = useState("");
  const [transport, setTransport] = useState("sse");
  const [url, setUrl] = useState("");

  const [discovering, setDiscovering] = useState(false);
  const [discoverError, setDiscoverError] = useState("");
  const [previewTools, setPreviewTools] = useState<{ name: string; description: string }[] | null>(null);

  const [saving, setSaving] = useState(false);
  const [discoveringId, setDiscoveringId] = useState<string | null>(null);
  const [discoveredTools, setDiscoveredTools] = useState<Record<string, Tool[]>>({});

  const load = () => serversApi.list().then(setServers);

  useEffect(() => { load(); }, []);

  const openNew = () => {
    setEditing(null);
    setName("");
    setTransport("sse");
    setUrl("");
    setPreviewTools(null);
    setDiscoverError("");
    setShowForm(true);
  };

  const openEdit = (s: Server) => {
    setEditing(s);
    setName(s.name);
    setTransport(s.transport);
    setUrl(s.url || "");
    setPreviewTools(null);
    setDiscoverError("");
    setShowForm(true);
  };

  const handleDiscover = async () => {
    setDiscovering(true);
    setDiscoverError("");
    setPreviewTools(null);
    try {
      const tools = await serversApi.discoverPreview({ transport, url });
      setPreviewTools(tools);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e.message;
      setDiscoverError(msg);
    } finally {
      setDiscovering(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      let server: Server;
      if (editing) {
        server = await serversApi.update(editing.id, { name, transport, url });
      } else {
        server = await serversApi.create({ name, transport, url });
      }
      const tools = await serversApi.discover(server.id);
      setDiscoveredTools((prev) => ({ ...prev, [server.id]: tools }));
      setShowForm(false);
      load();
    } catch (e: any) {
      alert("Save failed: " + (e?.response?.data?.detail || e.message));
    } finally {
      setSaving(false);
    }
  };

  const handleDiscoverExisting = async (s: Server) => {
    setDiscoveringId(s.id);
    try {
      const tools = await serversApi.discover(s.id);
      setDiscoveredTools((prev) => ({ ...prev, [s.id]: tools }));
    } catch (e: any) {
      alert("Discovery failed: " + (e?.response?.data?.detail || e.message));
    } finally {
      setDiscoveringId(null);
    }
  };

  const remove = async (id: string) => {
    if (confirm("Delete this server?")) {
      await serversApi.delete(id);
      const updated: Record<string, Tool[]> = { ...discoveredTools };
      delete updated[id];
      setDiscoveredTools(updated);
      load();
    }
  };

  const canSave = previewTools !== null && !discovering;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Servers</h2>
        <button onClick={openNew} className="flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-800">
          <Plus size={16} /> Add Server
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border p-5 mb-6">
          <h3 className="font-semibold mb-4">{editing ? "Edit Server" : "Add Server"}</h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="GitHub" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Transport</label>
              <select value={transport} onChange={(e) => { setTransport(e.target.value); setPreviewTools(null); setDiscoverError(""); }} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="sse">SSE</option>
                <option value="streamable-http">Streamable HTTP</option>
                <option value="stdio">STDIO</option>
              </select>
            </div>
            {(transport === "sse" || transport === "streamable-http") && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">URL</label>
                <input value={url} onChange={(e) => { setUrl(e.target.value); setPreviewTools(null); setDiscoverError(""); }} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="http://127.0.0.1:9001" />
              </div>
            )}
            {transport === "stdio" && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Command</label>
                <input value={url} onChange={(e) => { setUrl(e.target.value); setPreviewTools(null); setDiscoverError(""); }} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="npx -y @modelcontextprotocol/server-github" />
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 mb-4">
            <button
              onClick={handleDiscover}
              disabled={discovering}
              className="flex items-center gap-2 border border-slate-300 px-4 py-2 rounded-lg text-sm hover:bg-slate-50 disabled:opacity-50"
            >
              <Wifi size={16} />
              {discovering ? "Testing..." : "Discover"}
            </button>

            <button
              onClick={handleSave}
              disabled={!canSave || saving}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                canSave
                  ? "bg-slate-900 text-white hover:bg-slate-800"
                  : "bg-slate-200 text-slate-400 cursor-not-allowed"
              }`}
            >
              {saving ? "Saving..." : editing ? "Update" : "Save"}
            </button>

            <button onClick={() => setShowForm(false)} className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50">Cancel</button>
          </div>

          {discovering && (
            <p className="text-sm text-slate-400">Connecting to {url}...</p>
          )}

          {discoverError && (
            <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
              <XCircle size={16} />
              {discoverError}
            </div>
          )}

          {previewTools !== null && !discoverError && (
            <div>
              <div className="flex items-center gap-2 text-sm text-green-600 mb-2">
                <CheckCircle size={16} />
                Connected — {previewTools.length} tool{previewTools.length !== 1 ? "s" : ""} found
              </div>
              <div className="flex flex-wrap gap-2">
                {previewTools.map((t) => (
                  <span
                    key={t.name}
                    className="inline-flex items-center gap-1 bg-green-50 border border-green-200 rounded-full px-3 py-1 text-xs font-medium text-green-700"
                    title={t.description}
                  >
                    {t.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="space-y-4">
        {servers.map((s) => (
          <div key={s.id} className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div>
                  <span className="font-semibold">{s.name}</span>
                  <span className="text-xs text-slate-400 ml-2 font-mono">{s.transport}</span>
                  <span className="text-xs text-slate-400 ml-2 font-mono">{s.url || s.command}</span>
                </div>
                <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${s.enabled ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                  {s.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDiscoverExisting(s)}
                  disabled={discoveringId === s.id}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 disabled:text-slate-300"
                >
                  <Wifi size={14} />
                  {discoveringId === s.id ? "Discovering..." : "Discover"}
                </button>
                <button onClick={() => openEdit(s)} className="p-1 hover:text-blue-600"><Pencil size={15} /></button>
                <button onClick={() => remove(s.id)} className="p-1 hover:text-red-600"><Trash2 size={15} /></button>
              </div>
            </div>

            {discoveredTools[s.id] && discoveredTools[s.id].length > 0 && (
              <div className="border-t bg-slate-50 px-4 py-3">
                <div className="flex items-center gap-1 text-xs text-slate-500 mb-2">
                  <RefreshCw size={12} />
                  {discoveredTools[s.id].length} tool{discoveredTools[s.id].length !== 1 ? "s" : ""}
                </div>
                <div className="flex flex-wrap gap-2">
                  {discoveredTools[s.id].map((t) => (
                    <span
                      key={t.id}
                      className="inline-flex items-center gap-1 bg-white border rounded-full px-3 py-1 text-xs font-medium text-slate-700"
                      title={t.description}
                    >
                      {t.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {discoveringId === s.id && (
              <div className="border-t bg-slate-50 px-4 py-3 text-sm text-slate-400">
                Connecting to {s.url || s.command}...
              </div>
            )}
          </div>
        ))}

        {servers.length === 0 && (
          <p className="text-center text-slate-400 py-8">No servers registered. Click "Add Server" to begin.</p>
        )}
      </div>
    </div>
  );
}
