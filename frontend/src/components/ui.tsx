import { clsx } from "clsx";
import { motion } from "motion/react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Button({ className, variant = "primary", size = "md", ...p }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger"; size?: "sm" | "md" }) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all active:scale-[.97] disabled:opacity-50 disabled:pointer-events-none",
        size === "sm" ? "px-3 py-1.5 text-sm" : "px-4 py-2.5 text-sm",
        variant === "primary" && "bg-brand-600 text-white hover:bg-brand-700 shadow-sm",
        variant === "ghost" && "text-ink-700 hover:bg-ink-900/5",
        variant === "danger" && "bg-red-600 text-white hover:bg-red-700",
        className
      )}
      {...p}
    />
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={clsx("rounded-[var(--radius-card)] bg-surface shadow-[var(--shadow-card)] border border-ink-900/5", className)}>{children}</div>;
}

export function Badge({ tone = "gray", children }: { tone?: "gray" | "brand" | "green" | "amber" | "red"; children: ReactNode }) {
  const map = {
    gray: "bg-ink-300/30 text-ink-700", brand: "bg-brand-100 text-brand-700",
    green: "bg-emerald-100 text-emerald-700", amber: "bg-amber-100 text-amber-700", red: "bg-red-100 text-red-700",
  };
  return <span className={clsx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", map[tone])}>{children}</span>;
}

export function Skeleton({ className }: { className?: string }) {
  return <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.4 }}
    className={clsx("rounded-lg bg-ink-300/30", className)} />;
}