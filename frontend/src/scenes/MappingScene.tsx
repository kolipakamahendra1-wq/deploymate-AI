import { useMemo } from "react";
import { Line, OrbitControls, Text } from "@react-three/drei";
import type { Mapping } from "../api";
import { INK, PROV_COLOR, SceneFrame } from "./common";

const ROW = 0.62;

/** Source fields on the left column, target fields on the right, lines coloured by provenance. */
export default function MappingScene({ mapping }: { mapping: Mapping[] }) {
  const { left, right } = useMemo(() => {
    const src = mapping.map((m) => m.source_field);
    const tgt = [...new Set(mapping.map((m) => m.target_field).filter((t) => t !== "?"))];
    const y = (i: number, n: number) => ((n - 1) / 2 - i) * ROW;
    return {
      left: Object.fromEntries(src.map((f, i) => [f, [-3, y(i, src.length), 0] as [number, number, number]])),
      right: Object.fromEntries(tgt.map((f, i) => [f, [3, y(i, tgt.length), -1] as [number, number, number]])),
    };
  }, [mapping]);
  const height = Math.max(300, mapping.length * 42 + 80);

  return (
    <SceneFrame
      label="3D field mapping between source and target columns"
      height={Math.min(height, 520)}
      isEmpty={!mapping.length}
      empty="Mappings appear after the integration agent runs."
      caption="Line colour: teal = identical field, amber = inferred, no line = no target field. Thicker lines = higher confidence."
      camera={{ position: [0, 0, Math.max(8, mapping.length * 0.75)], fov: 45 }}
      list={<p>The table below lists every mapping with its confidence.</p>}
    >
      <ambientLight intensity={1} />
      <Text position={[-3, (mapping.length / 2) * ROW + 0.5, 0]} fontSize={0.24} color="#46555F" anchorX="center">SOURCE</Text>
      <Text position={[3, (mapping.length / 2) * ROW + 0.5, -1]} fontSize={0.24} color="#46555F" anchorX="center">TARGET</Text>
      {Object.entries(left).map(([f, p]) => (
        <Text key={`l-${f}`} position={[p[0] - 0.15, p[1], p[2]]} fontSize={0.2} color={INK} anchorX="right">{f}</Text>
      ))}
      {Object.entries(right).map(([f, p]) => (
        <Text key={`r-${f}`} position={[p[0] + 0.15, p[1], p[2]]} fontSize={0.2} color={INK} anchorX="left">{f}</Text>
      ))}
      {mapping.filter((m) => m.target_field !== "?" && right[m.target_field]).map((m) => (
        <Line key={m.source_field + m.target_field} points={[left[m.source_field], right[m.target_field]]}
              color={PROV_COLOR[m.provenance]} lineWidth={1 + m.confidence * 3} />
      ))}
      {mapping.filter((m) => m.target_field === "?").map((m) => (
        <mesh key={`u-${m.source_field}`} position={[-2.85, left[m.source_field][1], 0]}>
          <ringGeometry args={[0.07, 0.1, 16]} />
          <meshBasicMaterial color={PROV_COLOR.unknown} />
        </mesh>
      ))}
      <OrbitControls enablePan={false} minDistance={4} maxDistance={20} />
    </SceneFrame>
  );
}
