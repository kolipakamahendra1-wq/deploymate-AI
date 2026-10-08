import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../store";
import { Button, PageTitle, Panel } from "../components/ui/primitives";

const STEPS = ["Brief", "Materials", "Review"];

export default function NewCustomer() {
  const { createCustomer } = useApp();
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [brief, setBrief] = useState("");
  const [openapi, setOpenapi] = useState<unknown>(null);
  const [sample, setSample] = useState<unknown>(null);
  const [err, setErr] = useState("");

  const readJson = (set: (v: unknown) => void) => async (f?: File) => {
    if (!f) return;
    try { set(JSON.parse(await f.text())); setErr(""); } catch { setErr(`${f.name} is not valid JSON`); }
  };

  const loadDemo = async () => {
    const d = await api.demo();
    setName(String(d.name)); setBrief(String(d.brief)); setOpenapi(d.openapi); setSample(d.sample);
  };

  const submit = async () => {
    await createCustomer({ name, brief, openapi, sample });
    nav("/discovery");
  };

  return (
    <>
      <PageTitle title="New customer" hint="Paste the customer brief and attach whatever system material exists. Anything missing stays marked unknown." />
      <ol className="mb-4 flex gap-2" aria-label="Steps">
        {STEPS.map((s, i) => (
          <li key={s} aria-current={i === step ? "step" : undefined}
              className={`rounded-full px-3 py-1 text-sm font-medium ${i === step ? "bg-cobalt text-white" : i < step ? "bg-fact/15 text-fact" : "bg-panel text-ink-soft border border-line"}`}>
            {i + 1}. {s}
          </li>
        ))}
      </ol>
      <Panel>
        {step === 0 && (
          <div className="space-y-4">
            <label className="block text-sm font-medium">Customer name
              <input value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-full rounded-md border border-line bg-white p-2" />
            </label>
            <label className="block text-sm font-medium">Customer brief
              <textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={7} className="mt-1 w-full rounded-md border border-line bg-white p-2" />
            </label>
            <Button variant="ghost" onClick={loadDemo}>Load demo customer</Button>
          </div>
        )}
        {step === 1 && (
          <div className="grid gap-4 md:grid-cols-2">
            {[["OpenAPI spec (JSON)", setOpenapi, openapi], ["Sample record (JSON)", setSample, sample]].map(([label, set, val]) => (
              <label key={String(label)} className="hatched block cursor-pointer rounded-lg border border-dashed border-unknown p-6 text-center text-sm">
                <span className="font-semibold">{String(label)}</span>
                <span className="mt-1 block text-ink-soft">{val ? "Loaded" : "Drop a file or click to choose"}</span>
                <input type="file" accept="application/json,.json" className="sr-only"
                       onChange={(e) => readJson(set as (v: unknown) => void)(e.target.files?.[0])} />
              </label>
            ))}
            {err && <p role="alert" className="text-sm text-[#9b1c1c]">{err}</p>}
          </div>
        )}
        {step === 2 && (
          <dl className="space-y-2 text-sm">
            <div><dt className="font-semibold">Customer</dt><dd>{name || "(unnamed)"}</dd></div>
            <div><dt className="font-semibold">Brief</dt><dd className="whitespace-pre-wrap text-ink-soft">{brief || "(empty)"}</dd></div>
            <div><dt className="font-semibold">OpenAPI spec</dt><dd>{openapi ? "attached" : "none, API stays unknown"}</dd></div>
            <div><dt className="font-semibold">Sample record</dt><dd>{sample ? "attached" : "none"}</dd></div>
          </dl>
        )}
      </Panel>
      <div className="mt-4 flex gap-2">
        <Button variant="ghost" disabled={step === 0} onClick={() => setStep(step - 1)}>Back</Button>
        {step < 2
          ? <Button disabled={step === 0 && (!name || !brief)} onClick={() => setStep(step + 1)}>Next</Button>
          : <Button onClick={submit}>Create customer</Button>}
      </div>
    </>
  );
}
