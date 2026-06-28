import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Pencil, Search, X } from "lucide-react";
import { toolsApi, glossaryApi, serversApi, type Tool, type Domain, type Server } from "../api/client";
import Loading from "../components/Loading";

export default function Tools() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [servers, setServers] = useState<Server[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [filterServer, setFilterServer] = useState("");
  const [filterDomain, setFilterDomain] = useState("");
  const [search, setSearch] = useState("");

  const load = () => Promise.all([
    toolsApi.list(),
    serversApi.list(),
    glossaryApi.listDomains().catch(() => []),
  ]).then(([t, s, d]) => { setTools(t); setServers(s); setDomains(d); }).finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const update = async (id: string, data: Partial<Tool>) => {
    await toolsApi.update(id, data);
    load();
  };

  if (loading) return <Loading />;

  const filtered = tools.filter((t) => {
    if (filterServer && t.server_id !== filterServer) return false;
    if (filterDomain && !(t.domain || []).includes(filterDomain)) return false;
    if (search) {
      const s = search.toLowerCase();
      if (!t.name.toLowerCase().includes(s) && !t.description.toLowerCase().includes(s)) return false;
    }
    return true;
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Tools</h2>
        <span className="text-sm text-slate-400">{filtered.length} of {tools.length} tools</span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-3 mb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tools..."
            className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm"
          />
        </div>
        <select
          value={filterServer}
          onChange={(e) => setFilterServer(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm bg-white min-w-[150px]"
        >
          <option value="">All Servers</option>
          {servers.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <select
          value={filterDomain}
          onChange={(e) => setFilterDomain(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm bg-white min-w-[150px]"
        >
          <option value="">All Domains</option>
          {domains.map((d) => (
            <option key={d.id} value={d.name}>{d.name}</option>
          ))}
        </select>
        {(filterServer || filterDomain || search) && (
          <button onClick={() => { setFilterServer(""); setFilterDomain(""); setSearch(""); }} className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1">
            <X size={14} /> Clear
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-blue-50 text-left">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Server</th>
              <th className="px-4 py-3 font-medium">Description</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Tags</th>
              <th className="px-4 py-3 font-medium">Domain</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.id} className="border-b hover:bg-slate-50">
                <td className="px-4 py-3">
                  <Link to={`/tools/${t.id}`} className="font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1">
                    {t.name} <ExternalLink size={12} />
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-600">{t.server_name}</td>
                <td className="px-4 py-3 text-slate-600 max-w-xs truncate">
                  {t.description}
                  {t.original_description && t.original_description !== t.description && (
                    <span className="ml-1.5 text-amber-500 text-xs">(edited)</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${t.enabled ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {t.enabled ? "Enabled" : "Disabled"}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600">{t.tags?.join(", ") || "—"}</td>
                <td className="px-4 py-3 text-slate-600">{t.domain?.length ? t.domain.join(", ") : "—"}</td>
                <td className="px-4 py-3 text-right">
                  <ToolEditDialog tool={t} onSave={(data) => update(t.id, data)} />
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-400">No tools match filters</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ToolEditDialog({ tool, onSave }: { tool: Tool; onSave: (data: Partial<Tool>) => void }) {
  const [open, setOpen] = useState(false);
  const [description, setDescription] = useState(tool.description);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [domainsSelected, setDomainsSelected] = useState<string[]>([]);
  const [tags, setTags] = useState(tool.tags?.join(", ") || "");
  const [enabled, setEnabled] = useState(tool.enabled);

  useEffect(() => {
    setDescription(tool.description);
    setDomainsSelected(tool.domain || []);
    setTags(tool.tags?.join(", ") || "");
    setEnabled(tool.enabled);
    glossaryApi.listDomains().then(setDomains).catch(() => {});
  }, [tool]);

  const save = () => {
    onSave({
      description,
      domain: domainsSelected.length ? domainsSelected : undefined,
      tags: tags ? tags.split(",").map((t) => t.trim()).filter(Boolean) : undefined,
      enabled,
    });
    setOpen(false);
  };

  return (
    <>
      <button onClick={() => setOpen(true)} className="p-1 hover:text-blue-600"><Pencil size={15} /></button>
      {open && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setOpen(false)}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold mb-4">Edit Tool: {tool.name}</h3>
            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" rows={3} />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Domain</label>
                <div className="space-y-1 mt-1 max-h-32 overflow-y-auto border rounded-lg p-2">
                  {domains.length === 0 && (
                    <p className="text-xs text-slate-400">No domains configured</p>
                  )}
                  {domains.map((d) => (
                    <label key={d.id} className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={domainsSelected.includes(d.name)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setDomainsSelected([...domainsSelected, d.name]);
                          } else {
                            setDomainsSelected(domainsSelected.filter((n) => n !== d.name));
                          }
                        }}
                        className="rounded border-slate-300"
                      />
                      {d.name}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tags (comma separated)</label>
                <input value={tags} onChange={(e) => setTags(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="git, code, search" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="enabled" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="rounded" />
                <label htmlFor="enabled" className="text-sm">Enabled</label>
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={save} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">Save</button>
              <button onClick={() => setOpen(false)} className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
