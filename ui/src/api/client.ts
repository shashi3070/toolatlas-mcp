import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export type Server = {
  id: string;
  name: string;
  transport: string;
  command?: string;
  url?: string;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
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
  glossary_term_id?: string;
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
  term: string;
  definition: string;
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

export const serversApi = {
  list: () => api.get<Server[]>("/servers").then((r) => r.data),
  get: (id: string) => api.get<Server>(`/servers/${id}`).then((r) => r.data),
  create: (data: { name: string; transport?: string; command?: string; url?: string }) =>
    api.post<Server>("/servers", data).then((r) => r.data),
  update: (id: string, data: Partial<Server>) =>
    api.patch<Server>(`/servers/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/servers/${id}`),
  discover: (id: string) =>
    api.post<Tool[]>(`/servers/${id}/discover`).then((r) => r.data),
  discoverPreview: (data: { transport?: string; command?: string; url?: string }) =>
    api.post<{ name: string; description: string; input_schema: Record<string, unknown> }[]>("/servers/discover-preview", data).then((r) => r.data),
};

export const toolsApi = {
  list: () => api.get<Tool[]>("/tools").then((r) => r.data),
  get: (id: string) => api.get<Tool>(`/tools/${id}`).then((r) => r.data),
  update: (id: string, data: Partial<Tool>) =>
    api.patch<Tool>(`/tools/${id}`, data).then((r) => r.data),
};

export const proxiesApi = {
  list: () => api.get<Proxy[]>("/proxies").then((r) => r.data),
  get: (id: string) => api.get<Proxy>(`/proxies/${id}`).then((r) => r.data),
  create: (data: { name: string; slug: string; description?: string }) =>
    api.post<Proxy>("/proxies", data).then((r) => r.data),
  update: (id: string, data: Partial<Proxy>) =>
    api.patch<Proxy>(`/proxies/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/proxies/${id}`),
  servers: (id: string) =>
    api.get<Server[]>(`/proxies/${id}/servers`).then((r) => r.data),
  linkServer: (proxyId: string, serverId: string) =>
    api.post(`/proxies/${proxyId}/servers`, { server_id: serverId }),
  unlinkServer: (proxyId: string, serverId: string) =>
    api.delete(`/proxies/${proxyId}/servers/${serverId}`),
  tools: (id: string) =>
    api.get<Tool[]>(`/proxies/${id}/tools`).then((r) => r.data),
  updateToolSetting: (proxyId: string, toolId: string, data: { enabled?: boolean; custom_description?: string; alias?: string }) =>
    api.patch(`/proxies/${proxyId}/tools/${toolId}`, data),
  stats: (id: string) =>
    api.get<{ total_calls: number; successful_calls: number; avg_latency_ms: number; recent_calls: CallRecord[] }>(`/proxies/${id}/stats`).then((r) => r.data),
};

export const glossaryApi = {
  listTerms: () => api.get<GlossaryTerm[]>("/glossary/terms").then((r) => r.data),
  createTerm: (data: { term: string; definition?: string }) =>
    api.post<GlossaryTerm>("/glossary/terms", data).then((r) => r.data),
  updateTerm: (id: string, data: Partial<GlossaryTerm>) =>
    api.patch<GlossaryTerm>(`/glossary/terms/${id}`, data).then((r) => r.data),
  deleteTerm: (id: string) => api.delete(`/glossary/terms/${id}`),
  listDomains: () => api.get<Domain[]>("/glossary/domains").then((r) => r.data),
  createDomain: (data: { name: string; description?: string }) =>
    api.post<Domain>("/glossary/domains", data).then((r) => r.data),
};

export const analyticsApi = {
  stats: () => api.get<CallStats>("/analytics/stats").then((r) => r.data),
  calls: (params?: { limit?: number; offset?: number }) =>
    api.get<CallRecord[]>("/analytics/calls", { params }).then((r) => r.data),
  callDetail: (callId: string) =>
    api.get<CallDetail>(`/analytics/calls/${callId}`).then((r) => r.data),
  health: () => api.get<{ status: string; version: string }>("/health").then((r) => r.data),
};
