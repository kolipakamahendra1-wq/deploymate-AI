import { lazy, Suspense, useState } from "react";
import { Download, X } from "lucide-react";
import { useApp } from "../store";
import { Button, Empty, PageTitle, Panel } from "../components/ui/primitives";

const ArchitectureScene = lazy(() => import("../scenes/ArchitectureScene"));
const MermaidDiagram = lazy(() => import("../components/MermaidDiagram"));

const LAYERS = ["client", "api", "integration", "data"] as const;
const TABS = [["3d", "3D view"], ["layers", "Layers"], ["diagram", "Diagram"], ["source", "Mermaid source"]] as const;
type Tab = (typeof TABS)[number][0];

export default function Architecture() {
  const { data } = useApp();
  const a = data.architecture;
  const [tab, setTab] = useState<Tab>("3d");
  const [selId, setSel] = useState<string | null>(null);
  if (!a.components.length) return <><PageTitle title="Architecture" /><Empty what="architecture" /></>;
  const sel = a.components.find((c) => c.id === selId) ?? null;
  const name = (id: string) => a.components.find((c) => c.id === id)?.name ?? id;
  const boundaryOf = (id: string) => a.security_boundaries.filter((b) => b.components.includes(id)).map((b) => b.name);

  const download = () => {
    const url = URL.createObjectURL(new Blob([a.mermaid], { type: "text/plain" }));
    const el = document.createElement("a");
    el.href = url; el.download = "architecture.mmd"; el.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <PageTitle title="Architecture" hint="Proposed integration, layer by layer, with security boundaries. Select a component for details." />
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div role="tablist" aria-label="Architecture views" className="flex flex-wrap gap-2">
          {TABS.map(([t, label]) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
                    className={`rounded-md px-4 py-2 text-sm font-semibold ${tab === t ? "bg-cobalt text-white" : "border border-line bg-panel"}`}>
              {label}
            </button>
          ))}
        </div>
        <Button variant="ghost" onClick={download}><Download size={16} aria-hidden /> Export Mermaid</Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <div role="tabpanel" className="min-w-0">
          {tab === "3d" && (
            <Suspense fallback={<p className="p-6 text-ink-soft">Loading 3D scene…</p>}>
              <ArchitectureScene arch={a} selected={selId} onSelect={setSel} />
            </Suspense>
          )}
          {tab === "layers" && (
            <div className="space-y-3">
              {LAYERS.map((l) => (
                <Panel key={l} className="!p-4">
                  <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-soft">{l}</h2>
                  <div className="flex flex-wrap gap-2">
                    {a.components.filter((c) => c.layer === l).map((c) => (
                      <button key={c.id} onClick={() => setSel(c.id)} aria-pressed={selId === c.id}
                              className={`rounded-md border px-3 py-2 text-sm font-medium ${selId === c.id ? "border-cobalt bg-cobalt text-white" : "border-cobalt/40 bg-white hover:border-cobalt"}`}>
                        {c.name}
                      </button>
                    ))}
                  </div>
                </Panel>
              ))}
            </div>
          )}
          {tab === "diagram" && (
            <Panel><Suspense fallback={<p className="text-sm text-ink-soft">Loading diagram…</p>}><MermaidDiagram source={a.mermaid} /></Suspense></Panel>
          )}
          {tab === "source" && <Panel><pre className="overflow-x-auto font-mono text-[13px]">{a.mermaid}</pre></Panel>}
        </div>

        <aside aria-live="polite" className="h-fit rounded-lg border border-line bg-panel p-4">
          {sel ? (
            <>
              <div className="flex items-start justify-between gap-2">
                <h2 className="text-lg font-semibold">{sel.name}</h2>
                <button aria-label="Close details" onClick={() => setSel(null)}><X size={16} /></button>
              </div>
              <p className="text-xs uppercase tracking-wide text-ink-soft">{sel.layer} layer</p>
              <p className="mt-2 text-sm">{sel.description}</p>
              {boundaryOf(sel.id).length > 0 && <p className="mt-2 text-sm">Inside: {boundaryOf(sel.id).join(", ")}</p>}
              <h3 className="mt-4 text-sm font-semibold">Data flows</h3>
              <ul className="text-sm">
                {a.flows.filter((f) => f.source === sel.id || f.target === sel.id).map((f, i) => (
                  <li key={i}>{name(f.source)} → {name(f.target)} <span className="text-ink-soft">({f.label})</span></li>
                ))}
              </ul>
            </>
          ) : (
            <>
              <h2 className="text-sm font-semibold">Security boundaries</h2>
              <ul className="mt-1 space-y-1 text-sm">
                {a.security_boundaries.map((b) => <li key={b.name}><strong>{b.name}</strong>: {b.components.map(name).join(", ")}</li>)}
              </ul>
              <p className="mt-3 text-sm text-ink-soft">Select a component to see its details.</p>
            </>
          )}
        </aside>
      </div>
    </>
  );
}
