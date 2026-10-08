export type Prov = "fact" | "assumption" | "unknown";

export interface Claim { provenance: Prov; source?: string | null }
export interface Requirement extends Claim { id: string; text: string; kind: string }
export interface Question { id: string; text: string; category: string; priority: string }
export interface SystemNode extends Claim { id: string; name: string; role: string; confirmed: boolean }
export interface Endpoint extends Claim { system_id: string; method: string; path: string }
export interface Mapping extends Claim { source_field: string; target_field: string; confidence: number; transform: string }
export type Layer = "client" | "api" | "integration" | "data";
export interface ArchComponent { id: string; name: string; layer: Layer; description: string }
export interface Boundary { name: string; components: string[] }
export interface Architecture {
  components: ArchComponent[];
  flows: { source: string; target: string; label: string }[];
  security_boundaries: Boundary[];
  mermaid: string;
}
export interface Task { id: string; title: string; depends_on: string[]; estimate_days: number }
export interface TestCase { id: string; title: string; covers: string[]; expected: string }
export interface Risk { id: string; title: string; severity: "high" | "medium" | "low"; mitigation: string }
export interface CriticNote { severity: "error" | "warning"; message: string }
export interface Handoff { markdown: string; requires_human_review: boolean; approved: boolean }
export interface Decision { agent: string; decision: string; rationale: string; at: string; run?: number }
export interface PatternRef { id: string; name: string; summary: string; score: number }
export interface CustomerInfo {
  id: string; completed_stages: string[]; brief: string;
  has_spec: boolean; has_sample: boolean; recorded_demo: boolean;
}

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
  patterns: PatternRef[];
}

export interface EvalReport {
  mode: string;
  cases: number;
  summary: Record<string, number>;
  critic_accuracy: number;
  human_reviewer_score: number | null;
  notes: string;
  per_case: (Record<string, number | string | string[]> & { case: string; name: string })[];
  critic_cases: { case: string; expected_violation: boolean; flagged: boolean; correct: boolean }[];
}

export const STAGES = ["requirements", "clarification", "integration", "architecture", "validation", "critic", "handoff"];

export const emptyData = (): Data => ({
  requirements: [], questions: [], systems: [], endpoints: [], mapping: [],
  architecture: { components: [], flows: [], security_boundaries: [], mermaid: "" },
  plan: [], risks: [], tests: [], critic: [],
  handoff: { markdown: "", requires_human_review: true, approved: false }, decisions: [], patterns: [],
});

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`;
    try { detail = (await r.json()).detail ?? detail; } catch { /* not JSON */ }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

const post = (url: string, body?: unknown) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });

export const api = {
  health: () => fetch("/api/health").then((r) => j<{ llm: "live" | "offline" }>(r)),
  demo: () => fetch("/api/demo").then((r) => j<{ name: string; brief: string; openapi: unknown; sample: unknown }>(r)),
  customers: () => fetch("/api/customers").then((r) => j<{ id: string; name: string }[]>(r)),
  customer: (id: string) => fetch(`/api/customers/${id}`).then((r) => j<CustomerInfo>(r)),
  create: (body: unknown) => post("/api/customers", body).then((r) => j<{ id: string }>(r)),
  section: <T,>(id: string, s: string) => fetch(`/api/customers/${id}/${s}`).then((r) => j<T>(r)),
  decisionLog: (id: string) => fetch(`/api/customers/${id}/decision-log`).then((r) => j<Decision[]>(r)),
  approve: (id: string) => post(`/api/customers/${id}/handoff/approve`).then((r) => j<Handoff>(r)),
  evaluation: () => fetch("/api/evaluation").then((r) => j<EvalReport>(r)),
  runEvaluation: () => post("/api/evaluation/run").then((r) => j<EvalReport>(r)),
  async run(id: string, onStage: (stage: string) => void | Promise<void>) {
    const res = await post(`/api/customers/${id}/run`);
    if (!res.ok || !res.body) throw new Error(`Run failed: ${res.status}`);
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
        if (!p.startsWith("data: ")) continue;
        const msg = JSON.parse(p.slice(6));
        if (msg.error) throw new Error(msg.error);
        if (msg.stage) await onStage(msg.stage);
      }
    }
  },
};
