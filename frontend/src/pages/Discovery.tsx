import { lazy, Suspense } from "react";
import { Play } from "lucide-react";
import { STAGES } from "../api";
import { useApp } from "../store";
import { Button, Empty, PageTitle, Panel, provBorder, ProvBadge } from "../components/ui/primitives";

const SystemGraph = lazy(() => import("../scenes/SystemGraph"));

export default function Discovery() {
  const { customerId, data, done, running, run } = useApp();
  if (!customerId) return <><PageTitle title="Discovery" /><Empty what="customer" /></>;

  return (
    <>
      <PageTitle title="Discovery" hint="Seven agents work through the brief. The graph fills in as each stage completes." />
      <Panel className="mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={run} disabled={running}><Play size={16} aria-hidden /> {running ? "Running…" : "Run pipeline"}</Button>
          <ol className="flex flex-wrap gap-1.5" aria-label="Pipeline stages">
            {STAGES.map((s) => {
              const isDone = done.includes(s);
              const active = running && !isDone && done.length === STAGES.indexOf(s);
              return (
                <li key={s} aria-current={active ? "step" : undefined}
                    className={`rounded-full border px-3 py-1 text-xs font-semibold capitalize ${isDone ? "border-fact bg-fact/10 text-fact" : active ? "border-cobalt bg-cobalt text-white" : "border-line text-ink-soft"}`}>
                  {isDone ? "✓ " : ""}{s}
                </li>
              );
            })}
          </ol>
        </div>
      </Panel>

      <div className="mb-6">
        <Suspense fallback={<p className="p-6 text-ink-soft">Loading 3D scene…</p>}>
          <SystemGraph systems={data.systems} arch={data.architecture} />
        </Suspense>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <h2 className="mb-3 text-xl font-semibold">Requirements</h2>
          {data.requirements.length === 0 ? <p className="text-ink-soft">Nothing extracted yet.</p> : (
            <ul className="space-y-2">
              {data.requirements.map((r) => (
                <li key={r.id} className={`rounded border border-line border-l-4 bg-white p-3 ${provBorder(r.provenance)} ${r.provenance === "unknown" ? "hatched" : ""}`}>
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-ink-soft">{r.id} · {r.kind}</span>
                    <ProvBadge p={r.provenance} source={r.source} />
                  </div>
                  <p className="text-sm">{r.text}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel>
          <h2 className="mb-3 text-xl font-semibold">Questions to ask the customer</h2>
          {data.questions.length === 0 ? <p className="text-ink-soft">No open questions yet.</p> : (
            <ul className="space-y-2">
              {data.questions.map((q) => (
                <li key={q.id} className="rounded border border-line bg-white p-3">
                  <label className="flex items-start gap-2 text-sm">
                    <input type="checkbox" className="mt-1" />
                    <span>{q.text} <span className="ml-1 rounded bg-paper px-1.5 py-0.5 text-xs text-ink-soft">{q.category} · {q.priority}</span></span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </>
  );
}
