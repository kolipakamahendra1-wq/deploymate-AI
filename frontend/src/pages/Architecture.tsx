import { useState } from "react";
import { X } from "lucide-react";
import type { ArchComponent } from "../api";
import { useApp } from "../store";
import { Empty, PageTitle, Panel } from "../components/ui/primitives";

const LAYERS = ["client", "api", "integration", "data"] as const;

export default function Architecture() {
  const { data } = useApp();
  const a = data.architecture;
  const [tab, setTab] = useState<"layers" | "mermaid">("layers");
  const [sel, setSel] = useState<ArchComponent | null>(null);
  if (!a.components.length) return <><PageTitle title="Architecture" /><Empty what="architecture" /></>;
  const name = (id: string) => a.components.find((c) => c.id === id)?.name ?? id;

  return (
    <>
      <PageTitle title="Architecture" hint="Layered view of the proposed integration. Select a component for details." />
      <div role="tablist" aria-label="Architecture views" className="mb-4 flex gap-2">
        {(["layers", "mermaid"] as const).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
                  className={`rounded-md px-4 py-2 text-sm font-semibold ${tab === t ? "bg-cobalt text-white" : "border border-line bg-panel"}`}>
            {t === "layers" ? "Layers" : "Mermaid source"}
          </button>
        ))}
      </div>

      {tab === "layers" ? (
        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div className="space-y-3">
            {LAYERS.map((l) => (
              <Panel key={l} className="!p-4">
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-soft">{l}</h2>
                <div className="flex flex-wrap gap-2">
                  {a.components.filter((c) => c.layer === l).map((c) => (
                    <button key={c.id} onClick={() => setSel(c)}
                            className="rounded-md border border-cobalt/40 bg-white px-3 py-2 text-sm font-medium hover:border-cobalt">
                      {c.name}
                    </button>
                  ))}
                </div>
              </Panel>
            ))}
            <Panel className="!p-4">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-soft">Security boundaries</h2>
              <ul className="list-disc pl-5 text-sm">{a.security_boundaries.map((b) => <li key={b}>{b}</li>)}</ul>
            </Panel>
          </div>
          <aside aria-live="polite" className="rounded-lg border border-line bg-panel p-4">
            {sel ? (
              <>
                <div className="flex items-start justify-between">
                  <h2 className="text-lg font-semibold">{sel.name}</h2>
                  <button aria-label="Close details" onClick={() => setSel(null)}><X size={16} /></button>
                </div>
                <p className="mt-1 text-sm text-ink-soft">{sel.description}</p>
                <h3 className="mt-4 text-sm font-semibold">Data flows</h3>
                <ul className="text-sm">
                  {a.flows.filter((f) => f.source === sel.id || f.target === sel.id).map((f, i) => (
                    <li key={i}>{name(f.source)} → {name(f.target)} <span className="text-ink-soft">({f.label})</span></li>
                  ))}
                </ul>
              </>
            ) : <p className="text-sm text-ink-soft">Select a component to see its details.</p>}
          </aside>
        </div>
      ) : (
        <Panel><pre className="overflow-x-auto font-mono text-[13px]">{a.mermaid}</pre></Panel>
      )}
    </>
  );
}
