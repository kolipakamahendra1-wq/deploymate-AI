import { useEffect, useState, type ReactNode } from "react";
import { Canvas } from "@react-three/fiber";

export const INK = "#16222C";
export const PROV_COLOR = { fact: "#0E8A7D", assumption: "#C98A00", unknown: "#8A97A1" } as const;
export const COBALT = "#2B4EFF";

export function useReducedMotion() {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setReduced(mq.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

interface FrameProps {
  label: string;
  /** Accessible, keyboard-friendly equivalent of the scene. */
  list: ReactNode;
  /** Static 2D diagram shown when the user prefers reduced motion. */
  flat?: ReactNode;
  caption?: string;
  height?: number;
  empty?: string;
  isEmpty?: boolean;
  camera?: { position: [number, number, number]; fov?: number };
  children: ReactNode;
}

/** Shared wrapper for every 3D scene: list toggle, 2D fallback, accessible label. */
export function SceneFrame({ label, list, flat, caption, height = 380, empty, isEmpty, camera, children }: FrameProps) {
  const reduced = useReducedMotion();
  const [showList, setShowList] = useState(false);
  let view: ReactNode;
  if (isEmpty) view = <p className="grid h-full place-items-center px-6 text-center text-ink-soft">{empty}</p>;
  else if (showList) view = <div className="h-full overflow-auto p-4 text-sm">{list}</div>;
  else if (reduced) view = flat ?? <div className="h-full overflow-auto p-4 text-sm">{list}</div>;
  else view = (
    <div role="img" aria-label={label} className="h-full">
      <Canvas dpr={[1, 1.5]} camera={{ position: camera?.position ?? [0, 1, 11], fov: camera?.fov ?? 45 }}>
        {children}
      </Canvas>
    </div>
  );
  return (
    <figure className="m-0">
      <div className="relative overflow-hidden rounded-lg border border-line bg-panel" style={{ height }}>
        {view}
        {!isEmpty && (
          <button
            onClick={() => setShowList((v) => !v)}
            aria-pressed={showList}
            className="absolute right-3 top-3 rounded border border-line bg-panel px-2 py-1 text-xs font-medium hover:bg-paper"
          >
            {showList ? "Show diagram" : "Show list view"}
          </button>
        )}
      </div>
      {caption && <figcaption className="mt-2 text-xs text-ink-soft">{caption}{reduced ? "" : " Drag to orbit."}</figcaption>}
    </figure>
  );
}
