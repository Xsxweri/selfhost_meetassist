import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { format } from "date-fns";
import { Clock, Sparkles, Archive } from "lucide-react";
import { Memory } from "../../lib/api";
import { kindMeta } from "./kindMeta";
import { Badge, Skeleton } from "../ui";

function fmt(dt: string | null) { return dt ? format(new Date(dt), "yyyy-MM-dd HH:mm") : "—"; }

function Meter({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 text-xs text-ink-500">
      <span className="w-12 shrink-0">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-ink-300/40">
        <motion.div initial={{ width: 0 }} animate={{ width: `${Math.round(value * 100)}%` }}
          transition={{ duration: .6, ease: "easeOut" }} className="h-full rounded-full bg-brand-500" />
      </div>
      <span className="w-8 text-right tabular-nums">{value.toFixed(2)}</span>
    </div>
  );
}

export default function EvolutionChain({ memoryId }: { memoryId: string }) {
  const { data: chain, isLoading } = useQuery({
    queryKey: ["memory-chain", memoryId],
    queryFn: () => Memory.chain(memoryId),
  });

  if (isLoading) return <div className="space-y-3 p-4"><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /></div>;
  if (!chain || chain.length === 0) return <p className="p-4 text-sm text-ink-500">无演进数据</p>;

  return (
    <div className="px-4 py-3">
      {chain.length === 1 && (
        <p className="mb-3 flex items-center gap-1.5 text-xs text-ink-500"><Sparkles size={13} /> 首次记录，暂无演进历史</p>
      )}
      <div className="relative">
        {chain.length > 1 && <div className="absolute left-[7px] top-3 bottom-3 w-px bg-ink-300/60" />}
        <div className="space-y-4">
          {chain.map((m, i) => {
            const isCurrent = m.superseded_by === null;
            const meta = kindMeta(m.kind);
            return (
              <motion.div key={m.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }} className="relative flex gap-4">
                <div className="relative z-10 mt-1.5 shrink-0">
                  {isCurrent ? (
                    <span className="relative flex h-4 w-4">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-400 opacity-60" />
                      <span className="relative inline-flex h-4 w-4 rounded-full border-2 border-surface bg-brand-600" />
                    </span>
                  ) : (
                    <span className="block h-4 w-4 rounded-full border-2 border-surface bg-ink-300" />
                  )}
                </div>
                <div className={`flex-1 rounded-xl border p-3 ${isCurrent ? "border-brand-500/30 bg-brand-50/40" : "border-ink-900/5 bg-surface opacity-80"}`}>
                  <div className="mb-1.5 flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${meta.cls}`}>{meta.label}</span>
                    {isCurrent ? <Badge tone="green">当前有效</Badge> : <Badge tone="gray"><Archive size={11} className="mr-1" />已取代</Badge>}
                    {m.subject && <span className="text-xs font-medium text-ink-700">· {m.subject}</span>}
                  </div>
                  <p className={`text-sm leading-relaxed ${isCurrent ? "text-ink-900" : "text-ink-500"}`}>{m.content}</p>
                  <div className="mt-2 space-y-1">
                    <Meter label="重要性" value={m.importance} />
                    <Meter label="置信度" value={m.confidence} />
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-500">
                    <span className="inline-flex items-center gap-1"><Clock size={11} />{fmt(m.created_at)}</span>
                    <span>有效期 {fmt(m.valid_from)} → {m.valid_to ? fmt(m.valid_to) : "至今"}</span>
                    <span>命中 {m.access_count} 次</span>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}