import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, Radio } from "lucide-react";
import { Meetings } from "../lib/api";
import ExportMenu from "../components/ExportMenu";
import TranscriptView from "../components/transcript/TranscriptView";
import SummaryPanel from "../components/summary/SummaryPanel";
import LiveTranscription from "../components/live/LiveTranscription";
import Placeholder from "../pages/Placeholder";
import { format } from "date-fns";

const TABS = [
  { key: "summary", label: "纪要" },
  { key: "transcript", label: "转录" },
  { key: "live", label: "实时" },
  { key: "settings", label: "设置" },
] as const;
type Tab = typeof TABS[number]["key"];

export default function MeetingDetail() {
  const { id } = useParams();
  const [tab, setTab] = useState<Tab>("summary");
  const { data: m } = useQuery({ queryKey: ["meeting", id], queryFn: () => Meetings.get(id!) });

  return (
    <div className="mx-auto max-w-5xl">
      <Link to="/meetings" className="mb-4 inline-flex items-center gap-1 text-sm text-ink-500 hover:text-ink-900"><ArrowLeft size={16} /> 返回列表</Link>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ viewTransitionName: `mt-${id}` }}>{m?.title ?? "加载中…"}</h1>
          <p className="mt-1 text-sm text-ink-500">创建于 {m ? format(new Date(m.created_at), "yyyy-MM-dd HH:mm") : "…"}</p>
        </div>
        <div className="flex gap-2">
          <Link to={`/meetings/${id}`} onClick={() => setTab("live")}
            className="flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-600 active:scale-[.97]">
            <Radio size={16} /> 开始录制
          </Link>
          {m && <ExportMenu id={m.id} />}
        </div>
      </div>

      <div className="mb-6 flex gap-1 border-b border-black/5">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`relative px-4 py-2 text-sm font-medium transition ${tab === t.key ? "text-brand-600" : "text-ink-500 hover:text-ink-900"}`}>
            {t.label}
            {tab === t.key && <motion.span layoutId="detail-tab" className="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-brand-600" />}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: .18 }}>
          {tab === "summary" && <SummaryPanel id={id!} />}
          {tab === "transcript" && <TranscriptView id={id!} />}
          {tab === "live" && <LiveTranscription id={id!} />}
          {tab === "settings" && <Placeholder title="会议设置：重命名 / 删除 / 同意范围 / 分享（P3）" />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}