import { motion } from "motion/react";
import { AlertTriangle, Check, X } from "lucide-react";
import type { ConfirmationOut } from "../../lib/types";
import { Button } from "../ui";

export default function ConfirmationCard({ c, busy, onApprove, onReject }: {
  c: ConfirmationOut; busy: boolean; onApprove: () => void; onReject: () => void;
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border-2 border-amber-300 bg-amber-50 p-5">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 shrink-0 text-amber-600" size={22} />
        <div className="flex-1">
          <h4 className="font-semibold text-amber-900">需要人工确认 · {c.tool}</h4>
          {c.message && <p className="mt-1 text-sm text-amber-800">{c.message}</p>}
          {c.reason && <p className="mt-1 text-xs text-amber-700">理由：{c.reason}</p>}
          {c.args && Object.keys(c.args).length > 0 && (
            <pre className="mt-2 overflow-x-auto rounded-lg bg-white/70 p-3 text-xs text-ink-700">{JSON.stringify(c.args, null, 2)}</pre>
          )}
          <div className="mt-4 flex gap-2">
            <Button onClick={onApprove} disabled={busy}><Check size={16} /> 批准执行</Button>
            <Button variant="danger" onClick={onReject} disabled={busy}><X size={16} /> 拒绝</Button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}