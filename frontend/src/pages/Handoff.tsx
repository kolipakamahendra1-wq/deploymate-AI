import { Download, ShieldCheck } from "lucide-react";
import { useApp } from "../store";
import { Button, Empty, PageTitle, Panel } from "../components/ui/primitives";

export default function Handoff() {
  const { data, approve } = useApp();
  const h = data.handoff;
  if (!h.markdown) return <><PageTitle title="Handoff" /><Empty what="handoff package" /></>;

  const download = () => {
    const url = URL.createObjectURL(new Blob([h.markdown], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = url; a.download = "deploymate-handoff.md"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <PageTitle title="Handoff" hint="Customer-ready package. Nothing here is a commitment until a person approves it." />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Button variant="ghost" onClick={download}><Download size={16} aria-hidden /> Export Markdown</Button>
        <Button onClick={approve} disabled={h.approved}><ShieldCheck size={16} aria-hidden /> {h.approved ? "Approved by human reviewer" : "Approve for sharing"}</Button>
        {!h.approved && <span className="text-sm text-[#8a5f00]">Human review required before sharing externally.</span>}
      </div>
      <Panel>
        <pre className="whitespace-pre-wrap font-body text-sm leading-relaxed" tabIndex={0} aria-label="Handoff document preview">{h.markdown}</pre>
      </Panel>
      <Panel className="mt-6">
        <h2 className="mb-2 text-xl font-semibold">Decision log</h2>
        <ul className="space-y-1 text-sm">
          {data.decisions.map((d, i) => (
            <li key={i}><span className="font-mono text-xs text-ink-soft">{d.agent}</span> {d.decision}{d.rationale && <span className="text-ink-soft"> — {d.rationale}</span>}</li>
          ))}
        </ul>
      </Panel>
    </>
  );
}
