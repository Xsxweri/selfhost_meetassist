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
        variant === "primary" && "bg-[var(--color-accent)] text-white hover:brightness-110 shadow-sm",
        variant === "ghost" && "text-ink-700 hover:bg-ink-900/5",
        variant === "danger" && "bg-danger text-white hover:brightness-110",
        className
      )}
      {...p}
    />
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={clsx("rounded-[var(--radius-card)] bg-surface shadow-[var(--shadow-card)] border border-[var(--color-line)]", className)}>{children}</div>;
}

export function Badge({ tone = "gray", children }: { tone?: "gray" | "brand" | "green" | "amber" | "red"; children: ReactNode }) {
  const map = {
    gray: "bg-ink-300/30 text-ink-700",
    brand: "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
    green: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
    amber: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
    red: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300",
  };
  return <span className={clsx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", map[tone])}>{children}</span>;
}

export function Skeleton({ className }: { className?: string }) {
  return <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.4 }}
    className={clsx("rounded-lg bg-ink-300/30", className)} />;
}

export function PageHeader({ title, subtitle, icon: Icon, action, titleClassName }:
  { title: string; subtitle?: ReactNode; icon?: any; action?: ReactNode; titleClassName?: string }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        <span className="mt-1.5 h-8 w-1.5 shrink-0 rounded-full bg-[var(--color-accent)]" />
        <div>
          <div className="flex items-center gap-2">
            {Icon && <Icon size={20} style={{ color: "var(--color-accent)" }} />}
            <h1 className={clsx("text-2xl font-bold tracking-tight", titleClassName)}>{title}</h1>
          </div>
          {subtitle && <p className="mt-1 text-sm text-ink-500">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </div>
  );
}