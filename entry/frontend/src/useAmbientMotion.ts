import { createContext, useCallback, useLayoutEffect, useState } from "react";

const storageKey = "modus.ambient-motion";
const readPreference = (): 'auto' | 'on' | 'off' => {
  try { const value = localStorage.getItem(storageKey); return value === 'on' || value === 'off' ? value : 'auto'; }
  catch { return 'auto'; }
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
  // System preference is the default. An explicit in-app choice can opt into
  // gentle opacity-only motion, without changing any operating-system setting.
  const enabled = preferred === 'on' || preferred === 'auto' && !reduced;

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
    const next = enabled ? 'off' : 'on';
    try { localStorage.setItem(storageKey, next); }
    catch { /* Preference remains usable when storage is unavailable. */ }
    setPreferred(next);
  }, [enabled]);
  return { enabled, reduced, toggle };
}
