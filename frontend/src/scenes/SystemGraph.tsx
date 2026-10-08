import { useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Line, OrbitControls, Text } from "@react-three/drei";
import type { Group } from "three";
import type { Architecture, SystemNode } from "../api";

/** Colour per layer; unconfirmed systems are drawn as hollow wireframes. */
const COLORS = { fact: "#0E8A7D", assumption: "#C98A00", unknown: "#8A97A1" } as const;

interface N { id: string; label: string; pos: [number, number, number]; solid: boolean; color: string; big: boolean }

function layout(systems: SystemNode[], arch: Architecture): { nodes: N[]; links: [string, string][] } {
  const nodes: N[] = systems.map((s, i) => ({
    id: s.id,
    label: s.name,
    pos: [i === 0 ? -4.4 : 4.4, 0, 0],
    solid: s.confirmed,
    color: COLORS[s.provenance],
    big: true,
  }));
  // Architecture components that are the customer systems themselves reuse the system node.
  const alias: Record<string, string> = {};
  const inner = arch.components.filter((c) => {
    const sys = systems.find((s) => s.name === c.name);
    if (sys) alias[c.id] = sys.id;
    return !sys;
  });
  const layers = [...new Set(inner.map((c) => c.layer))];
  layers.forEach((layer, row) => {
    const inLayer = inner.filter((c) => c.layer === layer);
    inLayer.forEach((c, i) => {
      const x = (i - (inLayer.length - 1) / 2) * 3.2;
      const y = (layers.length - 1) / 2 * 1.3 - row * 1.3;
      nodes.push({ id: c.id, label: c.name, pos: [x, y, -0.8], solid: true, color: "#2B4EFF", big: false });
    });
  });
  const links = arch.flows.map((f) => [alias[f.source] ?? f.source, alias[f.target] ?? f.target] as [string, string]);
  if (systems.length === 2 && links.length === 0) links.push([systems[0].id, systems[1].id]);
  return { nodes, links };
}

function Node({ n, delay }: { n: N; delay: number }) {
  const ref = useRef<Group>(null);
  const t0 = useRef(0);
  useFrame((_, dt) => {
    if (!ref.current) return;
    t0.current += dt;
    const k = Math.min(1, Math.max(0, (t0.current - delay) * 2.5)); // appear as discovered
    ref.current.scale.setScalar(k);
  });
  const r = n.big ? 0.55 : 0.28;
  return (
    <group ref={ref} position={n.pos} scale={0}>
      <mesh>
        <sphereGeometry args={[r, 24, 24]} />
        {n.solid ? (
          <meshStandardMaterial color={n.color} roughness={0.5} />
        ) : (
          <meshBasicMaterial color={n.color} wireframe />
        )}
      </mesh>
      <Text position={[0, r + 0.28, 0]} fontSize={0.22} color="#16222C" anchorX="center">
        {n.label}
      </Text>
    </group>
  );
}

function Scene({ nodes, links }: { nodes: N[]; links: [string, string][] }) {
  const pos = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n.pos])), [nodes]);
  return (
    <>
      <ambientLight intensity={0.9} />
      <directionalLight position={[4, 6, 5]} intensity={1.2} />
      {nodes.map((n, i) => <Node key={n.id} n={n} delay={i * 0.25} />)}
      {links.filter(([a, b]) => pos[a] && pos[b]).map(([a, b], i) => (
        <Line key={i} points={[pos[a], pos[b]]} color="#46555F" lineWidth={1} transparent opacity={0.55} />
      ))}
      <OrbitControls enablePan={false} minDistance={5} maxDistance={14} />
    </>
  );
}

function Flat({ nodes, links }: { nodes: N[]; links: [string, string][] }) {
  return (
    <svg viewBox="-6 -3 12 6" role="img" aria-label="System diagram" className="h-full w-full">
      {links.map(([a, b], i) => {
        const p = nodes.find((n) => n.id === a)?.pos;
        const q = nodes.find((n) => n.id === b)?.pos;
        return p && q ? <line key={i} x1={p[0]} y1={-p[1]} x2={q[0]} y2={-q[1]} stroke="#46555F" strokeOpacity={0.5} strokeWidth={0.03} /> : null;
      })}
      {nodes.map((n) => (
        <g key={n.id} transform={`translate(${n.pos[0]},${-n.pos[1]})`}>
          <circle r={n.big ? 0.5 : 0.25} fill={n.solid ? n.color : "none"} stroke={n.color} strokeWidth={0.06} strokeDasharray={n.solid ? "" : "0.15"} />
          <text y={n.big ? -0.7 : -0.4} textAnchor="middle" fontSize={0.28} fill="#16222C">{n.label}</text>
        </g>
      ))}
    </svg>
  );
}

export default function SystemGraph({ systems, arch }: { systems: SystemNode[]; arch: Architecture }) {
  const { nodes, links } = useMemo(() => layout(systems, arch), [systems, arch]);
  const reduced = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [list, setList] = useState(false);

  return (
    <div>
      <div className="relative h-[380px] overflow-hidden rounded-lg border border-line bg-panel">
        {nodes.length === 0 ? (
          <p className="grid h-full place-items-center text-ink-soft">The graph fills in as agents discover systems.</p>
        ) : list || reduced ? (
          reduced && !list ? <Flat nodes={nodes} links={links} /> : <ul className="p-4">{nodes.map((n) => <li key={n.id}>{n.label} {n.solid ? "(confirmed)" : "(unconfirmed)"}</li>)}</ul>
        ) : (
          <div role="img" aria-label="3D system graph; the same systems are listed for screen readers below" className="h-full">
            <Canvas dpr={[1, 1.5]} camera={{ position: [0, 1, 11], fov: 45 }}>
              <Scene nodes={nodes} links={links} />
            </Canvas>
          </div>
        )}
        <button
          onClick={() => setList((v) => !v)}
          className="absolute right-3 top-3 rounded border border-line bg-panel px-2 py-1 text-xs font-medium hover:bg-paper"
        >
          {list ? "Show graph" : "Show list view"}
        </button>
      </div>
      <ul className="sr-only" aria-label="Systems in graph">
        {nodes.map((n) => <li key={n.id}>{n.label}: {n.solid ? "confirmed" : "unconfirmed"}</li>)}
      </ul>
      <p className="mt-2 text-xs text-ink-soft">
        Solid = confirmed. Hollow wireframe = unknown.{reduced ? "" : " Drag to orbit."}
      </p>
    </div>
  );
}
