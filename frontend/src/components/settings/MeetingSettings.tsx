import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Trash2, Mic, UserCheck } from "lucide-react";
import { Meetings, Consents, errMsg } from "../../lib/api";
import type { ConsentType } from "../../lib/types";
import { Button } from "../ui";

const CONSENTS: { type: ConsentType; label: string; desc: string; icon: any }[] = [
  { type: "recording", label: "录音授权", desc: "允许对本场会议进行音频录制与实时转写", icon: Mic },
  { type: "speaker_id", label: "说话人识别", desc: "允许区分并标注不同发言人身份", icon: UserCheck },
];

export default function MeetingSettings({ id }: { id: string }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const { data: meeting } = useQuery({ queryKey: ["meeting", id], queryFn: () => Meetings.get(id) });
  const { data: status } = useQuery({ queryKey: ["consent-status", id], queryFn: () => Consents.status(id) });

  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState<ConsentType | null>(null);

  useEffect(() => { if (meeting) setTitle(meeting.title); }, [meeting?.title]);

  const rename = async () => {
    if (!title.trim()) return toast.error("标题不能为空");
    setSaving(true);
    try {
      await Meetings.update(id, { title: title.trim() });
      qc.invalidateQueries({ queryKey: ["meeting", id] });
      qc.invalidateQueries({ queryKey: ["meetings"] });
      toast.success("已重命名");
    } catch (e) { toast.error(errMsg(e, "重命名失败")); }
    finally { setSaving(false); }
  };

  const toggleConsent = async (type: ConsentType, granted: boolean) => {
    setPending(type);
    try {
      if (granted) await Consents.revoke(id, type);
      else await Consents.grant(id, type);
      await qc.invalidateQueries({ queryKey: ["consent-status", id] });
      toast.success(granted ? "已撤回授权" : "已授权");
    } catch (e) { toast.error(errMsg(e, "操作失败")); }
    finally { setPending(null); }
  };

  const remove = async () => {
    if (!window.confirm("确认删除此会议？将软删除并自动撤回录音授权。")) return;
    setDeleting(true);
    try {
      await Meetings.remove(id);
      qc.invalidateQueries({ queryKey: ["meetings"] });
      toast.success("会议已删除");
      nav("/meetings");
    } catch (e) { toast.error(errMsg(e, "删除失败")); setDeleting(false); }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-[var(--radius-card)] bg-surface p-6 shadow-[var(--shadow-card)]">
        <h3 className="mb-4 font-semibold">重命名会议</h3>
        <div className="flex gap-2">
          <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={500}
            className="flex-1 rounded-lg border border-ink-900/10 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-400" />
          <Button onClick={rename} disabled={saving || !title.trim() || title.trim() === meeting?.title}>保存</Button>
        </div>
      </section>

      <section className="rounded-[var(--radius-card)] bg-surface p-6 shadow-[var(--shadow-card)]">
        <h3 className="mb-1 font-semibold">同意范围</h3>
        <p className="mb-4 text-sm text-ink-500">授权为 append-only 留痕，每次开关都会记入审计日志。</p>
        <div className="space-y-3">
          {CONSENTS.map(({ type, label, desc, icon: Icon }) => {
            const granted = status?.find((s) => s.consent_type === type)?.granted ?? false;
            return (
              <div key={type} className="flex items-center justify-between gap-4 rounded-xl bg-canvas p-4">
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600"><Icon size={16} /></span>
                  <div>
                    <div className="text-sm font-medium text-ink-900">{label}</div>
                    <div className="text-xs text-ink-500">{desc}</div>
                  </div>
                </div>
                <button onClick={() => toggleConsent(type, granted)} disabled={pending === type} aria-pressed={granted}
                  className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-60 disabled:cursor-not-allowed ${granted ? "bg-brand-600" : "bg-ink-300"}`}>
                  <span className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${granted ? "translate-x-5" : "translate-x-0"}`} />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <section className="rounded-[var(--radius-card)] border border-red-200 bg-red-50/40 p-6">
        <h3 className="mb-1 font-semibold text-red-700">危险操作</h3>
        <p className="mb-4 text-sm text-red-600/80">删除为软删除，会自动撤回录音授权并记入审计。</p>
        <Button variant="danger" onClick={remove} disabled={deleting}>
          <Trash2 size={16} /> {deleting ? "删除中…" : "删除会议"}
        </Button>
      </section>
    </div>
  );
}