import { useAuth } from "../store/auth";
import type { AgentChatOut, ConfirmationOut } from "./types";

export interface AgentStreamHandlers {
  onStart?: (threadId: string) => void;
  onNode?: (node: string, status: string) => void;
  onConfirmation?: (c: ConfirmationOut, threadId: string) => void;
  onDone?: (r: AgentChatOut) => void;
  onError?: (msg: string) => void;
}

export async function streamAgentChat(message: string, threadId: string | undefined, h: AgentStreamHandlers) {
  const res = await fetch("/api/v1/agent/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${useAuth.getState().token}` },
    body: JSON.stringify({ message, thread_id: threadId }),
  });
  if (!res.ok || !res.body) { h.onError?.(`HTTP ${res.status}`); return; }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const frames = buf.split("\n\n");
    buf = frames.pop() ?? "";
    for (const frame of frames) {
      const event = /event:\s*(.+)/.exec(frame)?.[1]?.trim();
      const dataLine = /data:\s*(.+)/.exec(frame)?.[1];
      if (!dataLine) continue;
      let data: any;
      try { data = JSON.parse(dataLine); } catch { continue; }
      if (event === "start") h.onStart?.(data.thread_id);
      else if (event === "node") h.onNode?.(data.node, data.status);
      else if (event === "confirmation") h.onConfirmation?.(data.confirmation, data.thread_id);
      else if (event === "done") h.onDone?.(data);
      else if (event === "error") h.onError?.(data.detail);
    }
  }
}