import { useState } from "react";
import { Link } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Plus, FileText, CalendarDays } from "lucide-react";
import toast from "react-hot-toast";
import { Meetings, errMsg } from "../lib/api";
import { Button, Card, Skeleton, Badge } from "../components/ui";
import { format } from "date-fns";

export default function MeetingList() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const { data, isPending } = useQuery({ queryKey: ["meetings"], queryFn: () => Meetings.list(0, 50) });
  const create = useMutation({
    mutationFn: (t: string) => Meetings.create({ title: t }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["meetings"] }); setTitle(""); toast.success("已创建"); },
    onError: (e: any) => toast.error(errMsg(e, "创建失败")),
  });

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight meeting-hero">我的会议</h1>
          <p className="text-sm text-ink-500 mt-1">共 {data?.length ?? 0} 场</p>
        </div>
      </header>

      <form onSubmit={(e) => { e.preventDefault(); title.trim() && create.mutate(title.trim()); }} className="flex gap-2 mb-6">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="新建会议标题…"
          className="flex-1 rounded-xl border border-ink-300/60 px-4 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition" />
        <Button type="submit" disabled={create.isPending}><Plus size={16} /> 新建</Button>
      </form>

      {isPending ? (
        <div className="grid gap-3">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}</div>
      ) : (
        <div className="grid gap-3">
          {data?.map((m, i) => (
            <motion.div key={m.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04, type: "spring", stiffness: 300, damping: 26 }}>
              <Link to={`/meetings/${m.id}`} viewTransition>
                <Card className="p-5 hover:border-brand-400/50 hover:shadow-lg transition-all group cursor-pointer">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h3 className="font-medium truncate group-hover:text-brand-700 transition-colors" style={{ viewTransitionName: `mt-${m.id}` }}>{m.title}</h3>
                      <div className="flex items-center gap-3 mt-2 text-xs text-ink-500">
                        <span className="inline-flex items-center gap-1"><CalendarDays size={13} />{format(new Date(m.created_at), "yyyy-MM-dd HH:mm")}</span>
                        {m.summary ? <Badge tone="green">已生成纪要</Badge> : <Badge tone="gray">无纪要</Badge>}
                      </div>
                    </div>
                    <FileText className="text-ink-300 group-hover:text-brand-500 transition-colors shrink-0" size={20} />
                  </div>
                </Card>
              </Link>
            </motion.div>
          ))}
          {!data?.length && <p className="text-center text-ink-500 py-16">还没有会议，先新建一场吧</p>}
        </div>
      )}
    </div>
  );
}