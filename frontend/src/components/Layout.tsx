import type { CSSProperties } from "react";
import { motion } from "motion/react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router";
import { clsx } from "clsx";
import { LayoutDashboard, MessagesSquare, Brain, ScrollText, LogOut, Radio, Search, Sun, Moon } from "lucide-react";
import { useAuth } from "../store/auth";
import { useTheme } from "../store/theme";

const nav = [
  { to: "/meetings", label: "会议",   icon: LayoutDashboard, color: "var(--color-mod-meeting)" },
  { to: "/search",   label: "搜索",   icon: Search,          color: "var(--color-mod-search)" },
  { to: "/agent",    label: "Agent",  icon: MessagesSquare,  color: "var(--color-mod-agent)" },
  { to: "/memory",   label: "记忆库", icon: Brain,           color: "var(--color-mod-memory)" },
  { to: "/audit",    label: "审计",   icon: ScrollText,      color: "var(--color-mod-audit)" },
];

export default function Layout() {
  const logout = useAuth((s) => s.logout);
  const nav2 = useNavigate();
  const { pathname } = useLocation();
  const theme = useTheme((s) => s.theme);
  const toggleTheme = useTheme((s) => s.toggle);

  const accent = nav.find((n) => pathname.startsWith(n.to))?.color ?? "var(--color-mod-dashboard)";
  const rootStyle = {
    "--color-accent": accent,
    "--color-accent-soft": `color-mix(in srgb, ${accent} 14%, transparent)`,
  } as CSSProperties;

  return (
    <div style={rootStyle} className="flex h-screen overflow-hidden">
      <aside className="w-60 shrink-0 border-r border-[var(--color-line)] bg-sidebar flex flex-col">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-[var(--color-line)]">
          <Radio style={{ color: accent }} size={22} />
          <span className="font-semibold tracking-tight">会议助理</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map(({ to, label, icon: Icon, color }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => clsx(
                "relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                !isActive && "text-ink-500 hover:text-ink-900 hover:bg-ink-900/5"
              )}>
              {({ isActive }) => (<>
                {isActive && <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-xl"
                  style={{ backgroundColor: `color-mix(in srgb, ${color} 14%, transparent)`, viewTransitionName: "nav-pill" }} />}
                <Icon size={18} className="relative" style={{ color: isActive ? color : undefined }} />
                <span className="relative" style={{ color: isActive ? color : undefined }}>{label}</span>
              </>)}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 space-y-1 border-t border-[var(--color-line)]">
          <button onClick={toggleTheme}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink-500 hover:text-ink-900 hover:bg-ink-900/5 transition-colors">
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            {theme === "dark" ? "浅色模式" : "夜读模式"}
          </button>
          <button onClick={() => { logout(); nav2("/login"); }}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink-500 hover:text-danger hover:bg-danger/10 transition-colors">
            <LogOut size={18} /> 退出登录
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-canvas">
        <Outlet />
      </main>
    </div>
  );
}