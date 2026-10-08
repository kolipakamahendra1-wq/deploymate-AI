import { NavLink, Outlet } from "react-router-dom";
import { useApp } from "../store";

export const NAV = [
  ["/", "New Customer"],
  ["/discovery", "Discovery"],
  ["/systems", "Systems"],
  ["/mapping", "Data Mapping"],
  ["/architecture", "Architecture"],
  ["/plan", "Implementation Plan"],
  ["/risks", "Risks"],
  ["/validation", "Validation"],
  ["/handoff", "Handoff"],
] as const;

export default function Shell() {
  const { llm, error, customerId } = useApp();
  return (
    <div className="flex min-h-full">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-cobalt focus:p-2 focus:text-white">
        Skip to content
      </a>
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line bg-panel p-4 md:flex">
        <div className="mb-6 flex items-center gap-2">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <span className="font-display text-lg font-bold">DeployMate AI</span>
        </div>
        <nav aria-label="Primary" className="flex flex-col gap-1">
          {NAV.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-cobalt text-white" : "text-ink hover:bg-paper"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <p className="mt-auto text-xs text-ink-soft">
          LLM: <strong>{llm === "live" ? "free hosted model" : "offline cache"}</strong>
          <br />
          Customer: <span className="font-mono">{customerId ?? "none"}</span>
        </p>
      </aside>
      <div className="min-w-0 flex-1">
        <nav aria-label="Primary mobile" className="flex gap-1 overflow-x-auto border-b border-line bg-panel p-2 md:hidden">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `whitespace-nowrap rounded px-3 py-1.5 text-sm ${isActive ? "bg-cobalt text-white" : ""}`}>
              {label}
            </NavLink>
          ))}
        </nav>
        {error && (
          <div role="alert" className="border-b border-[#9b1c1c]/30 bg-[#fde8e8] px-6 py-2 text-sm text-[#9b1c1c]">
            {error}
          </div>
        )}
        <main id="main" className="mx-auto max-w-6xl p-6 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
