import { useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Download, Radio, AlertCircle } from "lucide-react";
import { format } from "date-fns";
import { Shares, downloadSharedExport } from "../lib/api";
import { Badge, Skeleton } from "../components/ui";

export default function SharedMeeting() {
  const { token } = useParams();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["shared", token],
    queryFn: () => Shares.view(token!),
    retry: false,
  });

  if (isLoading) return <div className="mx-auto max-w-3xl space-y-3 p-8"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-40" /></div>;
  if (isError || !data) return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="text-center">
        <AlertCircle className="mx-auto mb-3 text-red-500" size={40} />
        <h1 className="text-xl font-semibold">链接无效或已过期</h1>
        <p className="mt-1 text-sm text-ink-500">该分享链接可能已被撤销或超过有效期。</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-ink-900/5 bg-surface">
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-6 py-4">
          <Radio className="text-brand-600" size={20} />
          <span className="text-sm font-medium text-ink-500">会议助理 · 只读分享</span>
        </div>
      </header>
      <main className="mx-auto max-w-3xl p-6">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold">{data.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-ink-500">
            <span>创建于 {format(new Date(data.created_at), "yyyy-MM-dd HH:mm")}</span>
            <Badge tone="brand">只读</Badge>
          </div>

          {data.allow_download && (
            <div className="mt-4 flex gap-2">
              {(["pdf", "docx", "md"] as const).map((fmt) => (
                <button key={fmt} onClick={() => downloadSharedExport(token!, fmt)}
                  className="flex items-center gap-1.5 rounded-lg bg-surface px-3 py-1.5 text-sm ring-1 ring-ink-900/10 transition hover:bg-brand-50 hover:text-brand-600">
                  <Download size={14} /> {fmt.toUpperCase()}
                </button>
              ))}
            </div>
          )}

          <section className="mt-6 rounded-[var(--radius-card)] bg-surface p-6 shadow-[var(--shadow-card)]">
            <h2 className="mb-3 font-semibold">会议纪要</h2>
            {data.summary
              ? <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-700">{data.summary}</p>
              : <p className="text-sm text-ink-500">暂无纪要</p>}
          </section>

          {data.action_items.length > 0 && (
            <section className="mt-6 rounded-[var(--radius-card)] bg-surface p-6 shadow-[var(--shadow-card)]">
              <h2 className="mb-3 font-semibold">待办事项 ({data.action_items.length})</h2>
              <div className="space-y-2">
                {data.action_items.map((it) => (
                  <div key={it.id} className="rounded-lg bg-canvas p-3 text-sm">
                    <span className="text-ink-900">{it.content}</span>
                    {it.owner && <span className="ml-2 text-xs text-ink-500">👤 {it.owner}</span>}
                  </div>
                ))}
              </div>
            </section>
          )}

          {data.transcripts.length > 0 && (
            <section className="mt-6 rounded-[var(--radius-card)] bg-surface p-6 shadow-[var(--shadow-card)]">
              <h2 className="mb-3 font-semibold">转录全文 ({data.transcripts.length})</h2>
              <div className="space-y-2">
                {data.transcripts.map((t, i) => <p key={i} className="text-sm leading-relaxed text-ink-700">{t}</p>)}
              </div>
            </section>
          )}
        </motion.div>
      </main>
    </div>
  );
}