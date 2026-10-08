import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, type EvalReport } from "../api";
import { Button, PageTitle, Panel } from "../components/ui/primitives";

const LABELS: Record<string, string> = {
  requirement_precision: "Requirement extraction precision",
  requirement_recall: "Requirement extraction recall",
  missing_question_recall: "Missing-question recall",
  mapping_accuracy: "Mapping accuracy",
  architecture_valid: "Architecture validity",
  test_coverage: "Test-case coverage",
  pattern_top1: "Pattern retrieval (top-1)",
};
const pct = (v: number) => `${Math.round(v * 100)}%`;

/** Horizontal bars, one series: single hue, value labels at the bar end, hover tooltip per bar. */
function MetricBars({ summary }: { summary: Record<string, number> }) {
  const [hover, setHover] = useState<string | null>(null);
  const rows = Object.keys(LABELS).filter((k) => k in summary);
  const W = 640, LABEL = 230, BAR_H = 22, GAP = 14, VALUE = 48;
  const plotW = W - LABEL - VALUE;
  const H = rows.length * (BAR_H + GAP) + 24;
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Evaluation metrics, percent of cases">
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <line x1={LABEL + t * plotW} x2={LABEL + t * plotW} y1={0} y2={H - 20} stroke="#CFD8DE" strokeWidth={1} />
            <text x={LABEL + t * plotW} y={H - 6} fontSize={11} textAnchor="middle" fill="#46555F">{pct(t)}</text>
          </g>
        ))}
        {rows.map((k, i) => {
          const v = summary[k];
          const y = i * (BAR_H + GAP) + 4;
          const w = Math.max(v * plotW, 2);
          return (
            <g key={k} onMouseEnter={() => setHover(k)} onMouseLeave={() => setHover(null)}>
              <rect x={0} y={y - GAP / 2} width={W} height={BAR_H + GAP} fill="transparent" />
              <text x={LABEL - 10} y={y + BAR_H / 2 + 4} fontSize={13} textAnchor="end" fill="#16222C">{LABELS[k]}</text>
              {/* square at the baseline, 4px rounded at the data end */}
              <path d={`M${LABEL},${y} h${w - 4} q4,0 4,4 v${BAR_H - 8} q0,4 -4,4 h${-(w - 4)} z`}
                    fill="#2B4EFF" opacity={hover && hover !== k ? 0.45 : 1} />
              <text x={LABEL + w + 8} y={y + BAR_H / 2 + 4} fontSize={13} fill="#16222C" fontWeight={600}>{pct(v)}</text>
            </g>
          );
        })}
      </svg>
      {hover && (
        <div role="status" className="pointer-events-none absolute right-0 top-0 rounded-md border border-line bg-white px-3 py-2 text-xs shadow">
          <strong>{LABELS[hover]}</strong>: {pct(summary[hover])} averaged over all cases
        </div>
      )}
    </div>
  );
}

export default function Evaluation() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [table, setTable] = useState(false);

  useEffect(() => { api.evaluation().then(setReport).catch(() => setReport(null)); }, []);

  const rerun = async () => {
    setBusy(true); setErr("");
    try { setReport(await api.runEvaluation()); } catch (e) { setErr(e instanceof Error ? e.message : "Evaluation failed"); }
    finally { setBusy(false); }
  };

  return (
    <>
      <PageTitle title="Evaluation" hint="Synthetic implementation cases scored on the PRD metrics. Runs the offline agents so results are reproducible." />
      <div className="mb-6 flex items-center gap-3">
        <Button onClick={rerun} disabled={busy}><RefreshCw size={16} aria-hidden className={busy ? "animate-spin" : ""} /> {busy ? "Running…" : report ? "Run again" : "Run evaluation"}</Button>
        {err && <span role="alert" className="text-sm text-[#9b1c1c]">{err}</span>}
      </div>
      {!report ? (
        <Panel><p className="text-ink-soft">No evaluation report yet. Run the evaluation to score all cases.</p></Panel>
      ) : (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-3">
            <Panel><div className="text-sm text-ink-soft">Synthetic cases</div><div className="font-display text-3xl font-bold">{report.cases}</div></Panel>
            <Panel><div className="text-sm text-ink-soft">Critic accuracy on planted violations</div><div className="font-display text-3xl font-bold">{pct(report.critic_accuracy)}</div></Panel>
            <Panel><div className="text-sm text-ink-soft">Human reviewer score</div>{report.human_reviewer_score == null
              ? <div className="mt-1 text-lg font-semibold text-ink-soft">Not measured: needs human reviewers</div>
              : <div className="font-display text-3xl font-bold">{report.human_reviewer_score}</div>}</Panel>
          </div>
          <Panel className="mb-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Metric averages</h2>
              <button onClick={() => setTable(!table)} aria-pressed={table} className="rounded border border-line px-2 py-1 text-xs font-medium hover:bg-paper">
                {table ? "Show chart" : "Show table"}
              </button>
            </div>
            {table ? (
              <table className="w-full text-left text-sm">
                <caption className="sr-only">Metric averages</caption>
                <thead className="text-xs uppercase text-ink-soft"><tr><th scope="col" className="py-2">Metric</th><th scope="col" className="py-2">Average</th></tr></thead>
                <tbody>{Object.keys(LABELS).map((k) => <tr key={k} className="border-t border-line"><td className="py-2">{LABELS[k]}</td><td className="py-2 tabular-nums">{pct(report.summary[k] ?? 0)}</td></tr>)}</tbody>
              </table>
            ) : <MetricBars summary={report.summary} />}
            <p className="mt-3 text-xs text-ink-soft">{report.notes}</p>
          </Panel>
          <Panel className="overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <caption className="p-4 text-left font-display text-xl font-semibold">Per case</caption>
              <thead className="border-y border-line bg-paper text-xs uppercase text-ink-soft">
                <tr>
                  <th scope="col" className="p-2">Case</th>
                  {Object.keys(LABELS).map((k) => <th key={k} scope="col" className="p-2">{LABELS[k].replace("Requirement extraction", "Req.")}</th>)}
                </tr>
              </thead>
              <tbody>
                {report.per_case.map((c) => (
                  <tr key={c.case} className="border-b border-line last:border-0">
                    <th scope="row" className="p-2 text-left font-normal"><span className="font-mono text-xs">{c.case}</span> {c.name}</th>
                    {Object.keys(LABELS).map((k) => {
                      const v = Number(c[k]);
                      return <td key={k} className={`p-2 tabular-nums ${v < 1 ? "font-semibold text-[#7a5300]" : ""}`}>{pct(v)}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </>
      )}
    </>
  );
}
