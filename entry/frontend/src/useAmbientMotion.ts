import { createContext, useCallback, useLayoutEffect, useState } from "react";

const storageKey = "modus.ambient-motion";
const readPreference = () => {
  try { return localStorage.getItem(storageKey) !== "off"; }
  catch { return true; }
};

export const AmbientMotionContext = createContext({
  enabled: false, reduced: false, toggle: () => {},
});

export default function useAmbientMotion() {
  const [preferred, setPreferred] = useState(readPreference);
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [visible, setVisible] = useState(() =>
    typeof document === "undefined" || document.visibilityState !== "hidden");
  const enabled = preferred && !reduced;

  useLayoutEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncReduced = () => setReduced(media.matches);
    const syncVisibility = () => setVisible(document.visibilityState !== "hidden");
    const syncStorage = (event: StorageEvent) => {
      if (event.key === storageKey || event.key === null) setPreferred(readPreference());
    };
    syncReduced();
    syncVisibility();
    media.addEventListener("change", syncReduced);
    document.addEventListener("visibilitychange", syncVisibility);
    window.addEventListener("storage", syncStorage);
    return () => {
      media.removeEventListener("change", syncReduced);
      document.removeEventListener("visibilitychange", syncVisibility);
      window.removeEventListener("storage", syncStorage);
    };
  }, []);

  useLayoutEffect(() => {
    document.documentElement.dataset.ambientMotion = enabled && visible ? "running" : "paused";
    return () => { delete document.documentElement.dataset.ambientMotion; };
  }, [enabled, visible]);

  const toggle = useCallback(() => {
    if (reduced) return;
    setPreferred(previous => {
      const next = !previous;
      try { localStorage.setItem(storageKey, next ? "on" : "off"); }
      catch { /* Preference remains usable when storage is unavailable. */ }
      return next;
    });
  }, [reduced]);
  return { enabled, reduced, toggle };
}
