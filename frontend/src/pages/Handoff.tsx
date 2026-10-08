import { useEffect, useState } from "react";
import { ChevronDown, Download, Printer, ShieldCheck } from "lucide-react";
import { api, type Decision } from "../api";
import { useApp } from "../store";
import { Button, Empty, PageTitle, Panel } from "../components/ui/primitives";

export default function Handoff() {
  const { data, approve, customerId, running } = useApp();
  const h = data.handoff;
  const [log, setLog] = useState<Decision[]>([]);
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    if (customerId && !running) api.decisionLog(customerId).then(setLog).catch(() => setLog([]));
  }, [customerId, running, h.markdown]);

  if (!h.markdown) return <><PageTitle title="Handoff" /><Empty what="handoff package" /></>;

  const download = () => {
    const url = URL.createObjectURL(new Blob([h.markdown], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = url; a.download = "deploymate-handoff.md"; a.click();
    URL.revokeObjectURL(url);
    setMenu(false);
  };
  const runs = [...new Set(log.map((d) => d.run))].sort((a, b) => (b ?? 0) - (a ?? 0));

  return (
    <>
      <PageTitle title="Handoff" hint="Customer-ready package. Nothing here is a commitment until a person approves it." />
      <div className="mb-4 flex flex-wrap items-center gap-3 print:hidden">
        <div className="relative">
          <Button variant="ghost" aria-haspopup="menu" aria-expanded={menu} onClick={() => setMenu(!menu)}>
            <Download size={16} aria-hidden /> Export <ChevronDown size={14} aria-hidden />
          </Button>
          {menu && (
            <ul role="menu" className="absolute z-10 mt-1 w-48 rounded-md border border-line bg-panel py-1 shadow-lg">
              <li role="none"><button role="menuitem" className="w-full px-3 py-2 text-left text-sm hover:bg-paper" onClick={download}>Markdown (.md)</button></li>
              <li role="none"><button role="menuitem" className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-paper"
                                      onClick={() => { setMenu(false); window.print(); }}><Printer size={14} aria-hidden /> Print or save as PDF</button></li>
            </ul>
          )}
        </div>
        <Button onClick={approve} disabled={h.approved}>
          <ShieldCheck size={16} aria-hidden /> {h.approved ? "Approved by human reviewer" : "Approve for sharing"}
        </Button>
        {!h.approved && <span className="text-sm text-[#7a5300]">Human review required before sharing externally.</span>}
      </div>
      <Panel className="print:border-0 print:p-0">
        <pre className="whitespace-pre-wrap font-body text-sm leading-relaxed" tabIndex={0} aria-label="Handoff document preview">{h.markdown}</pre>
      </Panel>
      <Panel className="mt-6 print:hidden">
        <h2 className="mb-1 text-xl font-semibold">Decision log</h2>
        <p className="mb-3 text-xs text-ink-soft">Append-only audit trail of every generated decision, kept across runs.</p>
        {runs.map((r) => (
          <details key={r} open={r === runs[0]} className="mb-2">
            <summary className="cursor-pointer text-sm font-semibold">Run {r}</summary>
            <ul className="mt-1 space-y-1 text-sm">
              {log.filter((d) => d.run === r).map((d, i) => (
                <li key={i}>
                  <span className="font-mono text-xs text-ink-soft">{d.agent}</span> {d.decision}
                  {d.rationale && <span className="text-ink-soft"> ({d.rationale})</span>}
                </li>
              ))}
            </ul>
          </details>
        ))}
      </Panel>
    </>
  );
}
