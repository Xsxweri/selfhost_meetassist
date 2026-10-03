import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Search as SearchIcon, MessagesSquare } from "lucide-react";
import { format } from "date-fns";
import { Search as SearchApi } from "../lib/api";
import { Skeleton, Button, Badge, PageHeader } from "../components/ui";

export default function Search() {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const nav = useNavigate();
  const { data, isFetching } = useQuery({
    queryKey: ["search", submitted],
    queryFn: () => SearchApi.all(submitted, 20),
    enabled: submitted.trim().length > 0,
  });
  const submit = (e: FormEvent) => { e.preventDefault(); setSubmitted(q.trim()); };

  return (
    <div className="mx-auto max-w-4xl p-8">
      <PageHeader title="全局搜索" icon={SearchIcon} />

      <form onSubmit={submit} className="mb-6 flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="语义检索全部会议转录…"
          className="flex-1 rounded-xl border border-ink-900/10 bg-surface px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)]" />
        <Button type="submit" disabled={!q.trim()}>搜索</Button>
      </form>

      {isFetching && <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}</div>}

      {!isFetching && submitted && data && (
        <>
          <p className="mb-3 text-sm text-ink-500">找到 {data.count} 条与「{data.query}」相关的结果</p>
          {data.results.length === 0 ? (
            <div className="py-16 text-center text-ink-500">无匹配结果</div>
          ) : (
            <div className="space-y-2">
              {data.results.map((hit, i) => (
                <motion.button key={hit.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i * 0.03, 0.3) }} onClick={() => nav(`/meetings/${hit.meeting_id}`)}
                  className="block w-full rounded-xl bg-surface p-4 text-left shadow-[var(--shadow-card)] transition hover:ring-2 hover:ring-brand-400">
                  <div className="flex items-start justify-between gap-3">
                    <p className="flex-1 text-sm leading-relaxed text-ink-900">{hit.text || "(空)"}</p>
                    <Badge tone="brand">{(hit.similarity * 100).toFixed(0)}%</Badge>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-x-4 text-xs text-ink-500">
                    {hit.speaker && <span className="flex items-center gap-1"><MessagesSquare size={12} /> {hit.speaker}</span>}
                    <span>{format(new Date(hit.created_at), "yyyy-MM-dd HH:mm")}</span>
                    <span>会议 {hit.meeting_id.slice(0, 8)}</span>
                  </div>
                </motion.button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}