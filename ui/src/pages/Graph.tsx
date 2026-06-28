import { useEffect, useRef, useState } from "react";
import { Network } from "vis-network";
import { Share2, GitBranch, Filter } from "lucide-react";
import {
  graphApi, proxiesApi,
  type TraceSummary, type TraceGraphResponse, type CoOccurrenceResponse, type Proxy,
} from "../api/client";
import Loading from "../components/Loading";

type Tab = "flow" | "relationships" | "topology";

const tabs: { key: Tab; label: string; icon: typeof Share2 }[] = [
  { key: "flow", label: "Call Flow", icon: GitBranch },
  { key: "relationships", label: "Relationships", icon: Share2 },
  { key: "topology", label: "Topology", icon: Share2 },
];

export default function Graph() {
  const [activeTab, setActiveTab] = useState<Tab>("flow");
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<TraceGraphResponse | null>(null);
  const [cooc, setCooc] = useState<CoOccurrenceResponse | null>(null);
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterProxy, setFilterProxy] = useState("");

  const networkRef = useRef<HTMLDivElement>(null);
  const networkInstance = useRef<Network | null>(null);

  useEffect(() => {
    proxiesApi.list().then(setProxies).catch(() => null).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (activeTab === "flow") {
      graphApi.traces({ proxy_id: filterProxy || undefined }).then(setTraces).catch(() => null);
    } else if (activeTab === "relationships") {
      graphApi.coOccurrence({ proxy_id: filterProxy || undefined, min_count: 2 }).then(setCooc).catch(() => null);
    }
  }, [activeTab, filterProxy]);

  useEffect(() => {
    if (!networkRef.current) return;
    networkInstance.current?.destroy();

    if (activeTab === "flow" && selectedTrace) {
      renderFlowGraph(selectedTrace);
    } else if (activeTab === "relationships" && cooc) {
      renderCoOccurrenceGraph(cooc);
    } else if (activeTab === "topology") {
      renderTopologyGraph();
    }

    return () => { networkInstance.current?.destroy(); };
  }, [activeTab, selectedTrace, cooc]);

  function renderFlowGraph(trace: TraceGraphResponse) {
    if (!networkRef.current) return;
    const nodes = trace.nodes.map((n) => ({
      id: n.id,
      label: `${n.tool_name}\n${n.duration_ms.toFixed(0)}ms`,
      color: n.success ? "#dbeafe" : "#fecaca",
      shape: "box",
      font: { size: 12 },
      borderWidth: 2,
      borderColor: n.success ? "#3b82f6" : "#ef4444",
    }));
    const edges = trace.edges.map((e) => ({
      from: e.source,
      to: e.target,
      label: e.label || "",
      arrows: "to",
      font: { size: 10, align: "middle" },
    }));
    networkInstance.current = new Network(networkRef.current, { nodes, edges }, {
      layout: { hierarchical: { direction: "LR", sortMethod: "directed" } },
      physics: { enabled: false },
      edges: { smooth: { enabled: true, type: "curvedCW", roundness: 0.2 } },
    } as any);
  }

  function renderCoOccurrenceGraph(data: CoOccurrenceResponse) {
    if (!networkRef.current) return;
    const maxCount = Math.max(...data.nodes.map((n) => n.call_count), 1);
    const nodes = data.nodes.map((n) => ({
      id: n.id,
      label: `${n.tool_name} (${n.call_count})`,
      value: n.call_count,
      color: "#e0f2fe",
      font: { size: Math.max(10, Math.min(24, 10 + (n.call_count / maxCount) * 14)) },
    }));
    const maxWeight = Math.max(...data.edges.map((e) => e.weight), 1);
    const edges = data.edges.map((e) => ({
      from: e.source,
      to: e.target,
      value: e.weight,
      width: Math.max(1, (e.weight / maxWeight) * 6),
      title: `${e.weight} co-occurrences`,
    }));
    networkInstance.current = new Network(networkRef.current, { nodes, edges }, {
      physics: { solver: "forceAtlas2Based", forceAtlas2Based: { gravitationalConstant: -40 } as any },
      edges: { smooth: { enabled: true, type: "continuous", roundness: 0.2 } },
    } as any);
  }

  async function renderTopologyGraph() {
    if (!networkRef.current) return;
    const data = await graphApi.full();
    const typeColors: Record<string, string> = {
      proxy: "#e0f2fe",
      server: "#dcfce7",
      tool: "#fef3c7",
    };
    const typeShapes: Record<string, string> = {
      proxy: "hexagon",
      server: "box",
      tool: "ellipse",
    };
    const nodes = data.nodes.map((n) => ({
      id: n.id,
      label: n.name,
      color: typeColors[n.type] || "#f1f5f9",
      shape: typeShapes[n.type] || "dot",
      font: { size: n.type === "tool" ? 10 : 13 },
    }));
    const edges = data.edges.map((e) => ({
      from: e.source,
      to: e.target,
      label: e.type,
      arrows: "to",
      font: { size: 9, align: "middle" },
      dashes: e.type === "contains",
    }));
    networkInstance.current = new Network(networkRef.current, { nodes, edges }, {
      physics: { solver: "barnesHut", barnesHut: { gravitationalConstant: -2000 } as any },
      edges: { smooth: { enabled: true, type: "continuous", roundness: 0.2 } },
    } as any);
  }

  if (loading) return <Loading />;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Tool Graph</h2>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1 w-fit">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => { setActiveTab(key); setSelectedTrace(null); }}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === key ? "bg-white shadow-sm text-blue-700" : "text-slate-600 hover:text-slate-800"
            }`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {/* Filters */}
      {(activeTab === "flow" || activeTab === "relationships") && (
        <div className="flex items-center gap-3 mb-4">
          <Filter size={16} className="text-slate-400" />
          <select
            value={filterProxy}
            onChange={(e) => setFilterProxy(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm bg-white min-w-[180px]"
          >
            <option value="">All Proxies</option>
            {proxies.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
      )}

      {/* Tab Content */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left / Top: Graph canvas */}
        <div className="xl:col-span-2 bg-white rounded-xl shadow-sm border">
          <div ref={networkRef} className="w-full h-[500px] rounded-xl" />
          {activeTab === "flow" && !selectedTrace && (
            <div className="flex items-center justify-center h-[500px] text-slate-400">
              Select a trace from the list to view its call flow
            </div>
          )}
        </div>

        {/* Right / Bottom: Side panel */}
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          {activeTab === "flow" && (
            <div>
              <div className="px-4 py-3 border-b bg-slate-50">
                <h3 className="font-semibold text-sm">Traces</h3>
              </div>
              <div className="divide-y max-h-[500px] overflow-y-auto">
                {traces.length === 0 && (
                  <p className="p-4 text-sm text-slate-400 text-center">No traces recorded yet</p>
                )}
                {traces.map((t) => (
                  <button
                    key={t.trace_id}
                    onClick={() => graphApi.traceDetail(t.trace_id).then(setSelectedTrace).catch(() => null)}
                    className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors ${
                      selectedTrace?.trace_id === t.trace_id ? "bg-blue-50" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded text-slate-500">
                        {t.trace_id.slice(0, 8)}
                      </span>
                      <span className={`text-xs font-medium ${t.success_rate === 100 ? "text-green-600" : "text-amber-600"}`}>
                        {t.success_rate}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span>{t.tool_count} calls</span>
                      <span>·</span>
                      <span>{t.total_duration_ms.toFixed(0)}ms</span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {t.tool_names.slice(0, 4).map((name) => (
                        <span key={name} className="text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                          {name}
                        </span>
                      ))}
                      {t.tool_names.length > 4 && (
                        <span className="text-xs text-slate-400">+{t.tool_names.length - 4}</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeTab === "relationships" && (
            <div className="p-4">
              <h3 className="font-semibold text-sm mb-3">Tool Pairs</h3>
              {!cooc || cooc.edges.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-8">No co-occurrence data yet.<br/>Make tool calls to see relationships.</p>
              ) : (
                <div className="space-y-2 max-h-[450px] overflow-y-auto">
                  {cooc.edges.slice(0, 30).map((e) => (
                    <div key={`${e.source}-${e.target}`} className="flex items-center justify-between text-sm bg-slate-50 rounded-lg px-3 py-2">
                      <span>
                        <span className="font-medium">{e.source}</span>
                        <span className="text-slate-300 mx-1">↔</span>
                        <span className="font-medium">{e.target}</span>
                      </span>
                      <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full font-medium">{e.weight}x</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === "topology" && (
            <div className="p-4">
              <h3 className="font-semibold text-sm mb-3">Legend</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-full bg-blue-200 border border-blue-500" />
                  <span>Proxy</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-sm bg-green-200 border border-green-500" />
                  <span>Server</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-full bg-amber-200 border border-amber-500" />
                  <span>Tool</span>
                </div>
                <hr className="my-3" />
                <p className="text-xs text-slate-400">Dashed edges = proxy→server<br/>Solid edges = server→tool</p>
                <p className="text-xs text-slate-400 mt-2">Drag to pan · Scroll to zoom · Click a node to select</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Trace detail bar */}
      {selectedTrace && activeTab === "flow" && (
        <div className="mt-4 bg-white rounded-xl shadow-sm border p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">
              Trace <span className="font-mono text-sm bg-slate-100 px-2 py-0.5 rounded">{selectedTrace.trace_id.slice(0, 12)}</span>
            </h3>
            <button onClick={() => setSelectedTrace(null)} className="text-sm text-blue-600 hover:text-blue-800">
              Close
            </button>
          </div>
          <div className="flex gap-6 text-sm">
            <div><span className="text-slate-500">Tools:</span> <span className="font-medium">{selectedTrace.tool_count}</span></div>
            <div><span className="text-slate-500">Total:</span> <span className="font-medium">{selectedTrace.total_duration_ms.toFixed(0)}ms</span></div>
            <div>
              <span className="text-slate-500">Nodes:</span>
              <span className="font-medium ml-1">
                {selectedTrace.nodes.filter((n) => n.success).length}/{selectedTrace.nodes.length} successful
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}