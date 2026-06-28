import { useEffect, useState, useRef } from "react";
import { Plus, Pencil, Trash2, Search, X, Upload, Download } from "lucide-react";
import { glossaryApi, type GlossaryTerm, type Domain } from "../api/client";
import Loading from "../components/Loading";

export default function Glossary() {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"domains" | "terms">("domains");

  const load = () => {
    Promise.all([
      glossaryApi.listTerms().then(setTerms),
      glossaryApi.listDomains().then(setDomains),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) return <Loading />;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Glossary</h2>
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setTab("domains")} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === "domains" ? "bg-blue-600 text-white" : "border hover:bg-slate-50"}`}>Domains</button>
        <button onClick={() => setTab("terms")} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === "terms" ? "bg-blue-600 text-white" : "border hover:bg-slate-50"}`}>Terms</button>
      </div>

      {tab === "domains" && <DomainsPanel domains={domains} onRefresh={load} />}
      {tab === "terms" && <TermsPanel terms={terms} domains={domains} onRefresh={load} />}
    </div>
  );
}

function TermsPanel({ terms, domains, onRefresh }: { terms: GlossaryTerm[]; domains: Domain[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [domainId, setDomainId] = useState("");
  const [term, setTerm] = useState("");
  const [definition, setDefinition] = useState("");
  const [search, setSearch] = useState("");
  const [filterDomain, setFilterDomain] = useState("");

  const openCreate = () => {
    setEditId(null);
    setDomainId("");
    setTerm("");
    setDefinition("");
    setShowForm(true);
  };

  const openEdit = (t: GlossaryTerm) => {
    setEditId(t.id);
    setDomainId(t.domain_id);
    setTerm(t.term);
    setDefinition(t.definition);
    setShowForm(true);
  };

  const save = async () => {
    if (!domainId || !term) return;
    if (editId) {
      await glossaryApi.updateTerm(editId, { domain_id: domainId, term, definition });
    } else {
      await glossaryApi.createTerm({ domain_id: domainId, term, definition });
    }
    setShowForm(false);
    setEditId(null);
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
        <button onClick={openCreate} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
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
          <h3 className="font-semibold mb-4">{editId ? "Edit Term" : "New Term"}</h3>
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
              <textarea value={definition} onChange={(e) => setDefinition(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm min-h-[60px]" placeholder="Application Programming Interface" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={!domainId || !term} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
              {editId ? "Update" : "Add"}
            </button>
            <button onClick={() => { setShowForm(false); setEditId(null); }} className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50">Cancel</button>
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
                  <th className="px-4 py-3 font-medium w-20" />
                </tr>
              </thead>
              <tbody>
                {groupTerms.map((t) => (
                  <tr key={t.id} className="border-b hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium">{t.term}</td>
                    <td className="px-4 py-3 text-slate-600">{t.definition}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <button onClick={() => openEdit(t)} className="p-1 hover:text-blue-600"><Pencil size={15} /></button>
                      <button onClick={() => remove(t.id)} className="p-1 hover:text-red-600 ml-1"><Trash2 size={15} /></button>
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
                  <th className="px-4 py-3 font-medium w-20" />
                </tr>
              </thead>
              <tbody>
                {ungrouped.map((t) => (
                  <tr key={t.id} className="border-b hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium">{t.term}</td>
                    <td className="px-4 py-3 text-slate-600">{t.definition}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <button onClick={() => openEdit(t)} className="p-1 hover:text-blue-600"><Pencil size={15} /></button>
                      <button onClick={() => remove(t.id)} className="p-1 hover:text-red-600 ml-1"><Trash2 size={15} /></button>
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

function DownloadTemplateButton() {
  const download = (format: "json" | "csv") => {
    if (format === "json") {
      const sample = [
        {
          domain: "development",
          description: "Software development tools",
          terms: [
            { term: "API", definition: "Application Programming Interface" },
            { term: "Git", definition: "Version control system" },
          ],
        },
      ];
      const blob = new Blob([JSON.stringify(sample, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "glossary-template.json"; a.click();
      URL.revokeObjectURL(url);
    } else {
      const sample = "domain,term,definition\r\ndevelopment,API,Application Programming Interface\r\ndevelopment,Git,Version control system\r\nsecurity,XSS,Cross-site scripting";
      const blob = new Blob([sample], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "glossary-template.csv"; a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="relative group">
      <button className="flex items-center gap-2 border border-slate-300 text-slate-600 px-4 py-2 rounded-lg text-sm hover:bg-slate-50">
        <Download size={16} /> Download Template
      </button>
      <div className="absolute right-0 top-full mt-1 bg-white border rounded-lg shadow-lg hidden group-hover:block z-10 min-w-[140px]">
        <button onClick={() => download("json")} className="block w-full text-left px-4 py-2 text-sm hover:bg-slate-50">JSON</button>
        <button onClick={() => download("csv")} className="block w-full text-left px-4 py-2 text-sm hover:bg-slate-50">CSV</button>
      </div>
    </div>
  );
}

function DomainsPanel({ domains, onRefresh }: { domains: Domain[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [search, setSearch] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);

  const openCreate = () => {
    setEditId(null);
    setName("");
    setDescription("");
    setShowForm(true);
  };

  const openEdit = (d: Domain) => {
    setEditId(d.id);
    setName(d.name);
    setDescription(d.description || "");
    setShowForm(true);
  };

  const save = async () => {
    if (!name) return;
    if (editId) {
      await glossaryApi.updateDomain(editId, { name, description });
    } else {
      await glossaryApi.createDomain({ name, description });
    }
    setShowForm(false);
    setEditId(null);
    setName("");
    setDescription("");
    onRefresh();
  };

  const remove = async (id: string) => {
    if (confirm("Delete this domain and all its terms?")) {
      await glossaryApi.deleteDomain(id);
      onRefresh();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportResult(null);
    try {
      const text = await file.text();
      let data: any[];
      if (file.name.endsWith(".json")) {
        data = JSON.parse(text);
      } else {
        const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
        if (lines.length < 2) throw new Error("CSV must have header row + data rows");
        const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
        const domainIdx = headers.indexOf("domain");
        const termIdx = headers.indexOf("term");
        const defIdx = headers.indexOf("definition");
        if (domainIdx < 0 || termIdx < 0) throw new Error("CSV must have 'domain' and 'term' columns");
        const domainMap: Record<string, any> = {};
        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(",").map((c) => c.trim());
          const dName = cols[domainIdx] || "General";
          if (!domainMap[dName]) domainMap[dName] = { domain: dName, description: "", terms: [] };
          domainMap[dName].terms.push({
            term: cols[termIdx],
            definition: defIdx >= 0 ? cols[defIdx] || "" : "",
          });
        }
        data = Object.values(domainMap);
      }
      if (!Array.isArray(data)) data = [data];
      const result = await glossaryApi.bulkImport({ items: data });
      setImportResult(`Created ${result.domains_created} domain(s) and ${result.terms_created} term(s)`);
      onRefresh();
    } catch (err) {
      setImportResult("Error: " + (err instanceof Error ? err.message : "Invalid file"));
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const filtered = domains.filter((d) => {
    if (search && !d.name.toLowerCase().includes(search.toLowerCase()) && !(d.description || "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <button onClick={openCreate} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          <Plus size={16} /> Add Domain
        </button>
        <button onClick={() => fileRef.current?.click()} disabled={importing} className="flex items-center gap-2 border border-blue-600 text-blue-600 px-4 py-2 rounded-lg text-sm hover:bg-blue-50">
          <Upload size={16} /> {importing ? "Importing..." : "Import JSON/CSV"}
        </button>
        <input ref={fileRef} type="file" accept=".json,.csv" onChange={handleFileUpload} className="hidden" />
        <DownloadTemplateButton />
        <div className="relative flex-1 max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search domains..." className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm" />
        </div>
        {search && (
          <button onClick={() => setSearch("")} className="text-xs text-blue-600 hover:text-blue-800">Clear</button>
        )}
      </div>

      {importResult && (
        <div className={`mb-4 px-4 py-2 rounded-lg text-sm ${importResult.startsWith("Error") ? "bg-red-50 text-red-700 border border-red-200" : "bg-green-50 text-green-700 border border-green-200"}`}>
          {importResult}
          <button onClick={() => setImportResult(null)} className="ml-2 font-bold">&times;</button>
        </div>
      )}

      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border p-5 mb-4">
          <h3 className="font-semibold mb-4">{editId ? "Edit Domain" : "New Domain"}</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Name <span className="text-red-500">*</span></label>
              <input value={name} onChange={(e) => setName(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="development" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm min-h-[60px]" placeholder="Tools for software development" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} disabled={!name} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
              {editId ? "Update" : "Add"}
            </button>
            <button onClick={() => { setShowForm(false); setEditId(null); }} className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid gap-3">
        {filtered.map((d) => (
          <div key={d.id} className="bg-white rounded-xl shadow-sm border p-4 flex items-center justify-between">
            <div>
              <h4 className="font-medium">{d.name}</h4>
              <p className="text-sm text-slate-500">{d.description}</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => openEdit(d)} className="p-1.5 hover:text-blue-600 hover:bg-slate-50 rounded"><Pencil size={16} /></button>
              <button onClick={() => remove(d.id)} className="p-1.5 hover:text-red-600 hover:bg-slate-50 rounded"><Trash2 size={16} /></button>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="text-center text-slate-400 py-8">{domains.length === 0 ? "No domains defined" : "No domains match filters."}</p>
        )}
      </div>
    </div>
  );
}