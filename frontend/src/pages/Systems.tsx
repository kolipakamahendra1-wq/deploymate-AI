import { lazy, Suspense } from "react";
import { useApp } from "../store";
import { Empty, Mono, PageTitle, Panel, provBorder, ProvBadge } from "../components/ui/primitives";

const SystemGraph = lazy(() => import("../scenes/SystemGraph"));

export default function Systems() {
  const { data } = useApp();
  if (!data.systems.length) return <><PageTitle title="Systems" /><Empty what="systems" /></>;
  return (
    <>
      <PageTitle title="Systems" hint="Every system and API the agents found. Only endpoints from the supplied spec are marked as facts." />
      <div className="mb-6">
        <Suspense fallback={<p className="p-6 text-ink-soft">Loading 3D scene…</p>}>
          <SystemGraph systems={data.systems} arch={data.architecture} />
        </Suspense>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {data.systems.map((s) => (
          <Panel key={s.id} className={`border-l-4 ${provBorder(s.provenance)} ${s.confirmed ? "" : "hatched"}`}>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-xl font-semibold">{s.name}</h2>
              <ProvBadge p={s.provenance} source={s.source} />
            </div>
            <p className="mb-3 text-sm text-ink-soft">
              Role: {s.role} · {s.confirmed ? "confirmed from supplied material" : "not confirmed: API contract unknown"}
            </p>
            <ul className="space-y-1">
              {data.endpoints.filter((e) => e.system_id === s.id).map((e) => (
                <li key={e.method + e.path} className="flex items-center gap-2 text-sm">
                  <span className="w-14 rounded bg-ink px-1.5 py-0.5 text-center font-mono text-[11px] text-white">{e.method}</span>
                  <Mono>{e.path}</Mono>
                </li>
              ))}
            </ul>
          </Panel>
        ))}
      </div>
    </>
  );
}
