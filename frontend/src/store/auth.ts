import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { UserResponse } from "../lib/types";

interface AuthState {
  token: string | null;
  user: UserResponse | null;
  remember: boolean;
  login: (token: string, remember: boolean) => void;
  setToken: (t: string) => void;
  setUser: (u: UserResponse) => void;
  logout: () => void;
}

const dualStorage = {
  getItem: (n: string) => localStorage.getItem(n) ?? sessionStorage.getItem(n),
  setItem: (n: string, v: string) => {
    let remember = true;
    try { remember = JSON.parse(v)?.state?.remember ?? true; } catch { /* ignore */ }
    if (remember) { localStorage.setItem(n, v); sessionStorage.removeItem(n); }
    else { sessionStorage.setItem(n, v); localStorage.removeItem(n); }
  },
  removeItem: (n: string) => { localStorage.removeItem(n); sessionStorage.removeItem(n); },
};

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      remember: true,
      login: (token, remember) => set({ token, remember }),
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: "ma-auth", storage: createJSONStorage(() => dualStorage) }
  )
);