import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Download, FileText, FileType2, Hash } from "lucide-react";
import { downloadExport } from "../lib/api";

export default function ExportMenu({ id }: { id: string }) {
  const [open, setOpen] = useState(false);
  const items = [
    { fmt: "pdf" as const, label: "PDF", icon: FileText },
    { fmt: "docx" as const, label: "Word", icon: FileType2 },
    { fmt: "md" as const, label: "Markdown", icon: Hash },
  ];
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-[var(--shadow-card)] transition hover:bg-brand-700 active:scale-[.97]"
      >
        <Download size={16} /> 导出
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: .96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6, scale: .96 }}
            className="absolute right-0 z-20 mt-2 w-40 overflow-hidden rounded-xl bg-surface shadow-[var(--shadow-card)] ring-1 ring-black/5"
          >
            {items.map(({ fmt, label, icon: Icon }) => (
              <button key={fmt}
                onClick={() => { setOpen(false); downloadExport(id, fmt); }}
                className="flex items-center gap-2 px-4 py-2.5 text-sm text-ink-700 transition hover:bg-brand-50 hover:text-brand-600">
                <Icon size={16} /> {label}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}