import {
  LogIn, Plus, Trash2, RotateCcw, CheckCircle, XCircle, Sparkles, Link2, Link2Off,
  Eye, Download, Bot, Wrench, BrainCircuit, GitBranch, ScrollText,
} from "lucide-react";

export const AUDIT_META: Record<string, { label: string; icon: any; cls: string }> = {
  "user.login":        { label: "登录",       icon: LogIn,        cls: "bg-blue-100 text-blue-700" },
  "meeting.create":    { label: "创建会议",   icon: Plus,         cls: "bg-emerald-100 text-emerald-700" },
  "meeting.delete":    { label: "删除会议",   icon: Trash2,       cls: "bg-red-100 text-red-700" },
  "meeting.restore":   { label: "恢复会议",   icon: RotateCcw,    cls: "bg-amber-100 text-amber-700" },
  "consent.grant":     { label: "授权",       icon: CheckCircle,  cls: "bg-emerald-100 text-emerald-700" },
  "consent.revoke":    { label: "撤回授权",   icon: XCircle,      cls: "bg-red-100 text-red-700" },
  "summary.generate":  { label: "生成纪要",   icon: Sparkles,     cls: "bg-purple-100 text-purple-700" },
  "share.create":      { label: "创建分享",   icon: Link2,        cls: "bg-brand-100 text-brand-700" },
  "share.revoke":      { label: "撤销分享",   icon: Link2Off,     cls: "bg-red-100 text-red-700" },
  "share.access":      { label: "访问分享",   icon: Eye,          cls: "bg-blue-100 text-blue-700" },
  "export":            { label: "导出",       icon: Download,     cls: "bg-ink-300/30 text-ink-700" },
  "agent.run":         { label: "Agent 执行", icon: Bot,          cls: "bg-purple-100 text-purple-700" },
  "agent.action":      { label: "Agent 动作", icon: Wrench,       cls: "bg-purple-100 text-purple-700" },
  "memory.write":      { label: "写入记忆",   icon: BrainCircuit, cls: "bg-emerald-100 text-emerald-700" },
  "memory.supersede":  { label: "记忆演进",   icon: GitBranch,    cls: "bg-amber-100 text-amber-700" },
};

export function auditMeta(a: string) {
  return AUDIT_META[a] ?? { label: a, icon: ScrollText, cls: "bg-ink-300/30 text-ink-700" };
}