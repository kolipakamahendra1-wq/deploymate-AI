import { useMemo, useState } from "react";
import { Edges, Line, OrbitControls, Text } from "@react-three/drei";
import type { Architecture, Layer } from "../api";
import { COBALT, INK, SceneFrame } from "./common";

const LAYERS: Layer[] = ["client", "api", "integration", "data"];
const Y: Record<Layer, number> = { client: 2.4, api: 0.8, integration: -0.8, data: -2.4 };
const BOUNDARY_COLORS = ["#B07800", "#0B7A6E", "#2B4EFF"];

type P = [number, number, number];

function positions(arch: Architecture): Record<string, P> {
  const out: Record<string, P> = {};
  for (const layer of LAYERS) {
    const comps = arch.components.filter((c) => c.layer === layer);
    comps.forEach((c, i) => { out[c.id] = [(i - (comps.length - 1) / 2) * 2.6, Y[layer], 0]; });
  }
  return out;
}

/**
 * A security boundary drawn as a translucent volume around each member component.
 * One bounding box would also swallow non-members that sit between them.
 */
function BoundaryVolume({ pts, color, name }: { pts: P[]; color: string; name: string }) {
  if (!pts.length) return null;
  const first = [...pts].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0];
  return (
    <group>
      {pts.map((p, i) => (
        <mesh key={i} position={p}>
          <boxGeometry args={[2.3, 0.85, 1.1]} />
          <meshBasicMaterial color={color} transparent opacity={0.16} depthWrite={false} />
        </mesh>
      ))}
      <Text position={[first[0] - 1.1, first[1] + 0.58, 0.56]} fontSize={0.17} color={color} anchorX="left">
        {name}
      </Text>
    </group>
  );
}

export default function ArchitectureScene({ arch, selected, onSelect }: {
  arch: Architecture; selected: string | null; onSelect: (id: string) => void;
}) {
  const pos = useMemo(() => positions(arch), [arch]);
  const [hover, setHover] = useState<string | null>(null);
  return (
    <SceneFrame
      label="3D architecture: layered planes with security boundaries"
      height={460}
      isEmpty={!arch.components.length}
      empty="Run the pipeline to generate the architecture."
      caption="Layers from top: client, API, integration, data. Tinted volumes are security boundaries. Click a component for details."
      camera={{ position: [0, 2.5, 11], fov: 45 }}
      list={
        <ul className="space-y-1">
          {arch.components.map((c) => (
            <li key={c.id}><button className="underline" onClick={() => onSelect(c.id)}>{c.name}</button> ({c.layer})</li>
          ))}
        </ul>
      }
    >
      <ambientLight intensity={0.95} />
      <directionalLight position={[4, 8, 6]} intensity={1} />
      {LAYERS.map((l) => (
        <group key={l} position={[0, Y[l] - 0.32, 0]}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[12, 2.2]} />
            <meshBasicMaterial color="#CFD8DE" transparent opacity={0.35} side={2} />
          </mesh>
          <Text position={[-5.8, 0.12, 1]} fontSize={0.2} color="#46555F" anchorX="left">{l.toUpperCase()}</Text>
        </group>
      ))}
      {arch.security_boundaries.map((b, i) => (
        <BoundaryVolume key={b.name} name={b.name} color={BOUNDARY_COLORS[i % BOUNDARY_COLORS.length]}
                        pts={b.components.map((id) => pos[id]).filter(Boolean)} />
      ))}
      {arch.flows.filter((f) => pos[f.source] && pos[f.target]).map((f, i) => (
        <Line key={i} points={[pos[f.source], pos[f.target]]} color="#46555F" lineWidth={1.2} transparent opacity={0.6} />
      ))}
      {arch.components.map((c) => {
        const on = selected === c.id || hover === c.id;
        return (
          <group key={c.id} position={pos[c.id]}>
            <mesh
              onClick={(e) => { e.stopPropagation(); onSelect(c.id); }}
              onPointerOver={(e) => { e.stopPropagation(); setHover(c.id); document.body.style.cursor = "pointer"; }}
              onPointerOut={() => { setHover(null); document.body.style.cursor = ""; }}
            >
              <boxGeometry args={[1.9, 0.45, 0.6]} />
              <meshBasicMaterial color={on ? COBALT : "#FFFFFF"} />
              <Edges color={COBALT} />
            </mesh>
            <Text position={[0, 0, 0.32]} fontSize={0.17} maxWidth={1.8} color={on ? "#FFFFFF" : INK} anchorX="center" anchorY="middle">
              {c.name}
            </Text>
          </group>
        );
      })}
      <OrbitControls enablePan={false} minDistance={6} maxDistance={18} />
    </SceneFrame>
  );
}
