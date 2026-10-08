import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { useApp } from "../store";
import { Empty, PageTitle, Panel } from "../components/ui/primitives";

export default function Validation() {
  const { data } = useApp();
  const [open, setOpen] = useState<string | null>(null);
  if (!data.tests.length) return <><PageTitle title="Validation" /><Empty what="test cases" /></>;

  const known = data.requirements.filter((r) => r.provenance !== "unknown");
  const covered = known.filter((r) => data.tests.some((t) => t.covers.includes(r.id)));
  const pct = known.length ? Math.round((covered.length / known.length) * 100) : 0;

  return (
    <>
      <PageTitle title="Validation" hint="Test cases and the requirements they cover. Unknown requirements are excluded until clarified." />
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        {[["Test cases", data.tests.length], ["Requirements covered", `${covered.length}/${known.length}`], ["Coverage", `${pct}%`]].map(([k, v]) => (
          <Panel key={String(k)}>
            <div className="text-sm text-ink-soft">{k}</div>
            <div className="font-display text-3xl font-bold">{v}</div>
          </Panel>
        ))}
      </div>
      <ul className="space-y-2">
        {data.tests.map((t) => (
          <li key={t.id} className="rounded-lg border border-line bg-panel">
            <h2>
              <button aria-expanded={open === t.id} onClick={() => setOpen(open === t.id ? null : t.id)}
                      className="flex w-full items-center justify-between p-4 text-left font-medium">
                <span><span className="mr-2 font-mono text-xs text-ink-soft">{t.id}</span>{t.title}</span>
                <ChevronDown size={18} aria-hidden className={open === t.id ? "rotate-180" : ""} />
              </button>
            </h2>
            {open === t.id && (
              <div className="border-t border-line p-4 text-sm">
                <p><strong>Expected:</strong> {t.expected}</p>
                <p className="mt-1 text-ink-soft">Covers: {t.covers.join(", ") || "none"}</p>
              </div>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
