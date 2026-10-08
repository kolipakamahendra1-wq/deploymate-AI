import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { Prov } from "../../api";

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-lg border border-line bg-panel p-5 ${className}`}>{children}</section>;
}

export function Button({
  variant = "primary", className = "", ...p
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }) {
  const base = "inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const v = variant === "primary"
    ? "bg-cobalt text-white hover:bg-[#1f3ed1]"
    : "border border-line bg-panel text-ink hover:bg-paper";
  return <button className={`${base} ${v} ${className}`} {...p} />;
}

const PROV: Record<Prov, { label: string; cls: string; icon: string }> = {
  fact: { label: "Verified fact", cls: "bg-white text-[#08665c] border-fact", icon: "●" },
  assumption: { label: "Assumption", cls: "bg-white text-[#7a5300] border-assume", icon: "◐" },
  unknown: { label: "Unknown", cls: "bg-white text-ink border-unknown border-dashed", icon: "○" },
};

/** Fact / assumption / unknown marker. Never colour alone: icon + text label too. */
export function ProvBadge({ p, source }: { p: Prov; source?: string | null }) {
  const m = PROV[p];
  return (
    <span
      title={source ? `Source: ${source}` : undefined}
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${m.cls}`}
    >
      <span aria-hidden>{m.icon}</span>
      {m.label}
    </span>
  );
}

export function provBorder(p: Prov) {
  return p === "fact" ? "border-l-fact" : p === "assumption" ? "border-l-assume" : "border-l-unknown";
}

export function Mono({ children }: { children: ReactNode }) {
  return <code className="font-mono text-[13px] text-ink">{children}</code>;
}

export function PageTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <header className="mb-6">
      <h1 className="text-3xl font-bold">{title}</h1>
      {hint && <p className="mt-1 max-w-2xl text-ink-soft">{hint}</p>}
    </header>
  );
}

export function Empty({ what }: { what: string }) {
  return (
    <div className="hatched rounded-lg border border-dashed border-unknown/60 p-8 text-center text-ink-soft">
      No {what} yet. Create a customer and run the pipeline from the Discovery page.
    </div>
  );
}

export function SeverityTag({ s }: { s: "high" | "medium" | "low" | "error" | "warning" }) {
  const cls = s === "high" || s === "error" ? "bg-[#fde8e8] text-[#9b1c1c]" : s === "medium" || s === "warning" ? "bg-assume/15 text-[#8a5f00]" : "bg-fact/10 text-[#08665c]";
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${cls}`}>{s}</span>;
}
