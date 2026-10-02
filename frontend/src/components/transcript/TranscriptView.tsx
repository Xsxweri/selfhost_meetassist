import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Meetings } from "../../lib/api";
import { Skeleton } from "../ui";

const fmt = (s: number | null) => {
  if (s == null) return "--:--";
  const m = Math.floor(s / 60), ss = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
};

export default function TranscriptView({ id }: { id: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["transcripts", id], queryFn: () => Meetings.transcripts(id) });

  if (isLoading) return <div className="space-y-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-16" />)}</div>;
  if (!data?.length) return <div className="py-20 text-center text-sm text-ink-500">暂无转录，去「实时」页录制一场会议</div>;

  return (
    <div className="space-y-2">
      {data.map((seg, i) => (
        <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: Math.min(i * 0.02, 0.4) }}
          className="flex gap-4 rounded-xl bg-surface p-4 shadow-[var(--shadow-card)]">
          <div className="w-24 shrink-0 font-mono text-xs text-ink-500">{fmt(seg.start)} → {fmt(seg.end)}</div>
          <div className="flex-1">
            <span className="mb-1 inline-block rounded bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-600">{seg.speaker}</span>
            <p className="text-sm leading-relaxed text-ink-900">{seg.text}</p>
          </div>
        </motion.div>
      ))}
    </div>
  );
}