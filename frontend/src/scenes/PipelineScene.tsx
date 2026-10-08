import { useEffect, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Billboard, RoundedBox, Text } from "@react-three/drei";
import gsap from "gsap";
import type { Mesh } from "three";
import { STAGES } from "../api";
import { COBALT, INK, PROV_COLOR, SceneFrame } from "./common";

const GAP = 3.2;
const LABELS: Record<string, string> = {
  requirements: "Requirements", clarification: "Clarification", integration: "Integration",
  architecture: "Architecture", validation: "Validation", critic: "Critic", handoff: "Handoff",
};

/** Follows the active stage during a run; pulls back to an overview of all stages when idle. */
function CameraRig({ index, overview }: { index: number; overview: boolean }) {
  const { camera } = useThree();
  useEffect(() => {
    const mid = -((STAGES.length - 1) * GAP) / 2;
    const pos = overview ? { x: 11, y: 7, z: mid + 6 } : { x: 4.5, y: 3, z: -index * GAP + 5.5 };
    const look: [number, number, number] = overview ? [0, -0.5, mid] : [0, 0, -index * GAP];
    const tween = gsap.to(camera.position, { ...pos, duration: 0.9, ease: "power2.inOut",
      onUpdate: () => camera.lookAt(look[0], look[1], look[2]) });
    return () => { tween.kill(); };
  }, [index, overview, camera]);
  return null;
}

function Plate({ i, stage, state }: { i: number; stage: string; state: "done" | "active" | "pending" }) {
  const ref = useRef<Mesh>(null);
  useFrame(({ clock }) => {
    if (ref.current && state === "active") ref.current.position.y = Math.sin(clock.elapsedTime * 3) * 0.08;
  });
  const color = state === "done" ? PROV_COLOR.fact : state === "active" ? COBALT : "#CFD8DE";
  return (
    <group position={[0, 0, -i * GAP]}>
      <RoundedBox ref={ref} args={[3.2, 0.25, 2]} radius={0.08}>
        <meshStandardMaterial color={color} transparent opacity={state === "pending" ? 0.55 : 0.95} />
      </RoundedBox>
      <Billboard position={[0, 0.7, 0]}>
        <Text fontSize={0.42} color={INK} anchorX="center" outlineWidth={0.02} outlineColor="#F7F9FA">
          {`${i + 1}. ${LABELS[stage]}`}
        </Text>
      </Billboard>
    </group>
  );
}

export default function PipelineScene({ done, running }: { done: string[]; running: boolean }) {
  const active = running ? Math.min(done.length, STAGES.length - 1) : Math.max(0, done.length - 1);
  return (
    <SceneFrame
      label="Agent pipeline in depth"
      height={260}
      caption="The seven agents sit along a depth axis; the camera follows the active stage."
      camera={{ position: [11, 7, -3.6], fov: 50 }}
      list={
        <ol className="space-y-1">
          {STAGES.map((s, i) => (
            <li key={s}>{i + 1}. {LABELS[s]}: {done.includes(s) ? "done" : running && i === done.length ? "running" : "pending"}</li>
          ))}
        </ol>
      }
    >
      <ambientLight intensity={0.9} />
      <directionalLight position={[3, 6, 4]} intensity={1.1} />
      <CameraRig index={active} overview={!running} />
      {STAGES.map((s, i) => (
        <Plate key={s} i={i} stage={s}
               state={done.includes(s) ? "done" : running && i === done.length ? "active" : "pending"} />
      ))}
    </SceneFrame>
  );
}
