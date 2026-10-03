export interface UserResponse { id: string; email: string; name: string | null; is_active: boolean; }
export interface Token { access_token: string; token_type: string; }
export interface MeetingResponse {
  id: string;
  owner_id: string | null;
  title: string;
  transcript: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
}
export interface TranscriptSegment { start: number | null; end: number | null; speaker: string; text: string; }
export type ConsentType = "recording" | "speaker_id";
export type ConsentAction = "grant" | "revoke";
export interface ConsentStatus { consent_type: ConsentType; granted: boolean; updated_at: string | null; }
export interface ConsentResponse {
  id: string; meeting_id: string; user_id: string; consent_type: string; action: string;
  ip_address: string | null; user_agent: string | null; note: string | null; created_at: string;
}
export interface StreamSegment { start: number; end: number; text: string; speaker: string; }
export type StreamMsg =
  | { type: "ready"; sample_rate: number }
  | { type: "subtitle"; segments: StreamSegment[] }
  | { type: "warning"; detail: string }
  | { type: "end"; duration: number }
  | { type: "error"; detail: string };
export interface ActionItemResponse { id: string; content: string; owner: string | null; due_date: string | null; status: string; }
export interface SummaryResponse { summary: string | null; action_items: ActionItemResponse[]; }
export type TaskState = "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
export interface TaskStatus { task_id: string; status: TaskState; result: SummaryResponse | null; detail: string | null; }
export interface SearchHit {
  id: string;
  meeting_id: string;
  text: string | null;
  speaker: string | null;
  created_at: string;
  similarity: number;
}
export interface SearchResponse { query: string; count: number; results: SearchHit[]; }
export interface ShareLinkResponse {
  id: string; meeting_id: string; token: string; path: string;
  allow_download: boolean; expires_at: string | null; revoked_at: string | null; created_at: string;
}
export interface SharedMeetingResponse {
  title: string; summary: string | null; created_at: string; allow_download: boolean;
  action_items: ActionItemResponse[]; transcripts: string[];
}
export interface AuditLogResponse {
  id: string; user_id: string | null; meeting_id: string | null; action: string;
  resource: string | null; detail: Record<string, any> | null;
  ip_address: string | null; user_agent: string | null; created_at: string;
}
export type MemoryKind = "decision" | "action" | "preference" | "fact" | "entity";
export interface MemoryResponse {
  id: string; owner_id: string; meeting_id: string | null; kind: MemoryKind; subject: string | null;
  content: string; importance: number; confidence: number; valid_from: string | null; valid_to: string | null;
  superseded_by: string | null; access_count: number; created_at: string; updated_at: string;
}
export interface MemorySearchHit { id: string; kind: string; subject: string | null; content: string; meeting_id: string | null; importance: number; similarity: number; }
export interface ConfirmationOut {
  type: string;
  tool: string;
  args: Record<string, any>;
  reason: string;
  message: string;
}
export interface AgentChatOut {
  thread_id: string;
  status: string;
  report: string | null;
  confirmation: ConfirmationOut | null;
}
export interface AgentResumeIn { thread_id: string; approved: boolean; }