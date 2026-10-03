import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "light" | "dark";
interface ThemeState {
  theme: Theme;
  toggle: () => void;
  apply: () => void;
}

export const useTheme = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "light",
      toggle: () => {
        set({ theme: get().theme === "light" ? "dark" : "light" });
        get().apply();
      },
      apply: () => {
        document.documentElement.classList.toggle("dark", get().theme === "dark");
      },
    }),
    { name: "ma-theme" }
  )
);