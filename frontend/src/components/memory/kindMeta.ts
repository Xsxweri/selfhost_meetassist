export const KIND_META: Record<string, { label: string; cls: string }> = {
  decision:   { label: "决策", cls: "bg-purple-100 text-purple-700" },
  action:     { label: "行动", cls: "bg-blue-100 text-blue-700" },
  preference: { label: "偏好", cls: "bg-amber-100 text-amber-700" },
  fact:       { label: "事实", cls: "bg-emerald-100 text-emerald-700" },
  entity:     { label: "实体", cls: "bg-rose-100 text-rose-700" },
};

export const KIND_KEYS = ["decision", "action", "preference", "fact", "entity"] as const;

export function kindMeta(k: string) {
  return KIND_META[k] ?? { label: k, cls: "bg-ink-300/30 text-ink-700" };
}