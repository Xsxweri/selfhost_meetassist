import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import toast from "react-hot-toast";
import { X, Link2, Copy, Trash2, Plus } from "lucide-react";
import { format } from "date-fns";
import { Shares, errMsg } from "../lib/api";
import { Button } from "./ui";

export default function ShareDialog({ meetingId, onClose }: { meetingId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [allowDownload, setAllowDownload] = useState(true);
  const [days, setDays] = useState(7);
  const [busy, setBusy] = useState(false);
  const { data: links } = useQuery({ queryKey: ["shares", meetingId], queryFn: () => Shares.list(meetingId) });

  const create = async () => {
    setBusy(true);
    try {
      await Shares.create(meetingId, { allow_download: allowDownload, expires_in_days: days });
      qc.invalidateQueries({ queryKey: ["shares", meetingId] });
      toast.success("分享链接已创建");
    } catch (e) { toast.error(errMsg(e, "创建失败")); }
    finally { setBusy(false); }
  };
  const revoke = async (token: string) => {
    try {
      await Shares.revoke(meetingId, token);
      qc.invalidateQueries({ queryKey: ["shares", meetingId] });
      toast.success("已撤销");
    } catch (e) { toast.error(errMsg(e, "撤销失败")); }
  };
  const copy = (token: string) => {
    navigator.clipboard.writeText(`${location.origin}/shared/${token}`);
    toast.success("链接已复制");
  };

  return (
    <motion.div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 p-4"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.div className="w-full max-w-lg rounded-2xl bg-surface p-6 shadow-xl"
        initial={{ scale: .95, y: 10 }} animate={{ scale: 1, y: 0 }} exit={{ scale: .95, y: 10 }}
        onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="flex items-center gap-2 font-semibold"><Link2 size={18} /> 分享此会议</h3>
          <button onClick={onClose} className="text-ink-500 hover:text-ink-900"><X size={18} /></button>
        </div>

        <div className="mb-4 space-y-3 rounded-xl bg-canvas p-4">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={allowDownload} onChange={(e) => setAllowDownload(e.target.checked)} className="accent-brand-600" />
            允许下载
          </label>
          <label className="flex items-center gap-2 text-sm">
            有效期
            <input type="number" min={1} max={365} value={days} onChange={(e) => setDays(+e.target.value)}
              className="w-20 rounded-lg border border-ink-900/10 px-2 py-1" /> 天
          </label>
          <Button onClick={create} disabled={busy} size="sm"><Plus size={16} /> 创建链接</Button>
        </div>

        <div className="max-h-64 space-y-2 overflow-y-auto">
          {links?.map((l) => {
            const active = !l.revoked_at && (!l.expires_at || new Date(l.expires_at) > new Date());
            return (
              <div key={l.id} className={`rounded-xl border p-3 ${active ? "border-ink-900/10" : "border-red-200 bg-red-50/50 opacity-70"}`}>
                <div className="flex items-center justify-between gap-2">
                  <code className="truncate text-xs text-ink-500">{location.origin}/shared/{l.token}</code>
                  <div className="flex shrink-0 gap-1">
                    <button onClick={() => copy(l.token)} className="rounded p-1 text-ink-500 hover:text-brand-600" title="复制"><Copy size={14} /></button>
                    {active && <button onClick={() => revoke(l.token)} className="rounded p-1 text-ink-500 hover:text-red-600" title="撤销"><Trash2 size={14} /></button>}
                  </div>
                </div>
                <div className="mt-1 flex gap-3 text-xs text-ink-500">
                  <span>{active ? "有效" : l.revoked_at ? "已撤销" : "已过期"}</span>
                  <span>{l.allow_download ? "可下载" : "禁止下载"}</span>
                  {l.expires_at && <span>至 {format(new Date(l.expires_at), "yyyy-MM-dd")}</span>}
                </div>
              </div>
            );
          })}
          {!links?.length && <p className="py-4 text-center text-sm text-ink-500">还没有分享链接</p>}
        </div>
      </motion.div>
    </motion.div>
  );
}