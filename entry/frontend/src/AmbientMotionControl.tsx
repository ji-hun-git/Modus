import { useContext } from "react";
import { Pause, Play } from "lucide-react";
import { AmbientMotionContext } from "./useAmbientMotion";

export default function AmbientMotionControl({ compact = false }: { compact?: boolean }) {
  const { enabled, reduced, toggle } = useContext(AmbientMotionContext);
  const label = enabled ? "Pause ambient motion" : reduced ? "Enable gentle motion" : "Resume ambient motion";
  return <button type="button" className={compact ? "ambient-motion-toggle" : "ambient-motion-menu"}
    onClick={toggle} aria-label={label} title={reduced && !enabled ? 'Motion is reduced by default. Choose to enable gentle breathing.' : label}>
    {enabled ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
    {!compact && <span>{enabled ? "Pause motion" : reduced ? "Enable gentle motion" : "Resume motion"}</span>}
  </button>;
}
