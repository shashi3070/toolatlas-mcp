import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Server } from "lucide-react";
import { toolsApi, glossaryApi, type Tool, type Domain, type GlossaryTerm } from "../api/client";

export default function ToolDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [tool, setTool] = useState<Tool | null>(null);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [description, setDescription] = useState("");
  const [domainsSelected, setDomainsSelected] = useState<string[]>([]);
  const [tags, setTags] = useState("");
  const [glossaryTermId, setGlossaryTermId] = useState("");

  useEffect(() => {
    if (!id) return;
    Promise.all([
      toolsApi.get(id),
      glossaryApi.listDomains().catch(() => []),
      glossaryApi.listTerms().catch(() => []),
    ]).then(([t, d, terms]) => {
      setTool(t);
      setDomains(d);
      setTerms(terms);
      setDescription(t.description || "");
      setDomainsSelected(t.domain || []);
      setTags((t.tags || []).join(", "));
      setGlossaryTermId(t.glossary_term_id || "");
      setLoading(false);
    });
  }, [id]);

  const handleSave = async () => {
    if (!tool) return;
    setSaving(true);
    try {
      const updated = await toolsApi.update(tool.id, {
        description,
        domain: domainsSelected.length ? domainsSelected : undefined,
        tags: tags ? tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
        glossary_term_id: glossaryTermId || undefined,
      });
      setTool(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      alert("Failed to save: " + (e instanceof Error ? e.message : e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-slate-400 text-center py-12">Loading...</div>;
  }

  if (!tool) {
    return <div className="text-red-500 text-center py-12">Tool not found</div>;
  }

  const hasCustomDesc = tool.original_description && tool.original_description !== description;

  const selectedTerm = terms.find((t) => t.id === glossaryTermId);
  const enrichmentLines: string[] = [];
  const tagList = tags.split(",").map((t) => t.trim()).filter(Boolean);
  if (tagList.length) enrichmentLines.push(`Tags: ${tagList.join(", ")}`);
  if (domainsSelected.length) enrichmentLines.push(`Domain: ${domainsSelected.join(", ")}`);
  if (selectedTerm) enrichmentLines.push(`Glossary: ${selectedTerm.definition || selectedTerm.term}`);
  const clientPreview = (description || tool.original_description) +
    (enrichmentLines.length ? "\n" + enrichmentLines.join("\n") : "");

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Link to="/tools" className="p-1.5 hover:bg-slate-100 rounded-lg">
          <ArrowLeft size={20} className="text-slate-500" />
        </Link>
        <div>
          <h2 className="text-2xl font-bold">{tool.name}</h2>
          <p className="text-sm text-slate-500 flex items-center gap-1 mt-0.5">
            <Server size={14} /> {tool.server_name || tool.server_id}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-5">
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <h3 className="font-semibold mb-3">Description</h3>
            {tool.original_description && (
              <div className="mb-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Original (from server)</p>
                <p className="text-sm text-slate-600">{tool.original_description}</p>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Custom Description {hasCustomDesc && <span className="text-amber-600 text-xs">(overridden)</span>}
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm min-h-[100px]"
              />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-5">
            <h3 className="font-semibold mb-3">Input Schema</h3>
            <pre className="bg-slate-900 text-slate-100 text-xs rounded-lg p-3 overflow-x-auto max-h-60">
              {JSON.stringify(tool.input_schema, null, 2)}
            </pre>
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-5 border-blue-200">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <span className="w-2 h-2 bg-blue-500 rounded-full" />
              Client Preview
            </h3>
            <p className="text-xs text-slate-500 mb-2">What the client sees when listing tools</p>
            <pre className="bg-blue-50 text-slate-800 text-xs rounded-lg p-3 overflow-x-auto whitespace-pre-wrap max-h-96">
{JSON.stringify({
  name: tool.name,
  description: clientPreview || tool.description,
  inputSchema: tool.input_schema,
  server: tool.server_name,
  enabled: tool.enabled,
}, null, 2)}
            </pre>
          </div>
        </div>

        <div className="space-y-5">
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <h3 className="font-semibold mb-4">Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Domain</label>
                <div className="space-y-1.5 mt-1 max-h-40 overflow-y-auto border rounded-lg p-2">
                  {domains.length === 0 && (
                    <p className="text-xs text-slate-400">No domains configured</p>
                  )}
                  {domains.map((d) => (
                    <label key={d.id} className="flex items-center gap-2 text-sm cursor-pointer hover:text-slate-900">
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
                <input
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  placeholder="git, code, search"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Glossary Term</label>
                <select
                  value={glossaryTermId}
                  onChange={(e) => setGlossaryTermId(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                >
                  <option value="">-- None --</option>
                  {terms.map((t) => (
                    <option key={t.id} value={t.id}>{t.term}</option>
                  ))}
                </select>
                {tool.glossary_term_id && (
                  <p className="text-xs text-slate-400 mt-1">Linked glossary term enriches this tool's description</p>
                )}
              </div>

              <div className="flex items-center gap-2 pt-2 border-t">
                <label className="text-sm font-medium text-slate-700">Enabled</label>
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${tool.enabled ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                  {tool.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full bg-slate-900 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
          >
            {saving ? "Saving..." : saved ? "Saved ✓" : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
