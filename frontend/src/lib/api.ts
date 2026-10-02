import axios from "axios";
import { useAuth } from "../store/auth";
import { streamAgentChat } from "./sse";
import type {
  AgentChatOut, AuditLogResponse, ConfirmationOut, ConsentStatus, MeetingResponse,
  MemoryResponse, SearchResponse, ShareLinkResponse, SharedMeetingResponse,
  SummaryResponse, TaskStatus, Token, UserResponse, ActionItemResponse, TranscriptSegment,
  ConsentType, ConsentResponse,
} from "./types";

export const http = axios.create({ baseURL: "/api/v1" });
http.interceptors.request.use((c) => {
  const t = useAuth.getState().token;
  if (t) c.headers.Authorization = `Bearer ${t}`;
  return c;
});
http.interceptors.response.use(
  (r) => r,
  (e) => { if (e.response?.status === 401) useAuth.getState().logout(); return Promise.reject(e); }
);

export const Auth = {
  register: (body: { email: string; password: string; name?: string }) => http.post<UserResponse>("/auth/register", body).then(r => r.data),
  login: (form: URLSearchParams) => http.post<Token>("/auth/login", form).then(r => r.data),
  me: () => http.get<UserResponse>("/auth/me").then(r => r.data),
};

export const Meetings = {
  list: (skip = 0, limit = 50) => http.get<MeetingResponse[]>("/meetings", { params: { skip, limit } }).then(r => r.data),
  get: (id: string) => http.get<MeetingResponse>(`/meetings/${id}`).then(r => r.data),
  create: (body: { title: string; scheduled_at?: string; location?: string }) => http.post<MeetingResponse>("/meetings", body).then(r => r.data),
  update: (id: string, body: { title?: string; transcript?: string; summary?: string }) => http.patch<MeetingResponse>(`/meetings/${id}`, body).then(r => r.data),
  remove: (id: string) => http.delete(`/meetings/${id}`).then(r => r.data),
  transcripts: (id: string) => http.get<TranscriptSegment[]>(`/meetings/${id}/transcripts`).then(r => r.data),
};

export const Consents = {
  status: (id: string) => http.get<ConsentStatus[]>(`/meetings/${id}/consents/status`).then(r => r.data),
  list: (id: string) => http.get<ConsentResponse[]>(`/meetings/${id}/consents`).then(r => r.data),
  grant: (id: string, consent_type: ConsentType, note?: string) =>
    http.post<ConsentResponse>(`/meetings/${id}/consents`, { consent_type, action: "grant", note }).then(r => r.data),
  revoke: (id: string, consent_type: ConsentType) =>
    http.post<ConsentResponse>(`/meetings/${id}/consents`, { consent_type, action: "revoke" }).then(r => r.data),
};

export const Summaries = {
  get: (id: string) => http.get<SummaryResponse>(`/meetings/${id}/summary`).then(r => r.data),
  generate: (id: string) => http.post<SummaryResponse>(`/meetings/${id}/summary`).then(r => r.data),
  generateAsync: (id: string) => http.post<{ task_id: string; status: string }>(`/meetings/${id}/summary/async`).then(r => r.data),
};

export const ActionItems = {
  list: (id: string) => http.get<ActionItemResponse[]>(`/meetings/${id}/action-items`).then(r => r.data),
  update: (id: string, itemId: string, body: Partial<{ content: string; owner: string; due_date: string; status: string }>) =>
    http.patch<ActionItemResponse>(`/meetings/${id}/action-items/${itemId}`, body).then(r => r.data),
  remove: (id: string, itemId: string) => http.delete(`/meetings/${id}/action-items/${itemId}`).then(r => r.data),
};

export const Tasks = { status: (tid: string) => http.get<TaskStatus>(`/tasks/${tid}`).then(r => r.data) };
export const Search = { query: (q: string, meeting_id?: string) => http.get<SearchResponse>("/search", { params: { q, meeting_id } }).then(r => r.data) };
export const Audits = { list: (skip = 0, limit = 50) => http.get<AuditLogResponse[]>("/audits", { params: { skip, limit } }).then(r => r.data) };

export const Memory = {
  list: (skip = 0, limit = 50, kind?: string) => http.get<MemoryResponse[]>("/memory", { params: { skip, limit, kind } }).then(r => r.data),
  create: (body: { kind?: string; subject?: string; content: string; importance?: number; meeting_id?: string }) => http.post<MemoryResponse[]>("/memory", body).then(r => r.data),
  update: (id: string, body: Partial<{ kind: string; subject: string; content: string; importance: number }>) => http.patch<MemoryResponse>(`/memory/${id}`, body).then(r => r.data),
  remove: (id: string) => http.delete(`/memory/${id}`).then(r => r.data),
  evolution: (id: string) => http.get<MemoryResponse[]>(`/memory/${id}/evolution`).then(r => r.data),
};

export const Shares = {
  create: (id: string, body: { expires_in_hours?: number; password?: string | null }) => http.post<ShareLinkResponse>(`/meetings/${id}/shares`, body).then(r => r.data),
  revoke: (id: string, token: string) => http.post(`/meetings/${id}/shares/${token}/revoke`).then(r => r.data),
  view: (token: string, password?: string) => http.get<SharedMeetingResponse>(`/shares/${token}`, { params: { password } }).then(r => r.data),
};

export const Agent = {
  chat: (body: { message: string; thread_id?: string; confirmation?: ConfirmationOut }) => http.post<AgentChatOut>("/agent/chat", body).then(r => r.data),
  stream: streamAgentChat,
};

export const exportUrl = (id: string, fmt: "pdf" | "docx" | "md") =>
  `/api/v1/meetings/${id}/exports/${fmt}?token=${useAuth.getState().token}`;

export function errMsg(err: any, fallback = "操作失败"): string {
  const d = err?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x: any) => x?.msg ?? JSON.stringify(x)).join("；");
  if (d) return JSON.stringify(d);
  return err?.message || fallback;
}