import { lazy, Suspense } from "react";
import { useApp } from "../store";
import { Empty, Mono, PageTitle, Panel, ProvBadge } from "../components/ui/primitives";

const MappingScene = lazy(() => import("../scenes/MappingScene"));

export default function DataMapping() {
  const { data } = useApp();
  if (!data.mapping.length) return <><PageTitle title="Data mapping" /><Empty what="mappings" /></>;
  const [src, tgt] = [data.systems[0]?.name ?? "Source", data.systems[1]?.name ?? "Target"];
  return (
    <>
      <PageTitle title="Data mapping" hint={`${src} field to ${tgt} field. Only identical field names are facts; everything else needs customer sign-off.`} />
      <div className="mb-6">
        <Suspense fallback={<p className="p-6 text-ink-soft">Loading 3D scene…</p>}><MappingScene mapping={data.mapping} /></Suspense>
      </div>
      <Panel className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Field mappings with confidence</caption>
          <thead className="border-b border-line bg-paper text-xs uppercase text-ink-soft">
            <tr>
              <th scope="col" className="p-3">Source field</th>
              <th scope="col" className="p-3">Target field</th>
              <th scope="col" className="p-3">Transform</th>
              <th scope="col" className="p-3">Confidence</th>
              <th scope="col" className="p-3">Provenance</th>
            </tr>
          </thead>
          <tbody>
            {data.mapping.map((m) => {
              const pct = Math.round(m.confidence * 100);
              // Colour carries provenance everywhere: a confident inference is still amber, not teal.
              const color = m.provenance === "fact" ? "bg-fact" : m.provenance === "assumption" ? "bg-assume" : "bg-unknown";
              return (
                <tr key={m.source_field} className={`border-b border-line last:border-0 ${m.provenance === "unknown" ? "hatched" : ""}`}>
                  <td className="p-3"><Mono>{m.source_field}</Mono></td>
                  <td className="p-3"><Mono>{m.target_field}</Mono></td>
                  <td className="p-3 text-ink-soft">{m.transform || "-"}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-24 rounded bg-line" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`Confidence ${pct}%`}>
                        <div className={`h-2 rounded ${color}`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="tabular-nums">{pct}%</span>
                    </div>
                  </td>
                  <td className="p-3"><ProvBadge p={m.provenance} source={m.source} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>
    </>
  );
}
