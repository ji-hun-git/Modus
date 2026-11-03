import { useContext } from "react";
import { Pause, Play } from "lucide-react";
import { AmbientMotionContext } from "./useAmbientMotion";

export default function AmbientMotionControl({ compact = false }: { compact?: boolean }) {
  const { enabled, reduced, toggle } = useContext(AmbientMotionContext);
  const label = reduced ? "Motion reduced by your system settings" : enabled ? "Pause ambient motion" : "Resume ambient motion";
  return <button type="button" className={compact ? "ambient-motion-toggle" : "ambient-motion-menu"}
    onClick={toggle} disabled={reduced} aria-label={label} title={label}>
    {enabled ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
    {!compact && <span>{reduced ? "Reduced motion" : enabled ? "Pause motion" : "Resume motion"}</span>}
  </button>;
}
