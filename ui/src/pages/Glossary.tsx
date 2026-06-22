import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Search, X } from "lucide-react";
import { glossaryApi, type GlossaryTerm, type Domain } from "../api/client";

export default function Glossary() {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [tab, setTab] = useState<"terms" | "domains">("terms");

  const load = () => {
    glossaryApi.listTerms().then(setTerms);
    glossaryApi.listDomains().then(setDomains);
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Glossary</h2>
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setTab("terms")} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === "terms" ? "bg-blue-600 text-white" : "border hover:bg-slate-50"}`}>Terms</button>
        <button onClick={() => setTab("domains")} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === "domains" ? "bg-blue-600 text-white" : "border hover:bg-slate-50"}`}>Domains</button>
      </div>

      {tab === "terms" && <TermsPanel terms={terms} domains={domains} onRefresh={load} />}
      {tab === "domains" && <DomainsPanel domains={domains} onRefresh={load} />}
    </div>
  );
}

function TermsPanel({ terms, domains, onRefresh }: { terms: GlossaryTerm[]; domains: Domain[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [domainId, setDomainId] = useState("");
  const [term, setTerm] = useState("");
  const [definition, setDefinition] = useState("");
  const [search, setSearch] = useState("");
  const [filterDomain, setFilterDomain] = useState("");

  const save = async () => {
    if (!domainId) return;
    await glossaryApi.createTerm({ domain_id: domainId, term, definition });
    setShowForm(false);
    setDomainId("");
    setTerm("");
    setDefinition("");
    onRefresh();
  };

  const remove = async (id: string) => {
    if (confirm("Delete this term?")) {
      await glossaryApi.deleteTerm(id);
      onRefresh();
    }
  };

  const filtered = terms.filter((t) => {
    if (filterDomain && t.domain_id !== filterDomain) return false;
    if (search && !t.term.toLowerCase().includes(search.toLowerCase()) && !t.definition.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const grouped = domains.reduce((acc, d) => {
    const groupTerms = filtered.filter((t) => t.domain_id === d.id);
    if (groupTerms.length) acc.set(d.id, { domain: d, terms: groupTerms });
    return acc;
  }, new Map<string, { domain: Domain; terms: GlossaryTerm[] }>());

  const ungrouped = filtered.filter((t) => !domains.some((d) => d.id === t.domain_id));

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          <Plus size={16} /> Add Term
        </button>
        <div className="relative flex-1 min-w-[150px] max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search terms..." className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm" />
        </div>
        <select value={filterDomain} onChange={(e) => setFilterDomain(e.target.value)} className="border rounded-lg px-3 py-2 text-sm bg-white min-w-[130px]">
          <option value="">All Domains</option>
          {domains.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        {(search || filterDomain) && (
          <button onClick={() => { setSearch(""); setFilterDomain(""); }} className="text-xs text-blue-600 hover:text-blue-800">Clear</button>
        )}
      </div>

      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border p-5 mb-4">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Domain <span className="text-red-500">*</span></label>
              <select value={domainId} onChange={(e) => setDomainId(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm bg-white">
                <option value="">-- Select Domain --</option>
                {domains.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Term <span className="text-red-500">*</span></label>
              <input value={term} onChange={(e) => setTerm(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="API" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Definition</label>
              <input value={definition} onChange={(e) => setDefinition(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Application Programming Interface" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={!domainId || !term} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">Add</button>
            <button onClick={() => setShowForm(false)} className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {Array.from(grouped.entries()).map(([domainId, { domain, terms: groupTerms }]) => (
          <div key={domainId} className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="px-4 py-2 bg-blue-50 border-b text-sm font-semibold text-blue-800">{domain.name}</div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50 text-left">
                  <th className="px-4 py-3 font-medium">Term</th>
                  <th className="px-4 py-3 font-medium">Definition</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {groupTerms.map((t) => (
                  <tr key={t.id} className="border-b hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium">{t.term}</td>
                    <td className="px-4 py-3 text-slate-600">{t.definition}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => remove(t.id)} className="p-1 hover:text-red-600"><Trash2 size={15} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

        {ungrouped.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="px-4 py-2 bg-slate-50 border-b text-sm font-semibold text-slate-500">Ungrouped</div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50 text-left">
                  <th className="px-4 py-3 font-medium">Term</th>
                  <th className="px-4 py-3 font-medium">Definition</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {ungrouped.map((t) => (
                  <tr key={t.id} className="border-b hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium">{t.term}</td>
                    <td className="px-4 py-3 text-slate-600">{t.definition}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => remove(t.id)} className="p-1 hover:text-red-600"><Trash2 size={15} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {filtered.length === 0 && (
          <p className="text-center text-slate-400 py-8">{terms.length === 0 ? "No terms defined. Create a domain first, then add terms under it." : "No terms match filters."}</p>
        )}
      </div>
    </div>
  );
}

function DomainsPanel({ domains, onRefresh }: { domains: Domain[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [search, setSearch] = useState("");

  const save = async () => {
    await glossaryApi.createDomain({ name, description });
    setShowForm(false);
    setName("");
    setDescription("");
    onRefresh();
  };

  const filtered = domains.filter((d) => {
    if (search && !d.name.toLowerCase().includes(search.toLowerCase()) && !(d.description || "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          <Plus size={16} /> Add Domain
        </button>
        <div className="relative flex-1 max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search domains..." className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm" />
        </div>
        {search && (
          <button onClick={() => setSearch("")} className="text-xs text-blue-600 hover:text-blue-800">Clear</button>
        )}
      </div>

      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border p-5 mb-4">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="development" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
              <input value={description} onChange={(e) => setDescription(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Tools for software development" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">Add</button>
            <button onClick={() => setShowForm(false)} className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid gap-3">
        {filtered.map((d) => (
          <div key={d.id} className="bg-white rounded-xl shadow-sm border p-4">
            <h4 className="font-medium">{d.name}</h4>
            <p className="text-sm text-slate-500">{d.description}</p>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="text-center text-slate-400 py-8">{domains.length === 0 ? "No domains defined" : "No domains match filters."}</p>
        )}
      </div>
    </div>
  );
}