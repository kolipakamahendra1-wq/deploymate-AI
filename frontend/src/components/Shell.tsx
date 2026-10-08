import { NavLink, Outlet } from "react-router-dom";
import { Command, X } from "lucide-react";
import { useApp } from "../store";
import CommandPalette from "./CommandPalette";
import { NAV } from "./nav";

function CustomerSwitcher() {
  const { customers, customerId, selectCustomer } = useApp();
  if (!customers.length) return null;
  return (
    <label className="mb-4 block text-xs font-medium text-ink-soft">
      Customer
      <select
        value={customerId ?? ""}
        onChange={(e) => selectCustomer(e.target.value)}
        className="mt-1 w-full rounded-md border border-line bg-white p-2 text-sm text-ink"
      >
        {!customerId && <option value="">Select a customer</option>}
        {customers.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.id})</option>)}
      </select>
    </label>
  );
}

export default function Shell() {
  const { llm, error, clearError, customer } = useApp();
  return (
    <div className="flex min-h-full">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-cobalt focus:p-2 focus:text-white">
        Skip to content
      </a>
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line bg-panel p-4 md:flex print:hidden">
        <div className="mb-5 flex items-center gap-2">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <span className="font-display text-lg font-bold">DeployMate AI</span>
        </div>
        <CustomerSwitcher />
        <nav aria-label="Primary" className="flex flex-col gap-0.5">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) => `rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-cobalt text-white" : "text-ink hover:bg-paper"}`}>
              {label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={() => window.dispatchEvent(new Event("dm-open-palette"))}
          className="mt-4 flex items-center justify-between rounded-md border border-line px-3 py-2 text-xs text-ink-soft hover:bg-paper"
        >
          <span className="flex items-center gap-1.5"><Command size={14} aria-hidden /> Command palette</span>
          <kbd className="font-mono">Ctrl K</kbd>
        </button>
        <p className="mt-auto text-xs text-ink-soft">
          Agents: <strong className="text-ink">{llm === "live" ? "free hosted model" : "offline"}</strong>
          {customer?.recorded_demo && <><br />Demo customer: recorded outputs</>}
        </p>
      </aside>
      <div className="min-w-0 flex-1">
        <nav aria-label="Primary mobile" className="flex gap-1 overflow-x-auto border-b border-line bg-panel p-2 md:hidden print:hidden">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `whitespace-nowrap rounded px-3 py-1.5 text-sm ${isActive ? "bg-cobalt text-white" : ""}`}>
              {label}
            </NavLink>
          ))}
        </nav>
        {error && (
          <div role="alert" className="flex items-center justify-between border-b border-[#9b1c1c]/30 bg-[#fde8e8] px-6 py-2 text-sm text-[#9b1c1c]">
            {error}
            <button onClick={clearError} aria-label="Dismiss error"><X size={16} /></button>
          </div>
        )}
        <main id="main" className="mx-auto max-w-6xl p-4 md:p-8">
          <Outlet />
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
