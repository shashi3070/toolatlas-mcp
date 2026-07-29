import axios from "axios";

declare global {
  interface Window {
    __TOOLATLAS_BASE_PATH__?: string;
  }
}
const basePath = window.__TOOLATLAS_BASE_PATH__ || import.meta.env.VITE_BASE_PATH || "";
const api = axios.create({ baseURL: `${basePath}/api` });

export type Server = {
  id: string;
  name: string;
  transport: string;
  command?: string;
  url?: string;
  enabled: boolean;
  connection_status: string;
  latency_ms?: number;
  reconnect_count: number;
  last_heartbeat?: string;
  last_tool_sync?: string;
  headers?: Record<string, string>;
  created_at?: string;
  updated_at?: string;
};

export type DashboardSummary = {
  servers: { total: number; connected: number; disconnected: number; unknown: number; total_tools: number };
  proxies: { total: number };
  tools: { total: number };
  calls: { per_minute: number; total: number };
  latency: { avg_ms: number };
  cache: { hit_rate: number; entries: number };
  recent_alerts: unknown[];
  recent_activity: unknown[];
};

export type SearchResults = {
  servers: Server[];
  tools: Tool[];
  proxies: Proxy[];
  glossary_terms: GlossaryTerm[];
};

export type GraphData = {
  nodes: { id: string; type: string; name: string; status?: string }[];
  edges: { source: string; target: string; type: string }[];
};

export type Tool = {
  id: string;
  server_id: string;
  name: string;
  original_name: string;
  original_description?: string;
  description: string;
  input_schema: Record<string, unknown>;
  enabled: boolean;
  tags: string[];
  domain: string[];
  glossary_term_ids: string[];
  alias?: string;
  server_name?: string;
};

export type Proxy = {
  id: string;
  name: string;
  slug: string;
  description: string;
  created_at?: string;
  updated_at?: string;
};

export type GlossaryTerm = {
  id: string;
  domain_id: string;
  term: string;
  definition: string;
  domain_name?: string;
  created_at?: string;
  updated_at?: string;
};

export type Domain = {
  id: string;
  name: string;
  description: string;
  created_at?: string;
};

export type CallRecord = {
  id: string;
  trace_id?: string;
  span_id?: string;
  parent_span_id?: string;
  tool_name: string;
  proxy_id?: string;
  tool_id?: string;
  server_id?: string;
  request_args?: Record<string, unknown>;
  response_summary?: string;
  duration_ms: number;
  success: boolean;
  error_message?: string;
  timestamp?: string;
  client_id?: string;
  org_id?: string;
  tenant_id?: string;
  user_id?: string;
};

export type CallDetail = CallRecord & {
  events?: {
    type: string;
    description: string;
    details?: Record<string, unknown>;
    timestamp: string;
  }[];
};

export type CallStats = {
  total_calls: number;
  successful_calls: number;
  avg_latency_ms: number;
  top_tools: { name: string; count: number }[];
};

export type ToolTestResponse = {
  name: string;
  result?: Record<string, unknown>;
  error?: string;
  duration_ms: number;
};

export const serversApi = {
  list: (signal?: AbortSignal) => api.get<Server[]>("/servers", { signal }).then((r) => r.data),
  get: (id: string, signal?: AbortSignal) => api.get<Server>(`/servers/${id}`, { signal }).then((r) => r.data),
  create: (data: { name: string; transport?: string; command?: string; url?: string; headers?: Record<string, string> }) =>
    api.post<Server>("/servers", data).then((r) => r.data),
  update: (id: string, data: Partial<Server>) =>
    api.patch<Server>(`/servers/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/servers/${id}`),
  discover: (id: string) =>
    api.post<Tool[]>(`/servers/${id}/discover`).then((r) => r.data),
  discoverPreview: (data: { transport?: string; command?: string; url?: string; headers?: Record<string, string> }) =>
    api.post<{ name: string; description: string; input_schema: Record<string, unknown> }[]>("/servers/discover-preview", data).then((r) => r.data),
  ping: (id: string) =>
    api.post<{ id: string; status: string; latency_ms?: number; connection_status: string; error?: string }>(`/servers/${id}/ping`).then((r) => r.data),
  reconnect: (id: string) =>
    api.post<{ status: string; latency_ms?: number }>(`/servers/${id}/reconnect`).then((r) => r.data),
};

export const toolsApi = {
  list: (signal?: AbortSignal) => api.get<Tool[]>("/tools", { signal }).then((r) => r.data),
  get: (id: string, signal?: AbortSignal) => api.get<Tool>(`/tools/${id}`, { signal }).then((r) => r.data),
  update: (id: string, data: Partial<Tool>) =>
    api.patch<Tool>(`/tools/${id}`, data).then((r) => r.data),
  test: (id: string, data: { arguments?: Record<string, unknown> }) =>
    api.post<ToolTestResponse>(`/tools/${id}/test`, data).then((r) => r.data),
};

export const proxiesApi = {
  list: (signal?: AbortSignal) => api.get<Proxy[]>("/proxies", { signal }).then((r) => r.data),
  get: (id: string, signal?: AbortSignal) => api.get<Proxy>(`/proxies/${id}`, { signal }).then((r) => r.data),
  create: (data: { name: string; slug: string; description?: string }) =>
    api.post<Proxy>("/proxies", data).then((r) => r.data),
  update: (id: string, data: Partial<Proxy>) =>
    api.patch<Proxy>(`/proxies/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/proxies/${id}`),
  servers: (id: string, signal?: AbortSignal) =>
    api.get<Server[]>(`/proxies/${id}/servers`, { signal }).then((r) => r.data),
  linkServer: (proxyId: string, serverId: string, toolNames?: string[]) =>
    api.post(`/proxies/${proxyId}/servers`, { server_id: serverId, tool_names: toolNames }),
  unlinkServer: (proxyId: string, serverId: string) =>
    api.delete(`/proxies/${proxyId}/servers/${serverId}`),
  tools: (id: string, signal?: AbortSignal) =>
    api.get<Tool[]>(`/proxies/${id}/tools`, { signal }).then((r) => r.data),
  updateToolSetting: (proxyId: string, toolId: string, data: { enabled?: boolean; custom_description?: string; alias?: string }) =>
    api.patch(`/proxies/${proxyId}/tools/${toolId}`, data),
  stats: (id: string, signal?: AbortSignal) =>
    api.get<{ total_calls: number; successful_calls: number; avg_latency_ms: number; recent_calls: CallRecord[] }>(`/proxies/${id}/stats`, { signal }).then((r) => r.data),
  designer: (id: string) =>
    api.get<{ proxy: Proxy; servers: { server: Server; tools: { id: string; name: string; description: string; enabled: boolean; alias?: string; custom_description?: string }[] }[] }>(`/proxies/${id}/designer`).then((r) => r.data),
  saveDesigner: (id: string, data: { servers: { server_id: string; tools: { id: string; enabled?: boolean; alias?: string; custom_description?: string }[] }[] }) =>
    api.post(`/proxies/${id}/designer/save`, data),
};

export const glossaryApi = {
  listTerms: (signal?: AbortSignal) => api.get<GlossaryTerm[]>("/glossary/terms", { signal }).then((r) => r.data),
  createTerm: (data: { domain_id: string; term: string; definition?: string }) =>
    api.post<GlossaryTerm>("/glossary/terms", data).then((r) => r.data),
  updateTerm: (id: string, data: Partial<GlossaryTerm>) =>
    api.patch<GlossaryTerm>(`/glossary/terms/${id}`, data).then((r) => r.data),
  deleteTerm: (id: string) => api.delete(`/glossary/terms/${id}`),
  listDomains: (signal?: AbortSignal) => api.get<Domain[]>("/glossary/domains", { signal }).then((r) => r.data),
  createDomain: (data: { name: string; description?: string }) =>
    api.post<Domain>("/glossary/domains", data).then((r) => r.data),
  updateDomain: (id: string, data: { name?: string; description?: string }) =>
    api.patch<Domain>(`/glossary/domains/${id}`, data).then((r) => r.data),
  deleteDomain: (id: string) => api.delete(`/glossary/domains/${id}`),
  bulkImport: (data: { items: { domain: string; description?: string; terms: { term: string; definition?: string }[] }[] }) =>
    api.post<{ domains_created: number; terms_created: number }>("/glossary/import", data).then((r) => r.data),
};

export const analyticsApi = {
  stats: (signal?: AbortSignal) => api.get<CallStats>("/analytics/stats", { signal }).then((r) => r.data),
  calls: (params?: { limit?: number; offset?: number; org_id?: string; tenant_id?: string }, signal?: AbortSignal) =>
    api.get<CallRecord[]>("/analytics/calls", { params, signal }).then((r) => r.data),
  callDetail: (callId: string, signal?: AbortSignal) =>
    api.get<CallDetail>(`/analytics/calls/${callId}`, { signal }).then((r) => r.data),
  topTools: (limit?: number, signal?: AbortSignal) =>
    api.get<{ name: string; calls: number }[]>("/analytics/top-tools", { params: { limit }, signal }).then((r) => r.data),
  slowestTools: (limit?: number, signal?: AbortSignal) =>
    api.get<{ name: string; avg_latency_ms: number }[]>("/analytics/slowest-tools", { params: { limit }, signal }).then((r) => r.data),
  errorRates: (signal?: AbortSignal) =>
    api.get<{ total: number; error_count: number; error_rate: number }>("/analytics/error-rates", { signal }).then((r) => r.data),
  health: (signal?: AbortSignal) => api.get<{ status: string; version: string }>("/health", { signal }).then((r) => r.data),
};

export const dashboardApi = {
  summary: (signal?: AbortSignal) => api.get<DashboardSummary>("/dashboard/summary", { signal }).then((r) => r.data),
};

export const searchApi = {
  search: (q: string) => api.get<SearchResults>("/search", { params: { q } }).then((r) => r.data),
};

export type TraceSummary = {
  trace_id: string;
  tool_count: number;
  total_duration_ms: number;
  first_timestamp?: string;
  last_timestamp?: string;
  success_rate: number;
  tool_names: string[];
};

export type TraceGraphResponse = {
  trace_id: string;
  nodes: { id: string; type: string; tool_name: string; duration_ms: number; success: boolean; timestamp?: string; span_id?: string; parent_span_id?: string }[];
  edges: { source: string; target: string; label?: string; duration_ms?: number; type?: string }[];
  total_duration_ms: number;
  tool_count: number;
};

export type CoOccurrenceNode = {
  id: string;
  tool_name: string;
  call_count: number;
};

export type CoOccurrenceEdge = {
  source: string;
  target: string;
  weight: number;
};

export type CoOccurrenceResponse = {
  nodes: CoOccurrenceNode[];
  edges: CoOccurrenceEdge[];
};

export const graphApi = {
  full: (signal?: AbortSignal) => api.get<GraphData>("/graph", { signal }).then((r) => r.data),
  proxy: (proxyId: string, signal?: AbortSignal) => api.get<GraphData>(`/graph/proxy/${proxyId}`, { signal }).then((r) => r.data),
  traces: (params?: { limit?: number; proxy_id?: string }, signal?: AbortSignal) =>
    api.get<TraceSummary[]>("/graph/traces", { params, signal }).then((r) => r.data),
  traceDetail: (traceId: string, signal?: AbortSignal) =>
    api.get<TraceGraphResponse>(`/graph/trace/${traceId}`, { signal }).then((r) => r.data),
  coOccurrence: (params?: { proxy_id?: string; min_count?: number; limit?: number }, signal?: AbortSignal) =>
    api.get<CoOccurrenceResponse>("/graph/co-occurrence", { params, signal }).then((r) => r.data),
};

export const settingsApi = {
  list: () => api.get<Record<string, unknown>>("/settings").then((r) => r.data),
};
