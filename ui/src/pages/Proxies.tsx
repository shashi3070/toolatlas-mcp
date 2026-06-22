import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2, ExternalLink, Search, X } from "lucide-react";
import { proxiesApi, type Proxy } from "../api/client";

export default function Proxies() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [search, setSearch] = useState("");

  const load = () => proxiesApi.list().then(setProxies);

  useEffect(() => { load(); }, []);

  const filtered = proxies.filter((p) => {
    if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && !p.slug.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const save = async () => {
    await proxiesApi.create({ name, slug, description });
    setShowForm(false);
    setName("");
    setSlug("");
    setDescription("");
    load();
  };

  const remove = async (id: string) => {
    if (confirm("Delete this proxy?")) {
      await proxiesApi.delete(id);
      load();
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Proxies</h2>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          <Plus size={16} /> Create Proxy
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border p-5 mb-6">
          <h3 className="font-semibold mb-4">New Proxy</h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Developer" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Slug</label>
              <input value={slug} onChange={(e) => setSlug(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="dev" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
              <input value={description} onChange={(e) => setDescription(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Tools for developers" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">Create</button>
            <button onClick={() => setShowForm(false)} className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border p-3 mb-4 flex items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search proxies..." className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm" />
        </div>
        {search && (
          <button onClick={() => setSearch("")} className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1">
            <X size={14} /> Clear
          </button>
        )}
        <span className="text-xs text-slate-400 ml-auto">{filtered.length} of {proxies.length}</span>
      </div>

      <div className="grid gap-4">
        {filtered.map((p) => (
          <div key={p.id} className="bg-white rounded-xl shadow-sm border p-5 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">{p.name}</h3>
                <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-mono">{p.slug}</span>
              </div>
              <p className="text-sm text-slate-500 mt-0.5">{p.description}</p>
            </div>
            <div className="flex items-center gap-2">
              <Link to={`/proxies/${p.id}`} className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
                Configure <ExternalLink size={14} />
              </Link>
              <button onClick={() => remove(p.id)} className="p-1 hover:text-red-600"><Trash2 size={15} /></button>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="text-center text-slate-400 py-8">{proxies.length === 0 ? "No proxies created yet" : "No proxies match filters."}</p>
        )}
      </div>
    </div>
  );
}
