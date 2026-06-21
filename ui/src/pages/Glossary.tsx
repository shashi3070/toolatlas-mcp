import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
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
        <button onClick={() => setTab("terms")} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === "terms" ? "bg-slate-900 text-white" : "border hover:bg-slate-50"}`}>Terms</button>
        <button onClick={() => setTab("domains")} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === "domains" ? "bg-slate-900 text-white" : "border hover:bg-slate-50"}`}>Domains</button>
      </div>

      {tab === "terms" && <TermsPanel terms={terms} onRefresh={load} />}
      {tab === "domains" && <DomainsPanel domains={domains} onRefresh={load} />}
    </div>
  );
}

function TermsPanel({ terms, onRefresh }: { terms: GlossaryTerm[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [term, setTerm] = useState("");
  const [definition, setDefinition] = useState("");

  const save = async () => {
    await glossaryApi.createTerm({ term, definition });
    setShowForm(false);
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

  return (
    <div>
      <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-800 mb-4">
        <Plus size={16} /> Add Term
      </button>

      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border p-5 mb-4">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Term</label>
              <input value={term} onChange={(e) => setTerm(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="API" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Definition</label>
              <input value={definition} onChange={(e) => setDefinition(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Application Programming Interface" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} className="bg-slate-900 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-800">Add</button>
            <button onClick={() => setShowForm(false)} className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-slate-50 text-left">
              <th className="px-4 py-3 font-medium">Term</th>
              <th className="px-4 py-3 font-medium">Definition</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {terms.map((t) => (
              <tr key={t.id} className="border-b hover:bg-slate-50">
                <td className="px-4 py-3 font-medium">{t.term}</td>
                <td className="px-4 py-3 text-slate-600">{t.definition}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => remove(t.id)} className="p-1 hover:text-red-600"><Trash2 size={15} /></button>
                </td>
              </tr>
            ))}
            {terms.length === 0 && (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-slate-400">No terms defined</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DomainsPanel({ domains, onRefresh }: { domains: Domain[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const save = async () => {
    await glossaryApi.createDomain({ name, description });
    setShowForm(false);
    setName("");
    setDescription("");
    onRefresh();
  };

  return (
    <div>
      <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-800 mb-4">
        <Plus size={16} /> Add Domain
      </button>

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
            <button onClick={save} className="bg-slate-900 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-800">Add</button>
            <button onClick={() => setShowForm(false)} className="border px-4 py-2 rounded-lg text-sm hover:bg-slate-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid gap-3">
        {domains.map((d) => (
          <div key={d.id} className="bg-white rounded-xl shadow-sm border p-4">
            <h4 className="font-medium">{d.name}</h4>
            <p className="text-sm text-slate-500">{d.description}</p>
          </div>
        ))}
        {domains.length === 0 && (
          <p className="text-center text-slate-400 py-8">No domains defined</p>
        )}
      </div>
    </div>
  );
}
