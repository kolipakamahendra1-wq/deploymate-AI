import type { Task } from "../api";
import { useApp } from "../store";
import { Empty, PageTitle, Panel } from "../components/ui/primitives";

/** Depth = longest dependency chain, which gives the timeline column. */
function depth(t: Task, all: Task[], seen = new Set<string>()): number {
  if (seen.has(t.id)) return 0;
  seen.add(t.id);
  return t.depends_on.length
    ? 1 + Math.max(...t.depends_on.map((d) => { const x = all.find((y) => y.id === d); return x ? depth(x, all, seen) : 0; }))
    : 0;
}

export default function Plan() {
  const { data } = useApp();
  if (!data.plan.length) return <><PageTitle title="Implementation plan" /><Empty what="plan" /></>;
  const cols = Math.max(...data.plan.map((t) => depth(t, data.plan))) + 1;
  const total = data.plan.reduce((n, t) => n + t.estimate_days, 0);
  return (
    <>
      <PageTitle title="Implementation plan" hint={`${data.plan.length} tasks, about ${total} engineer-days. Columns are dependency waves: a task starts after its dependencies finish.`} />
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, minmax(220px, 1fr))` }}>
        {Array.from({ length: cols }, (_, c) => (
          <Panel key={c} className="!p-3">
            <h2 className="mb-2 text-sm font-semibold uppercase text-ink-soft">Wave {c + 1}</h2>
            <ul className="space-y-2">
              {data.plan.filter((t) => depth(t, data.plan) === c).map((t) => (
                <li key={t.id} className="rounded border border-line bg-white p-3 text-sm">
                  <div className="font-mono text-xs text-ink-soft">{t.id} · {t.estimate_days}d</div>
                  <div className="font-medium">{t.title}</div>
                  {t.depends_on.length > 0 && <div className="mt-1 text-xs text-ink-soft">after {t.depends_on.join(", ")}</div>}
                </li>
              ))}
            </ul>
          </Panel>
        ))}
      </div>
    </>
  );
}
