import { useState } from "react";
import { motion } from "motion/react";
import { X } from "lucide-react";
import toast from "react-hot-toast";
import { useQueryClient } from "@tanstack/react-query";
import { Memory, errMsg } from "../../lib/api";
import type { MemoryResponse } from "../../lib/types";
import { KIND_KEYS, KIND_META } from "./kindMeta";
import { Button } from "../ui";

export default function MemoryEditDialog({ memory, onClose }: { memory: MemoryResponse; onClose: () => void }) {
  const qc = useQueryClient();
  const [kind, setKind] = useState(memory.kind);
  const [subject, setSubject] = useState(memory.subject ?? "");
  const [content, setContent] = useState(memory.content);
  const [importance, setImportance] = useState(memory.importance);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await Memory.update(memory.id, { kind, subject: subject || undefined, content, importance });
      toast.success("已保存");
      qc.invalidateQueries({ queryKey: ["memories"] });
      qc.invalidateQueries({ queryKey: ["memory-chain", memory.id] });
      onClose();
    } catch (e: any) { toast.error(errMsg(e, "保存失败")); }
    finally { setBusy(false); }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 p-4" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: .95, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: .95 }}
        onClick={(e) => e.stopPropagation()} className="w-full max-w-lg rounded-2xl bg-surface p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">编辑记忆</h3>
          <button onClick={onClose} className="text-ink-500 hover:text-ink-900"><X size={20} /></button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-500">类型</label>
            <div className="flex flex-wrap gap-2">
              {KIND_KEYS.map((k) => (
                <button key={k} onClick={() => setKind(k)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${kind === k ? KIND_META[k].cls + " ring-2 ring-brand-400" : "bg-ink-300/20 text-ink-500 hover:bg-ink-300/40"}`}>
                  {KIND_META[k].label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-500">主题</label>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="可选"
              className="w-full rounded-xl border border-ink-300/60 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-500">内容</label>
            <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4}
              className="w-full resize-none rounded-xl border border-ink-300/60 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
          </div>
          <div>
            <label className="mb-1.5 flex items-center justify-between text-xs font-medium text-ink-500">
              <span>重要性</span><span className="tabular-nums text-brand-600">{importance.toFixed(2)}</span>
            </label>
            <input type="range" min={0} max={1} step={0.05} value={importance} onChange={(e) => setImportance(Number(e.target.value))} className="w-full accent-brand-600" />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={busy}>取消</Button>
          <Button onClick={save} disabled={busy || !content.trim()}>{busy ? "保存中…" : "保存"}</Button>
        </div>
      </motion.div>
    </motion.div>
  );
}