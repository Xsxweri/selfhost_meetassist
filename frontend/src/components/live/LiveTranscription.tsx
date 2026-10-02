import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import toast from "react-hot-toast";
import { Mic, Square, ShieldCheck } from "lucide-react";
import { Consents } from "../../lib/api";
import { useLiveTranscription } from "../../hooks/useLiveTranscription";
import { Button, Badge } from "../ui";
import Waveform from "./Waveform";

export default function LiveTranscription({ id }: { id: string }) {
  const qc = useQueryClient();
  const live = useLiveTranscription(id);
  const { data: consents } = useQuery({ queryKey: ["consents", id], queryFn: () => Consents.status(id) });
  const granted = consents?.find((c) => c.consent_type === "recording")?.granted ?? false;

  const grant = async () => {
    try { await Consents.grant(id, "recording"); qc.invalidateQueries({ queryKey: ["consents", id] }); toast.success("已授权录音"); }
    catch { toast.error("授权失败"); }
  };

  if (!granted) {
    return (
      <motion.div initial={{ opacity: 0, scale: .98 }} animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center gap-4 rounded-[var(--radius-card)] bg-surface p-12 text-center shadow-[var(--shadow-card)]">
        <ShieldCheck size={40} className="text-brand-500" />
        <div>
          <h3 className="text-lg font-semibold">录音授权</h3>
          <p className="mt-1 max-w-md text-sm text-ink-500">实时转写需要录制音频。授权后本会议将记录音频并转写为文字，操作会留痕审计。</p>
        </div>
        <Button onClick={grant}><ShieldCheck size={16} /> 我同意录音并转写</Button>
      </motion.div>
    );
  }

  const recording = live.status === "recording" || live.status === "connecting";
  return (
    <div className="space-y-4">
      <div className="rounded-[var(--radius-card)] bg-surface p-6 shadow-[var(--shadow-card)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {recording && <span className="relative flex h-3 w-3"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" /><span className="relative inline-flex h-3 w-3 rounded-full bg-red-500" /></span>}
            <span className="font-semibold">{live.status === "connecting" ? "连接中" : recording ? "录制中" : live.status === "ended" ? "已结束" : "准备就绪"}</span>
          </div>
          {!recording
            ? <Button onClick={live.start}><Mic size={16} /> 开始录制</Button>
            : <Button variant="danger" onClick={live.stop}><Square size={16} /> 结束</Button>}
        </div>
        <Waveform level={live.level} active={recording} />
        {live.error && <p className="mt-2 text-sm text-red-500">{live.error}</p>}
      </div>

      <div className="space-y-2">
        <AnimatePresence initial={false}>
          {live.segments.map((seg, i) => (
            <motion.div key={`${seg.start}-${i}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className="flex gap-4 rounded-xl bg-surface p-4 shadow-[var(--shadow-card)]">
              <div className="w-16 shrink-0 pt-0.5 font-mono text-xs text-ink-500">{seg.start.toFixed(1)}s</div>
              <div className="flex-1">
                <Badge tone="brand">{seg.speaker}</Badge>
                <p className="mt-1 text-sm leading-relaxed text-ink-900">{seg.text}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {!live.segments.length && <p className="py-12 text-center text-sm text-ink-500">点「开始录制」，字幕每 5 秒实时出现</p>}
      </div>
    </div>
  );
}