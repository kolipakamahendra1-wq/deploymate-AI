import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line, OrbitControls, Text } from "@react-three/drei";
import type { Group } from "three";
import type { Architecture, SystemNode } from "../api";
import { COBALT, INK, PROV_COLOR, SceneFrame } from "./common";

interface N { id: string; label: string; pos: [number, number, number]; solid: boolean; color: string; big: boolean }

/** Customer systems on the outside, discovered integration components between them. */
function layout(systems: SystemNode[], arch: Architecture): { nodes: N[]; links: [string, string][] } {
  const step = systems.length > 1 ? 8.8 / (systems.length - 1) : 0;
  // System ids and component ids come from different namespaces and may collide.
  const sid = (id: string) => `sys:${id}`;
  const cid = (id: string) => `comp:${id}`;
  const nodes: N[] = systems.map((s, i) => ({
    id: sid(s.id), label: s.name, pos: [systems.length > 1 ? -4.4 + i * step : 0, i > 1 ? -2.2 : 0, 0],
    solid: s.confirmed, color: PROV_COLOR[s.provenance], big: true,
  }));
  // Architecture components that are the customer systems themselves reuse the system node.
  const alias: Record<string, string> = {};
  const inner = arch.components.filter((c) => {
    const sys = systems.find((s) => s.name.toLowerCase() === c.name.toLowerCase());
    if (sys) alias[c.id] = sid(sys.id);
    return !sys;
  });
  const layers = [...new Set(inner.map((c) => c.layer))];
  layers.forEach((layer, row) => {
    const inLayer = inner.filter((c) => c.layer === layer);
    inLayer.forEach((c, i) => {
      const x = (i - (inLayer.length - 1) / 2) * 3.2;
      const y = ((layers.length - 1) / 2) * 1.3 - row * 1.3;
      nodes.push({ id: cid(c.id), label: c.name, pos: [x, y, -0.8], solid: true, color: COBALT, big: false });
    });
  });
  const ref = (id: string) => alias[id] ?? cid(id);
  const links = arch.flows.map((f) => [ref(f.source), ref(f.target)] as [string, string]);
  if (systems.length >= 2 && links.length === 0) links.push([sid(systems[0].id), sid(systems[1].id)]);
  return { nodes: nodes.slice(0, 40), links };
}

function Node({ n, delay }: { n: N; delay: number }) {
  const ref = useRef<Group>(null);
  const t = useRef(0);
  useFrame((_, dt) => {
    if (!ref.current) return;
    t.current += dt;
    ref.current.scale.setScalar(Math.min(1, Math.max(0, (t.current - delay) * 2.5))); // appear as discovered
  });
  const r = n.big ? 0.55 : 0.28;
  return (
    <group ref={ref} position={n.pos} scale={0}>
      <mesh>
        <sphereGeometry args={[r, 24, 24]} />
        {n.solid ? <meshStandardMaterial color={n.color} roughness={0.5} /> : <meshBasicMaterial color={n.color} wireframe />}
      </mesh>
      <Text position={[0, r + 0.28, 0]} fontSize={0.22} color={INK} anchorX="center">{n.label}</Text>
    </group>
  );
}

function Flat({ nodes, links }: { nodes: N[]; links: [string, string][] }) {
  const at = (id: string) => nodes.find((n) => n.id === id)?.pos;
  return (
    <svg viewBox="-6 -3 12 6" role="img" aria-label="System diagram" className="h-full w-full">
      {links.map(([a, b], i) => {
        const p = at(a), q = at(b);
        return p && q ? <line key={i} x1={p[0]} y1={-p[1]} x2={q[0]} y2={-q[1]} stroke="#46555F" strokeOpacity={0.5} strokeWidth={0.03} /> : null;
      })}
      {nodes.map((n) => (
        <g key={n.id} transform={`translate(${n.pos[0]},${-n.pos[1]})`}>
          <circle r={n.big ? 0.5 : 0.25} fill={n.solid ? n.color : "none"} stroke={n.color} strokeWidth={0.06} strokeDasharray={n.solid ? "" : "0.15"} />
          <text y={n.big ? -0.7 : -0.4} textAnchor="middle" fontSize={0.26} fill={INK}>{n.label}</text>
        </g>
      ))}
    </svg>
  );
}

export default function SystemGraph({ systems, arch }: { systems: SystemNode[]; arch: Architecture }) {
  const { nodes, links } = useMemo(() => layout(systems, arch), [systems, arch]);
  const pos = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n.pos])), [nodes]);
  return (
    <SceneFrame
      label="3D system graph"
      isEmpty={nodes.length === 0}
      empty="The graph fills in as agents discover systems."
      caption="Solid = confirmed. Hollow wireframe = API contract unknown."
      flat={<Flat nodes={nodes} links={links} />}
      list={<ul className="space-y-1">{nodes.map((n) => <li key={n.id}>{n.label}: {n.big ? (n.solid ? "customer system, confirmed" : "customer system, unconfirmed") : "integration component"}</li>)}</ul>}
    >
      <ambientLight intensity={0.9} />
      <directionalLight position={[4, 6, 5]} intensity={1.2} />
      {nodes.map((n, i) => <Node key={n.id} n={n} delay={i * 0.2} />)}
      {links.filter(([a, b]) => pos[a] && pos[b]).map(([a, b], i) => (
        <Line key={i} points={[pos[a], pos[b]]} color="#46555F" lineWidth={1} transparent opacity={0.55} />
      ))}
      <OrbitControls enablePan={false} minDistance={5} maxDistance={16} />
    </SceneFrame>
  );
}
