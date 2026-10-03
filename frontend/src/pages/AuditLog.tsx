import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { ScrollText } from "lucide-react";
import { format } from "date-fns";
import { Audits, Meetings } from "../lib/api";
import { auditMeta } from "../components/auditMeta";
import { Badge, Skeleton, PageHeader } from "../components/ui";

export default function AuditLog() {
  const [meetingId, setMeetingId] = useState("");
  const { data: meetings } = useQuery({ queryKey: ["meetings"], queryFn: () => Meetings.list(0, 100) });
  const { data, isLoading } = useQuery({
    queryKey: ["audits", meetingId],
    queryFn: () => Audits.list({ meeting_id: meetingId || undefined, limit: 200 }),
  });

  return (
    <div className="mx-auto max-w-5xl p-8">
      <PageHeader title="审计日志" icon={ScrollText} action={
        <select value={meetingId} onChange={(e) => setMeetingId(e.target.value)}
          className="rounded-lg border border-ink-900/10 bg-surface px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)]">
          <option value="">全部会议</option>
          {meetings?.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
        </select>
      } />

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-16" />)}</div>
      ) : !data?.length ? (
        <div className="py-20 text-center text-ink-500">暂无审计记录</div>
      ) : (
        <div className="space-y-2">
          {data.map((log, i) => {
            const meta = auditMeta(log.action);
            const Icon = meta.icon;
            return (
              <motion.div key={log.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.02, 0.3) }}
                className="flex items-start gap-3 rounded-xl bg-surface p-4 shadow-[var(--shadow-card)]">
                <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${meta.cls}`}><Icon size={16} /></span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-ink-900">{meta.label}</span>
                    <code className="rounded bg-ink-900/5 px-1.5 py-0.5 text-xs text-ink-500">{log.action}</code>
                    {log.resource && <Badge tone="gray">{log.resource}</Badge>}
                  </div>
                  {log.detail && Object.keys(log.detail).length > 0 && (
                    <pre className="mt-1.5 overflow-x-auto rounded-lg bg-canvas p-2 text-xs text-ink-700">{JSON.stringify(log.detail, null, 2)}</pre>
                  )}
                  <div className="mt-1.5 flex flex-wrap gap-x-4 text-xs text-ink-500">
                    <span>{format(new Date(log.created_at), "yyyy-MM-dd HH:mm:ss")}</span>
                    {log.ip_address && <span>IP {log.ip_address}</span>}
                    {log.meeting_id && <span>会议 {log.meeting_id.slice(0, 8)}</span>}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}