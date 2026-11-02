import { useLayoutEffect, useState } from "react";

export type Appearance = "dark" | "light" | "system";
const storageKey = "modus.appearance";
const valid = (value: string | null): value is Appearance =>
  value === "dark" || value === "light" || value === "system";

export default function useAppearance() {
  const [appearance, setAppearance] = useState<Appearance>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return valid(saved) ? saved : "dark";
    } catch { return "dark"; }
  });
  useLayoutEffect(() => {
    const system = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      document.documentElement.dataset.appearance = appearance === "system"
        ? (system.matches ? "dark" : "light") : appearance;
    };
    apply();
    system.addEventListener("change", apply);
    try { localStorage.setItem(storageKey, appearance); } catch { /* Optional preference. */ }
    return () => system.removeEventListener("change", apply);
  }, [appearance]);
  return [appearance, setAppearance] as const;
}
