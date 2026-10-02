import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UserResponse } from "../lib/types";

interface AuthState {
  token: string | null;
  user: UserResponse | null;
  setToken: (t: string) => void;
  setUser: (u: UserResponse) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: "ma-auth" }
  )
);