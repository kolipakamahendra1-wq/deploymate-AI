import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, emptyData, type Data } from "./api";

interface Ctx {
  customerId: string | null;
  data: Data;
  done: string[];
  running: boolean;
  error: string | null;
  llm: string;
  createCustomer: (body: unknown) => Promise<void>;
  run: () => Promise<void>;
  approve: () => Promise<void>;
}

const C = createContext<Ctx | null>(null);
const KEYS: (keyof Data)[] = [
  "requirements", "questions", "systems", "endpoints", "mapping", "architecture",
  "plan", "risks", "tests", "critic", "handoff", "decisions",
];

export function Provider({ children }: { children: ReactNode }) {
  const [customerId, setId] = useState<string | null>(() => {
    try { return localStorage.getItem("dm-customer"); } catch { return null; }
  });
  const [data, setData] = useState<Data>(emptyData());
  const [done, setDone] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llm, setLlm] = useState("cache");

  useEffect(() => { api.health().then((h) => setLlm(h.llm)).catch(() => setError("Backend not reachable on :8000")); }, []);

  const refresh = useCallback(async (id: string) => {
    const entries = await Promise.all(KEYS.map(async (k) => [k, await api.section(id, k)] as const));
    setData(Object.fromEntries(entries) as unknown as Data);
  }, []);

  useEffect(() => {
    if (!customerId) return;
    refresh(customerId).catch(() => { setId(null); });
    fetch(`/api/customers/${customerId}`).then((r) => r.json()).then((c) => setDone(c.completed_stages ?? [])).catch(() => undefined);
  }, [customerId, refresh]);

  const createCustomer = useCallback(async (body: unknown) => {
    setError(null);
    const { id } = await api.create(body);
    try { localStorage.setItem("dm-customer", id); } catch { /* storage unavailable */ }
    setData(emptyData());
    setDone([]);
    setId(id);
  }, []);

  const run = useCallback(async () => {
    if (!customerId) return;
    setRunning(true);
    setError(null);
    setDone([]);
    try {
      await api.run(customerId, async (stage) => {
        setDone((d) => [...d, stage]);
        await refresh(customerId);
      });
      await refresh(customerId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunning(false);
    }
  }, [customerId, refresh]);

  const approve = useCallback(async () => {
    if (!customerId) return;
    const h = await api.approve(customerId);
    setData((d) => ({ ...d, handoff: h }));
  }, [customerId]);

  const value = useMemo(
    () => ({ customerId, data, done, running, error, llm, createCustomer, run, approve }),
    [customerId, data, done, running, error, llm, createCustomer, run, approve],
  );
  return <C.Provider value={value}>{children}</C.Provider>;
}

export const useApp = () => {
  const v = useContext(C);
  if (!v) throw new Error("Provider missing");
  return v;
};
