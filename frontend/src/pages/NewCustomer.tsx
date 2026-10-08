import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../store";
import { Button, PageTitle, Panel } from "../components/ui/primitives";

const STEPS = ["Brief", "Materials", "Review"];

interface Attachment { name: string; value: unknown }

async function readFile(f: File): Promise<Attachment> {
  const text = await f.text();
  // JSON is sent as data; YAML and CSV are sent as text and parsed by the backend.
  if (/\.json$/i.test(f.name)) return { name: f.name, value: JSON.parse(text) };
  return { name: f.name, value: text };
}

function Dropzone({ label, accept, att, onFile, onClear }: {
  label: string; accept: string; att: Attachment | null; onFile: (f: File) => void; onClear: () => void;
}) {
  const [over, setOver] = useState(false);
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}
      className={`rounded-lg border border-dashed p-6 text-center text-sm ${over ? "border-cobalt bg-cobalt/5" : "hatched border-unknown"}`}
    >
      <p className="font-semibold">{label}</p>
      {att ? (
        <p className="mt-1">
          <span className="font-mono">{att.name}</span>{" "}
          <button className="ml-2 text-cobalt underline" onClick={onClear}>Remove</button>
        </p>
      ) : (
        <label className="mt-1 block cursor-pointer text-ink-soft">
          Drop a file here or <span className="text-cobalt underline">choose one</span>
          <input type="file" accept={accept} className="sr-only" onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
        </label>
      )}
    </div>
  );
}

export default function NewCustomer() {
  const { createCustomer } = useApp();
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [brief, setBrief] = useState("");
  const [openapi, setOpenapi] = useState<Attachment | null>(null);
  const [sample, setSample] = useState<Attachment | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const attach = (set: (a: Attachment | null) => void) => async (f: File) => {
    try { set(await readFile(f)); setErr(""); } catch { setErr(`${f.name} could not be read as JSON`); }
  };

  const loadDemo = async () => {
    const d = await api.demo();
    setName(d.name); setBrief(d.brief);
    setOpenapi({ name: "order_platform.openapi.json", value: d.openapi });
    setSample({ name: "fulfillment_sample.json", value: d.sample });
  };

  const submit = async () => {
    setBusy(true);
    try {
      await createCustomer({ name, brief, openapi: openapi?.value ?? null, sample: sample?.value ?? null });
      nav("/discovery");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not create customer");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageTitle title="New customer" hint="Paste the customer brief and attach whatever system material exists. Anything missing stays marked unknown." />
      <ol className="mb-4 flex flex-wrap gap-2" aria-label="Steps">
        {STEPS.map((s, i) => (
          <li key={s} aria-current={i === step ? "step" : undefined}
              className={`rounded-full px-3 py-1 text-sm font-medium ${i === step ? "bg-cobalt text-white" : i < step ? "bg-fact/15 text-[#08665c]" : "border border-line bg-panel text-ink-soft"}`}>
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
              <textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={7}
                        placeholder="We need to connect our order platform to our internal fulfillment system…"
                        className="mt-1 w-full rounded-md border border-line bg-white p-2" />
            </label>
            <Button variant="ghost" onClick={loadDemo}>Load demo customer</Button>
          </div>
        )}
        {step === 1 && (
          <div className="grid gap-4 md:grid-cols-2">
            <Dropzone label="OpenAPI spec (JSON or YAML)" accept=".json,.yaml,.yml,application/json" att={openapi}
                      onFile={attach(setOpenapi)} onClear={() => setOpenapi(null)} />
            <Dropzone label="Sample records (JSON or CSV)" accept=".json,.csv,application/json,text/csv" att={sample}
                      onFile={attach(setSample)} onClear={() => setSample(null)} />
          </div>
        )}
        {step === 2 && (
          <dl className="space-y-2 text-sm">
            <div><dt className="font-semibold">Customer</dt><dd>{name}</dd></div>
            <div><dt className="font-semibold">Brief</dt><dd className="whitespace-pre-wrap text-ink-soft">{brief}</dd></div>
            <div><dt className="font-semibold">OpenAPI spec</dt><dd>{openapi ? openapi.name : "none: APIs stay unknown"}</dd></div>
            <div><dt className="font-semibold">Sample records</dt><dd>{sample ? sample.name : "none: field mapping needs a sample"}</dd></div>
          </dl>
        )}
        {err && <p role="alert" className="mt-3 text-sm text-[#9b1c1c]">{err}</p>}
      </Panel>
      <div className="mt-4 flex gap-2">
        <Button variant="ghost" disabled={step === 0} onClick={() => setStep(step - 1)}>Back</Button>
        {step < 2
          ? <Button disabled={step === 0 && (!name.trim() || !brief.trim())} onClick={() => setStep(step + 1)}>Next</Button>
          : <Button onClick={submit} disabled={busy}>{busy ? "Creating…" : "Create customer"}</Button>}
      </div>
    </>
  );
}
