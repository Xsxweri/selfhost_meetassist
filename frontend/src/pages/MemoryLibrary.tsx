import { useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import { format } from "date-fns";
import { Brain, Pencil, Trash2, ChevronDown, GitBranch, Inbox } from "lucide-react";
import toast from "react-hot-toast";
import { Memory, errMsg } from "../lib/api";
import type { MemoryResponse } from "../lib/types";
import { KIND_KEYS, kindMeta } from "../components/memory/kindMeta";
import EvolutionChain from "../components/memory/EvolutionChain";
import MemoryEditDialog from "../components/memory/MemoryEditDialog";
import { Button, Card, Badge, Skeleton, PageHeader } from "../components/ui";

function FilterChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button onClick={onClick}
      className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition ${active ? "bg-[var(--color-accent)] text-white shadow-sm" : "border border-ink-900/5 bg-surface text-ink-700 hover:bg-ink-300/20"}`}>
      {children}
    </button>
  );
}

export default function MemoryLibrary() {
  const qc = useQueryClient();
  const [kind, setKind] = useState<string | undefined>(undefined);
  const [includeSuperseded, setIncludeSuperseded] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editing, setEditing] = useState<MemoryResponse | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["memories", kind, includeSuperseded],
    queryFn: () => Memory.list({ kind, include_superseded: includeSuperseded, limit: 100 }),
  });

  const remove = async (m: MemoryResponse) => {
    if (!window.confirm("确认删除这条记忆？（软删除，仍可从演进链追溯）")) return;
    try {
      await Memory.remove(m.id);
      toast.success("已删除");
      qc.invalidateQueries({ queryKey: ["memories"] });
    } catch (e: any) { toast.error(errMsg(e, "删除失败")); }
  };

  return (
    <div className="mx-auto max-w-4xl p-6">
       <PageHeader title="记忆库" icon={Brain} />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <FilterChip active={!kind} onClick={() => setKind(undefined)}>全部</FilterChip>
        {KIND_KEYS.map((k) => <FilterChip key={k} active={kind === k} onClick={() => setKind(k)}>{kindMeta(k).label}</FilterChip>)}
        <label className="ml-auto flex cursor-pointer items-center gap-2 text-xs text-ink-500">
          <input type="checkbox" checked={includeSuperseded} onChange={(e) => setIncludeSuperseded(e.target.checked)} className="accent-[var(--color-accent)]" />
          显示历史版本
        </label>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-28 w-full" />)}</div>
      ) : !data || data.length === 0 ? (
        <Card className="p-16 text-center">
          <Inbox className="mx-auto mb-3 text-ink-300" size={40} />
          <p className="text-sm text-ink-500">还没有记忆。生成会议纪要后，系统会自动抽取决策 / 行动 / 偏好 / 事实 / 实体。</p>
        </Card>
      ) : (
        <div className="space-y-3">
          <AnimatePresence initial={false}>
            {data.map((m) => {
              const meta = kindMeta(m.kind);
              const isOpen = expanded === m.id;
              const current = m.superseded_by === null && m.valid_to === null;
              return (
                <motion.div key={m.id} layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: .98 }}>
                  <Card className="overflow-hidden">
                    <div className="p-4">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.cls}`}>{meta.label}</span>
                        {current ? <Badge tone="green">当前有效</Badge> : <Badge tone="gray">历史版本</Badge>}
                        {m.subject && <span className="text-sm font-medium text-ink-900">{m.subject}</span>}
                        <div className="ml-auto flex items-center gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setEditing(m)}><Pencil size={14} /></Button>
                          <Button variant="ghost" size="sm" onClick={() => remove(m)} className="hover:text-danger"><Trash2 size={14} /></Button>
                        </div>
                      </div>
                      <p className="text-sm leading-relaxed text-ink-700">{m.content}</p>
                      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink-500">
                        <span>重要性 <b className="text-[var(--color-accent)]">{m.importance.toFixed(2)}</b></span>
                        <span>置信度 <b className="text-[var(--color-accent)]">{m.confidence.toFixed(2)}</b></span>
                        <span>命中 {m.access_count} 次</span>
                        <span>{format(new Date(m.created_at), "yyyy-MM-dd HH:mm")}</span>
                      </div>
                      <button onClick={() => setExpanded(isOpen ? null : m.id)}
                        className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-[var(--color-accent)] hover:opacity-80">
                        <GitBranch size={13} /> {isOpen ? "收起演进链" : "查看演进链"}
                        <motion.span animate={{ rotate: isOpen ? 180 : 0 }}><ChevronDown size={13} /></motion.span>
                      </button>
                    </div>
                    <AnimatePresence initial={false}>
                      {isOpen && (
                        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: .25 }} className="overflow-hidden border-t border-ink-900/5 bg-canvas/60">
                          <EvolutionChain memoryId={m.id} />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </Card>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}

      <AnimatePresence>{editing && <MemoryEditDialog memory={editing} onClose={() => setEditing(null)} />}</AnimatePresence>
    </div>
  );
}