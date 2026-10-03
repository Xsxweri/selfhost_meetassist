import { useState } from "react";
import type { InputHTMLAttributes, ReactNode } from "react";
import { useNavigate } from "react-router";
import { motion, useAnimation } from "motion/react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import {
  Mail, Lock, Eye, EyeOff, AlertTriangle, Loader2, CheckCircle2, LogIn, AudioLines,
} from "lucide-react";
import { Auth, errMsg } from "../lib/api";
import { useAuth } from "../store/auth";
import { Button } from "../components/ui";

const SLOGAN = "让每一次会议，都成为沉淀的智慧";
const FEATURES = ["实时转录与说话人识别", "AI 智能纪要与待办提取", "可检索的长期记忆库"];

function friendly(m: string) {
  const s = (m || "").toLowerCase();
  if (s.includes("incorrect") || m.includes("密码")) return "账号或密码错误";
  if (s.includes("rate") || s.includes("429") || m.includes("频繁")) return "尝试过于频繁，请 1 分钟后再试";
  if (s.includes("registered") || m.includes("已注册")) return "该邮箱已注册，请直接登录";
  if (s.includes("network")) return "网络连接失败，请检查后端服务";
  return m || "登录失败，请重试";
}

// 品牌区流动声波纹理
function WaveDecor() {
  return (
    <svg className="absolute inset-0 h-full w-full opacity-[.18]" preserveAspectRatio="none" viewBox="0 0 400 400">
      {Array.from({ length: 7 }).map((_, i) => (
        <motion.path key={i}
          d={`M0 ${60 + i * 48} Q 100 ${20 + i * 48} 200 ${60 + i * 48} T 400 ${60 + i * 48}`}
          fill="none" stroke="white" strokeWidth={1.5}
          animate={{ x: [0, 24, 0] }}
          transition={{ duration: 7 + i, repeat: Infinity, ease: "easeInOut" }} />
      ))}
    </svg>
  );
}

// 带聚焦光晕 + 中心延展下划线 + 错误态的输入框
function TextField({ icon: Icon, trailing, error, onCaps, ...props }:
  { icon: any; trailing?: ReactNode; error?: string; onCaps?: (on: boolean) => void }
  & InputHTMLAttributes<HTMLInputElement>) {
  const [focused, setFocused] = useState(false);
  const active = focused && !error;
  return (
    <div>
      <div
        className={clsx("relative flex items-center rounded-xl border bg-transparent transition-colors duration-200",
          error ? "border-[var(--color-danger)]" : active ? "border-[var(--color-accent)]" : "border-ink-300/60")}
        style={active ? { boxShadow: "0 0 0 3px var(--color-accent-soft)" } : undefined}>
        <Icon size={18} className={clsx("ml-3.5 shrink-0 transition-colors", active ? "text-[var(--color-accent)]" : "text-ink-500")} />
        <input
          {...props}
          onFocus={(e) => { setFocused(true); props.onFocus?.(e); }}
          onBlur={(e) => { setFocused(false); onCaps?.(false); props.onBlur?.(e); }}
          className="w-full bg-transparent px-3 py-3 text-sm text-ink-900 outline-none placeholder:text-ink-300"
        />
        {trailing && <div className="mr-2 flex shrink-0 items-center">{trailing}</div>}
        <motion.span
          className="pointer-events-none absolute bottom-0 left-0 h-0.5 w-full origin-center rounded-full bg-[var(--color-accent)]"
          initial={false} animate={{ scaleX: active ? 1 : 0 }} transition={{ duration: 0.3 }} />
      </div>
      {error && (
        <p className="mt-1.5 flex items-center gap-1 text-xs text-[var(--color-danger)]">
          <AlertTriangle size={12} /> {error}
        </p>
      )}
    </div>
  );
}

export default function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [pwd, setPwd] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPwd, setShowPwd] = useState(false);
  const [caps, setCaps] = useState(false);
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const controls = useAnimation();
  const nav = useNavigate();
  const login = useAuth((s) => s.login);
  const setUser = useAuth((s) => s.setUser);

  const capsCheck = (e: React.KeyboardEvent) => {
    if (typeof e.getModifierState === "function") setCaps(e.getModifierState("CapsLock"));
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy || success) return;
    setError("");
    setBusy(true);
    try {
      if (mode === "register") {
        await Auth.register({ email, password: pwd });
        toast.success("注册成功，正在登录…");
      }
      const t = await Auth.login(new URLSearchParams({ username: email, password: pwd }));
      login(t.access_token, remember);
      try { setUser(await Auth.me()); } catch { /* user 可延后补 */ }
      setSuccess(true);
      setTimeout(() => nav("/meetings", { replace: true }), 800);
    } catch (err: any) {
      setError(friendly(errMsg(err, "登录失败，请重试")));
      setBusy(false);
      controls.start({ x: [0, -12, 12, -10, 10, -6, 6, 0], transition: { duration: 0.5 } });
    }
  }

  const switchMode = () => { setMode(mode === "login" ? "register" : "login"); setError(""); };
  const forgot = () => toast("自托管部署，请联系管理员重置密码", { icon: "🔑" });

  return (
    <div className="grid min-h-dvh grid-cols-1 md:grid-cols-[3fr_2fr]">
      {/* 左侧 · 品牌沉浸区（<768px 隐藏） */}
      <aside className="relative hidden overflow-hidden bg-gradient-to-br from-[var(--color-accent)] to-[#1d4ed8] px-12 text-white md:flex md:flex-col md:justify-center lg:px-20">
        <WaveDecor />
        <div className="relative z-10 max-w-lg">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-white/15 backdrop-blur">
              <AudioLines size={24} />
            </div>
            <span className="text-xl font-semibold tracking-tight">会议助理</span>
          </div>
          <h2 className="mt-12 text-3xl font-bold leading-snug lg:text-[2.6rem]">{SLOGAN}</h2>
          <p className="mt-5 text-sm leading-relaxed text-white/70">
            AI 驱动的会议记录、洞察与长期记忆，把说过的每一句话，变成可复用的知识资产。
          </p>
          <ul className="mt-10 space-y-3 text-sm text-white/85">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-2.5">
                <CheckCircle2 size={16} className="text-white/60" /> {f}
              </li>
            ))}
          </ul>
        </div>
      </aside>

      {/* 右侧 · 交互操作区 */}
      <main className="flex min-h-dvh items-center justify-center overflow-y-auto bg-canvas px-6 py-10">
        <motion.div
          animate={controls}
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ type: "spring", stiffness: 260, damping: 26 }}
          className="w-full max-w-sm">
          {/* 移动端品牌露出 */}
          <div className="mb-8 flex items-center gap-2.5 md:hidden">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-[var(--color-accent)] text-white">
              <AudioLines size={20} />
            </div>
            <span className="text-lg font-semibold">会议助理</span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-ink-900">
            {mode === "login" ? "欢迎回来" : "创建账号"}
          </h1>
          <p className="mt-1.5 text-sm text-ink-500">
            {mode === "login" ? "登录你的账号，继续未完成的会议" : "注册后即可开始记录你的第一场会议"}
          </p>

          <form onSubmit={submit} className="mt-8 space-y-4" noValidate={false}>
            <TextField
              icon={Mail} type="email" required autoComplete="email"
              placeholder="邮箱地址" value={email}
              onChange={(e) => setEmail(e.target.value)} />

            <TextField
              icon={Lock} type={showPwd ? "text" : "password"} required minLength={6}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              placeholder={mode === "login" ? "密码" : "密码（≥6 位）"}
              value={pwd} onChange={(e) => setPwd(e.target.value)}
              onKeyDown={capsCheck} onKeyUp={capsCheck} onCaps={setCaps}
              trailing={
                <button type="button" onClick={() => setShowPwd((v) => !v)}
                  className="grid h-8 w-8 place-items-center rounded-lg text-ink-500 transition hover:bg-ink-900/5 hover:text-ink-900"
                  aria-label={showPwd ? "隐藏密码" : "显示密码"}>
                  {showPwd ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              } />

            {caps && (
              <p className="flex items-center gap-1.5 text-xs text-[var(--color-degrade)]">
                <AlertTriangle size={13} /> 大写锁定已开启，请注意密码大小写
              </p>
            )}

            {mode === "login" && (
              <div className="flex items-center justify-between pt-1 text-sm">
                <label className="flex cursor-pointer select-none items-center gap-2 text-ink-700">
                  <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)}
                    className="h-4 w-4 rounded accent-[var(--color-accent)]" />
                  记住我
                </label>
                <button type="button" onClick={forgot}
                  className="text-ink-500 transition hover:text-[var(--color-accent)]">忘记密码？</button>
              </div>
            )}

            <Button type="submit" disabled={busy || success} className="w-full py-3">
              {success ? (<><CheckCircle2 size={18} /> 登录成功，即将跳转…</>)
                : busy ? (<><Loader2 size={18} className="animate-spin" /> 登录中…</>)
                  : (<><LogIn size={18} /> {mode === "login" ? "登录" : "注册并登录"}</>)}
            </Button>

            {error && (
              <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-1.5 pt-1 text-sm text-[var(--color-danger)]">
                <AlertTriangle size={15} /> {error}
              </motion.p>
            )}
          </form>

          <p className="mt-7 text-center text-sm text-ink-500">
            {mode === "login" ? "还没有账号？" : "已有账号？"}
            <button type="button" onClick={switchMode}
              className="ml-1 font-medium text-[var(--color-accent)] transition hover:underline">
              {mode === "login" ? "立即注册" : "返回登录"}
            </button>
          </p>
        </motion.div>
      </main>
    </div>
  );
}