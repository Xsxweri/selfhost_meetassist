import { useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Send, Plus, Bot, User } from "lucide-react";
import toast from "react-hot-toast";
import { Agent, errMsg } from "../lib/api";
import { streamAgentChat } from "../lib/sse";
import type { ConfirmationOut } from "../lib/types";
import NodeProgress from "../components/agent/NodeProgress";
import ConfirmationCard from "../components/agent/ConfirmationCard";
import { Button, PageHeader } from "../components/ui";

type Msg = { role: "user" | "assistant"; content: string };

export default function AgentChat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [trace, setTrace] = useState<string[]>([]);
  const [gate, setGate] = useState<{ c: ConfirmationOut; tid: string } | null>(null);
  const tidRef = useRef<string | undefined>(undefined);
  const endRef = useRef<HTMLDivElement>(null);
  const scroll = () => setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    setMessages(m => [...m, { role: "user", content: text }]);
    setStreaming(true); setTrace([]); scroll();
    try {
      await streamAgentChat(text, tidRef.current, {
        onStart: (tid) => { tidRef.current = tid; },
        onNode: (node) => { setTrace(t => [...t, node]); scroll(); },
        onConfirmation: (c, tid) => { tidRef.current = tid; setGate({ c, tid }); setStreaming(false); scroll(); },
        onDone: (r) => { setMessages(m => [...m, { role: "assistant", content: r.report || "（无报告）" }]); setStreaming(false); setTrace([]); scroll(); },
        onError: (msg) => { setMessages(m => [...m, { role: "assistant", content: "⚠️ " + msg }]); setStreaming(false); setTrace([]); },
      });
    } catch (e: any) { setStreaming(false); toast.error(errMsg(e, "对话失败")); }
  };

  const resume = async (approved: boolean) => {
    if (!gate) return;
    const tid = gate.tid;
    setGate(null); setStreaming(true); setTrace([]);
    try {
      const r = await Agent.resume({ thread_id: tid, approved });
      if (r.confirmation) setGate({ c: r.confirmation, tid: r.thread_id });
      else setMessages(m => [...m, { role: "assistant", content: r.report || (approved ? "✅ 已批准并执行" : "⛔ 已拒绝该操作") }]);
    } catch (e: any) { toast.error(errMsg(e, "确认失败")); }
    finally { setStreaming(false); scroll(); }
  };

  const newChat = () => { tidRef.current = undefined; setMessages([]); setGate(null); setTrace([]); };

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col p-6">
      <PageHeader title="Agent 助手" icon={Bot}
        action={<Button variant="ghost" size="sm" onClick={newChat}><Plus size={16} /> 新会话</Button>} />

      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {!messages.length && !streaming && (
          <div className="py-20 text-center text-sm text-ink-500">
            <Bot size={40} className="mx-auto mb-3 text-brand-400" />
            问我任何关于会议的问题，例如「总结我最近的会议」「列出所有未完成待办」
          </div>
        )}
        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              {m.role === "assistant" && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-600"><Bot size={16} /></div>}
               <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-[var(--color-accent)] text-white" : "bg-surface text-ink-900 shadow-[var(--shadow-card)]"}`}>
                <p className="whitespace-pre-wrap">{m.content}</p>
              </div>
              {m.role === "user" && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink-300/40 text-ink-700"><User size={16} /></div>}
            </motion.div>
          ))}
        </AnimatePresence>

        {streaming && (
          <div className="flex gap-3">
            <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-600"><Bot size={16} /></div>
            <div className="rounded-2xl bg-surface px-4 py-3 shadow-[var(--shadow-card)]"><NodeProgress trace={trace} /></div>
          </div>
        )}

        {gate && <ConfirmationCard c={gate.c} busy={streaming} onApprove={() => resume(true)} onReject={() => resume(false)} />}
        <div ref={endRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="mt-4 flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} disabled={streaming}
          placeholder="输入指令…（Enter 发送）"
          className="flex-1 rounded-xl border border-ink-300/60 px-4 py-2.5 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:opacity-50" />
        <Button type="submit" disabled={streaming || !input.trim()}><Send size={16} /> 发送</Button>
      </form>
    </div>
  );
}