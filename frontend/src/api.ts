export type Prov = "fact" | "assumption" | "unknown";

export interface Claim { provenance: Prov; source?: string | null }
export interface Requirement extends Claim { id: string; text: string; kind: string }
export interface Question { id: string; text: string; category: string; priority: string }
export interface SystemNode extends Claim { id: string; name: string; role: string; confirmed: boolean }
export interface Endpoint extends Claim { system_id: string; method: string; path: string }
export interface Mapping extends Claim { source_field: string; target_field: string; confidence: number; transform: string }
export interface ArchComponent { id: string; name: string; layer: "client" | "api" | "integration" | "data"; description: string }
export interface Architecture {
  components: ArchComponent[];
  flows: { source: string; target: string; label: string }[];
  security_boundaries: string[];
  mermaid: string;
}
export interface Task { id: string; title: string; depends_on: string[]; estimate_days: number }
export interface TestCase { id: string; title: string; covers: string[]; expected: string }
export interface Risk { id: string; title: string; severity: "high" | "medium" | "low"; mitigation: string }
export interface CriticNote { severity: "error" | "warning"; message: string }
export interface Handoff { markdown: string; requires_human_review: boolean; approved: boolean }
export interface Decision { agent: string; decision: string; rationale: string; at: string }

export interface Data {
  requirements: Requirement[];
  questions: Question[];
  systems: SystemNode[];
  endpoints: Endpoint[];
  mapping: Mapping[];
  architecture: Architecture;
  plan: Task[];
  risks: Risk[];
  tests: TestCase[];
  critic: CriticNote[];
  handoff: Handoff;
  decisions: Decision[];
}

export const STAGES = ["requirements", "clarification", "integration", "architecture", "validation", "critic", "handoff"];

export const emptyData = (): Data => ({
  requirements: [], questions: [], systems: [], endpoints: [], mapping: [],
  architecture: { components: [], flows: [], security_boundaries: [], mermaid: "" },
  plan: [], risks: [], tests: [], critic: [],
  handoff: { markdown: "", requires_human_review: true, approved: false }, decisions: [],
});

const j = async <T,>(r: Response): Promise<T> => {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
};

export const api = {
  health: () => fetch("/api/health").then((r) => j<{ llm: string }>(r)),
  demo: () => fetch("/api/demo").then((r) => j<Record<string, unknown>>(r)),
  create: (body: unknown) =>
    fetch("/api/customers", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then((r) => j<{ id: string }>(r)),
  section: <T,>(id: string, s: string) => fetch(`/api/customers/${id}/${s}`).then((r) => j<T>(r)),
  approve: (id: string) => fetch(`/api/customers/${id}/handoff/approve`, { method: "POST" }).then((r) => j<Handoff>(r)),
  async run(id: string, onStage: (stage: string) => void) {
    const res = await fetch(`/api/customers/${id}/run`, { method: "POST" });
    if (!res.body) throw new Error("no stream");
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() ?? "";
      for (const p of parts) {
        const msg = JSON.parse(p.replace(/^data: /, ""));
        if (msg.error) throw new Error(msg.error);
        if (msg.stage) onStage(msg.stage);
      }
    }
  },
};
