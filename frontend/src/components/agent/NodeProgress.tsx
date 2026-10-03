import { motion } from "motion/react";
import { Brain, Compass, GitBranch, Zap, Megaphone, ShieldCheck, AlertTriangle, Cpu } from "lucide-react";

const META: Record<string, { label: string; icon: any }> = {
  recall: { label: "记忆召回", icon: Brain },
  planner: { label: "规划", icon: Compass },
  router: { label: "路由", icon: GitBranch },
  human_gate: { label: "人工闸门", icon: AlertTriangle },
  executor: { label: "执行工具", icon: Zap },
  reporter: { label: "生成汇报", icon: Megaphone },
  audit: { label: "审计留痕", icon: ShieldCheck },
};

export default function NodeProgress({ trace }: { trace: string[] }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {trace.map((n, i) => {
        const meta = META[n] ?? { label: n, icon: Cpu };
        const Icon = meta.icon;
        const last = i === trace.length - 1;
        return (
          <motion.span key={i} initial={{ opacity: 0, scale: .8 }} animate={{ opacity: 1, scale: 1 }}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${last ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-700"}`}>
            <Icon size={13} /> {meta.label}
          </motion.span>
        );
      })}
      <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1 }} className="text-xs text-ink-500">思考中…</motion.span>
    </div>
  );
}