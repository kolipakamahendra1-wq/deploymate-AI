import { useMemo, useState } from "react";
import { useApp } from "../store";
import { Empty, PageTitle, Panel, SeverityTag } from "../components/ui/primitives";

const RANK = { high: 0, medium: 1, low: 2 } as const;

export default function Risks() {
  const { data } = useApp();
  const [asc, setAsc] = useState(true);
  const rows = useMemo(
    () => [...data.risks].sort((a, b) => (RANK[a.severity] - RANK[b.severity]) * (asc ? 1 : -1)),
    [data.risks, asc],
  );
  if (!data.risks.length) return <><PageTitle title="Risks" /><Empty what="risks" /></>;
  return (
    <>
      <PageTitle title="Risk register" hint="Sorted by severity. Critic findings are listed below the register." />
      <Panel className="mb-6 overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Risk register</caption>
          <thead className="border-b border-line bg-paper text-xs uppercase text-ink-soft">
            <tr>
              <th scope="col" className="p-3">ID</th>
              <th scope="col" className="p-3">Risk</th>
              <th scope="col" className="p-3" aria-sort={asc ? "ascending" : "descending"}>
                <button onClick={() => setAsc(!asc)} className="font-semibold uppercase">Severity {asc ? "▲" : "▼"}</button>
              </th>
              <th scope="col" className="p-3">Mitigation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-line last:border-0">
                <td className="p-3 font-mono text-xs">{r.id}</td>
                <td className="p-3 font-medium">{r.title}</td>
                <td className="p-3"><SeverityTag s={r.severity} /></td>
                <td className="p-3 text-ink-soft">{r.mitigation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
      <Panel>
        <h2 className="mb-2 text-xl font-semibold">Critic findings</h2>
        {data.critic.length === 0 ? <p className="text-[#08665c]">The critic found no guardrail violations.</p> : (
          <ul className="space-y-2">{data.critic.map((n, i) => <li key={i} className="flex items-center gap-2 text-sm"><SeverityTag s={n.severity} />{n.message}</li>)}</ul>
        )}
      </Panel>
    </>
  );
}
