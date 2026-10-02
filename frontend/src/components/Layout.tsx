import { motion } from "motion/react";
import { NavLink, Outlet, useNavigate } from "react-router";
import { clsx } from "clsx";
import { LayoutDashboard, MessagesSquare, Brain, ScrollText, LogOut, Radio } from "lucide-react";
import { useAuth } from "../store/auth";

const nav = [
  { to: "/meetings", label: "会议", icon: LayoutDashboard },
  { to: "/agent", label: "Agent", icon: MessagesSquare },
  { to: "/memory", label: "记忆库", icon: Brain },
  { to: "/audit", label: "审计", icon: ScrollText },
];

export default function Layout() {
  const logout = useAuth((s) => s.logout);
  const nav2 = useNavigate();
  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-60 shrink-0 border-r border-ink-900/5 bg-surface flex flex-col">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-ink-900/5">
          <Radio className="text-brand-600" size={22} />
          <span className="font-semibold tracking-tight">会议助理</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} viewTransition
              className={({ isActive }) => clsx(
                "relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                isActive ? "text-brand-700" : "text-ink-500 hover:text-ink-900 hover:bg-ink-900/5"
              )}>
              {({ isActive }) => (<>
                {isActive && <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-xl bg-brand-50" style={{ viewTransitionName: "nav-pill" }} />}
                <Icon size={18} className="relative" /><span className="relative">{label}</span>
              </>)}
            </NavLink>
          ))}
        </nav>
        <button onClick={() => { logout(); nav2("/login"); }}
          className="m-3 flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink-500 hover:text-red-600 hover:bg-red-50 transition-colors">
          <LogOut size={18} /> 退出登录
        </button>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}