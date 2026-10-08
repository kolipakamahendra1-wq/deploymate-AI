import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { useApp } from "../store";
import { NAV } from "./nav";

interface Cmd { id: string; label: string; hint: string; run: () => void }

/** Ctrl/Cmd+K palette: jump to any page, run the pipeline, or switch customer. */
export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const nav = useNavigate();
  const { run, customers, selectCustomer, customerId, running } = useApp();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); }
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("dm-open-palette", onOpen);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("dm-open-palette", onOpen); };
  }, []);

  useEffect(() => { if (open) { setQ(""); setIdx(0); setTimeout(() => input.current?.focus(), 0); } }, [open]);

  const cmds = useMemo<Cmd[]>(() => [
    ...NAV.map(([to, label]) => ({ id: `go-${to}`, label, hint: "Go to page", run: () => nav(to) })),
    ...(customerId && !running ? [{ id: "run", label: "Run pipeline", hint: "Action", run: () => { nav("/discovery"); run(); } }] : []),
    ...customers.map((c) => ({ id: `cust-${c.id}`, label: c.name, hint: `Switch customer · ${c.id}`, run: () => selectCustomer(c.id) })),
  ], [nav, run, customers, selectCustomer, customerId, running]);

  const shown = cmds.filter((c) => (c.label + " " + c.hint).toLowerCase().includes(q.toLowerCase())).slice(0, 12);
  if (!open) return null;

  const choose = (c?: Cmd) => { if (c) { setOpen(false); c.run(); } };

  return (
    <div className="fixed inset-0 z-50 grid place-items-start justify-center bg-ink/30 px-4 pt-[12vh]" onClick={() => setOpen(false)}>
      <div role="dialog" aria-modal="true" aria-label="Command palette"
           className="w-full max-w-lg overflow-hidden rounded-lg border border-line bg-panel shadow-xl"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b border-line px-3">
          <Search size={16} aria-hidden className="text-ink-soft" />
          <input
            ref={input} value={q} placeholder="Type a page, action or customer…"
            aria-label="Search commands" aria-controls="dm-cmds"
            aria-activedescendant={shown[idx] ? `cmd-${shown[idx].id}` : undefined}
            onChange={(e) => { setQ(e.target.value); setIdx(0); }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(i + 1, shown.length - 1)); }
              if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)); }
              if (e.key === "Enter") choose(shown[idx]);
              if (e.key === "Escape") setOpen(false);
            }}
            className="w-full bg-transparent py-3 text-sm outline-none"
          />
        </div>
        <ul id="dm-cmds" role="listbox" className="max-h-80 overflow-y-auto py-1">
          {shown.length === 0 && <li className="px-4 py-3 text-sm text-ink-soft">No matches</li>}
          {shown.map((c, i) => (
            <li key={c.id} id={`cmd-${c.id}`} role="option" aria-selected={i === idx}
                onMouseEnter={() => setIdx(i)} onClick={() => choose(c)}
                className={`flex cursor-pointer items-center justify-between px-4 py-2 text-sm ${i === idx ? "bg-cobalt text-white" : ""}`}>
              <span>{c.label}</span>
              <span className={`text-xs ${i === idx ? "text-white/80" : "text-ink-soft"}`}>{c.hint}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
