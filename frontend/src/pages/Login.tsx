import { useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "motion/react";
import toast from "react-hot-toast";
import { Auth, errMsg } from "../lib/api";
import { useAuth } from "../store/auth";
import { Button } from "../components/ui";


export default function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [pwd, setPwd] = useState("");
  const [busy, setBusy] = useState(false);
  const setToken = useAuth((s) => s.setToken);
  const nav = useNavigate();

   async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "register") { await Auth.register({ email, password: pwd }); toast.success("注册成功，正在登录"); }
      const t = await Auth.login(new URLSearchParams({ username: email, password: pwd }));
      setToken(t.access_token);
      nav("/meetings", { viewTransition: true });
    } catch (err: any) {
      toast.error(errMsg(err, "失败，请重试"));
    } finally { setBusy(false); }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-gradient-to-br from-brand-50 via-canvas to-brand-100 p-6">
      <motion.div initial={{ opacity: 0, y: 24, scale: .96 }} animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: "spring", stiffness: 260, damping: 24 }}
        className="w-full max-w-sm rounded-2xl bg-surface p-8 shadow-[var(--shadow-card)] border border-ink-900/5">
        <h1 className="text-2xl font-semibold tracking-tight">会议助理</h1>
        <p className="text-sm text-ink-500 mt-1">AI 驱动的会议记录与洞察</p>

        <div className="relative mt-6 grid grid-cols-2 rounded-xl bg-ink-900/5 p-1 text-sm font-medium">
          {(["login", "register"] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)}
              className={clsxTab(mode === m)}>{m === "login" ? "登录" : "注册"}</button>
          ))}
          <motion.span layoutId="auth-tab" className="absolute inset-y-1 w-[calc(50%-4px)] rounded-lg bg-surface shadow-sm"
            style={{ left: mode === "login" ? 4 : "50%" }} />
        </div>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="邮箱"
            className="w-full rounded-xl border border-ink-300/60 px-4 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition" />
          <input type="password" required minLength={6} value={pwd} onChange={(e) => setPwd(e.target.value)} placeholder="密码（≥6位）"
            className="w-full rounded-xl border border-ink-300/60 px-4 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition" />
          <Button type="submit" disabled={busy} className="w-full">{busy ? "处理中…" : mode === "login" ? "登录" : "注册并登录"}</Button>
        </form>
      </motion.div>
    </div>
  );
}
const clsxTab = (active: boolean) => `relative z-10 py-1.5 rounded-lg transition-colors ${active ? "text-brand-700" : "text-ink-500"}`;