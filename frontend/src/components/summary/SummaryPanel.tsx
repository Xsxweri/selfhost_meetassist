import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import toast from "react-hot-toast";
import { Sparkles, Trash2, ArrowRight, Pencil } from "lucide-react";
import { ActionItems, Meetings, Summaries, Tasks, errMsg } from "../../lib/api";
import type { ActionItemResponse } from "../../lib/types";
import { Button, Skeleton } from "../ui";

const FLOW: Record<string, string> = { pending: "confirmed", confirmed: "done", done: "pending" };
const LABEL: Record<string, string> = { pending: "待处理", confirmed: "已确认", done: "已完成" };

export default function SummaryPanel({ id }: { id: string }) {
  const qc = useQueryClient();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);

  const sumQ = useQuery({ queryKey: ["summary", id], queryFn: () => Summaries.get(id) });
  const taskQ = useQuery({
    queryKey: ["task", taskId], queryFn: () => Tasks.status(taskId!), enabled: !!taskId,
    refetchInterval: (q) => (["SUCCESS", "FAILURE"].includes(q.state.data?.status ?? "") ? false : 1500),
  });

  useEffect(() => {
    const st = taskQ.data?.status;
    if (st === "SUCCESS") { qc.invalidateQueries({ queryKey: ["summary", id] }); setTaskId(null); toast.success("纪要已生成"); }
    if (st === "FAILURE") { setTaskId(null); toast.error(taskQ.data?.detail ?? "生成失败"); }
  }, [taskQ.data]);

  const generate = async () => { const { task_id } = await Summaries.generateAsync(id); setTaskId(task_id); };
   const startEdit = () => { setDraft(sumQ.data?.summary ?? ""); setEditing(true); };
  const saveEdit = async () => {
    setSaving(true);
    try {
      await Meetings.update(id, { summary: draft });
      await qc.invalidateQueries({ queryKey: ["summary", id] });
      setEditing(false);
      toast.success("纪要已保存");
    } catch (e) { toast.error(errMsg(e, "保存失败")); }
    finally { setSaving(false); }
  };
  const advance = (it: ActionItemResponse) =>
    ActionItems.update(id, it.id, { status: FLOW[it.status] ?? "done" }).then(() => qc.invalidateQueries({ queryKey: ["summary", id] }));
  const remove = (it: ActionItemResponse) =>
    ActionItems.remove(id, it.id).then(() => qc.invalidateQueries({ queryKey: ["summary", id] }));

  if (sumQ.isLoading) return <div className="space-y-3"><Skeleton className="h-40" /><Skeleton className="h-24" /></div>;

  const items = sumQ.data?.action_items ?? [];
  const groups = ["pending", "confirmed", "done"].map(s => ({ s, list: items.filter(i => i.status === s) }));

  return (
    <div className="space-y-6">
      <div className="rounded-[var(--radius-card)] bg-surface p-6 shadow-[var(--shadow-card)]">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold">会议纪要</h3>
          <div className="flex gap-2">
            {!editing && sumQ.data?.summary && (
              <Button variant="ghost" size="sm" onClick={startEdit}><Pencil size={16} /> 编辑</Button>
            )}
            <Button onClick={generate} disabled={!!taskId || editing}>
              <Sparkles size={16} /> {taskId ? "生成中…" : (sumQ.data?.summary ? "重新生成" : "生成纪要")}
            </Button>
          </div>
        </div>
        {taskId && (
          <div className="mb-3 h-1 overflow-hidden rounded bg-brand-50">
            <motion.div className="h-full w-1/3 bg-brand-500" animate={{ x: ["-100%", "300%"] }} transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }} />
          </div>
        )}
        {editing ? (
          <div className="space-y-3">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={12}
              className="w-full rounded-lg border border-[var(--color-line)] bg-canvas p-3 text-sm leading-relaxed text-ink-900 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
              placeholder="编辑会议纪要…"
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setEditing(false)} disabled={saving}>取消</Button>
              <Button size="sm" onClick={saveEdit} disabled={saving}>{saving ? "保存中…" : "保存"}</Button>
            </div>
          </div>
        ) : sumQ.data?.summary ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-700">{sumQ.data.summary}</p>
        ) : (
          <p className="text-sm text-ink-500">尚无纪要，点右上「生成纪要」（异步，自动轮询）。</p>
        )}
      </div>

      <div>
        <h3 className="mb-3 font-semibold">待办事项 <span className="text-sm text-ink-500">({items.length})</span></h3>
        <div className="grid gap-4 md:grid-cols-3">
          {groups.map(({ s, list }) => (
            <div key={s} className="rounded-xl bg-canvas p-3 ring-1 ring-black/5">
              <div className="mb-2 text-xs font-semibold text-ink-500">{LABEL[s]} · {list.length}</div>
              <div className="space-y-2">
                {list.map(it => (
                  <motion.div key={it.id} layout initial={{ opacity: 0, scale: .95 }} animate={{ opacity: 1, scale: 1 }}
                    className="rounded-lg bg-surface p-3 shadow-sm">
                    <p className="text-sm text-ink-900">{it.content}</p>
                    <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-ink-500">
                      {it.owner && <span>👤 {it.owner}</span>}
                      {it.due_date && <span>📅 {it.due_date.slice(0, 10)}</span>}
                    </div>
                    <div className="mt-2 flex gap-2">
                      <button onClick={() => advance(it)} className="flex items-center gap-1 text-xs text-brand-600 hover:underline"><ArrowRight size={12} /> {LABEL[FLOW[it.status] ?? "done"]}</button>
                      <button onClick={() => remove(it)} className="flex items-center gap-1 text-xs text-red-500 hover:underline"><Trash2 size={12} /> 删除</button>
                    </div>
                  </motion.div>
                ))}
                {!list.length && <div className="py-4 text-center text-xs text-ink-300">空</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}