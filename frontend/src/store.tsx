import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, emptyData, type CustomerInfo, type Data } from "./api";

interface Ctx {
  customerId: string | null;
  customer: CustomerInfo | null;
  customers: { id: string; name: string }[];
  data: Data;
  done: string[];
  running: boolean;
  error: string | null;
  llm: string;
  createCustomer: (body: unknown) => Promise<void>;
  selectCustomer: (id: string) => void;
  run: () => Promise<void>;
  approve: () => Promise<void>;
  clearError: () => void;
}

const C = createContext<Ctx | null>(null);
const KEYS: (keyof Data)[] = [
  "requirements", "questions", "systems", "endpoints", "mapping", "architecture",
  "plan", "risks", "tests", "critic", "handoff", "decisions", "patterns",
];

function remember(id: string | null) {
  try { if (id) localStorage.setItem("dm-customer", id); else localStorage.removeItem("dm-customer"); } catch { /* storage unavailable */ }
}

export function Provider({ children }: { children: ReactNode }) {
  const [customerId, setId] = useState<string | null>(() => {
    try { return localStorage.getItem("dm-customer"); } catch { return null; }
  });
  const [customer, setCustomer] = useState<CustomerInfo | null>(null);
  const [customers, setCustomers] = useState<{ id: string; name: string }[]>([]);
  const [data, setData] = useState<Data>(emptyData());
  const [done, setDone] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llm, setLlm] = useState("offline");

  const loadCustomers = useCallback(() => api.customers().then(setCustomers).catch(() => undefined), []);

  useEffect(() => {
    api.health().then((h) => setLlm(h.llm)).catch(() => setError("Backend not reachable. Start it on port 8000."));
    loadCustomers();
  }, [loadCustomers]);

  const refresh = useCallback(async (id: string) => {
    const entries = await Promise.all(KEYS.map(async (k) => [k, await api.section(id, k)] as const));
    setData(Object.fromEntries(entries) as unknown as Data);
  }, []);

  useEffect(() => {
    if (!customerId) { setCustomer(null); setData(emptyData()); setDone([]); return; }
    api.customer(customerId)
      .then((c) => { setCustomer(c); setDone(c.completed_stages); return refresh(customerId); })
      .catch(() => { setId(null); remember(null); });
  }, [customerId, refresh]);

  const selectCustomer = useCallback((id: string) => { remember(id); setId(id); }, []);

  const createCustomer = useCallback(async (body: unknown) => {
    setError(null);
    const { id } = await api.create(body);
    remember(id);
    setData(emptyData());
    setDone([]);
    setId(id);
    loadCustomers();
  }, [loadCustomers]);

  const run = useCallback(async () => {
    if (!customerId) return;
    setRunning(true);
    setError(null);
    setDone([]);
    setData(emptyData());
    try {
      await api.run(customerId, async (stage) => {
        setDone((d) => [...d, stage]);
        await refresh(customerId);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunning(false);
    }
  }, [customerId, refresh]);

  const approve = useCallback(async () => {
    if (!customerId) return;
    try {
      const h = await api.approve(customerId);
      setData((d) => ({ ...d, handoff: h }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval failed");
    }
  }, [customerId]);

  const value = useMemo(
    () => ({ customerId, customer, customers, data, done, running, error, llm,
             createCustomer, selectCustomer, run, approve, clearError: () => setError(null) }),
    [customerId, customer, customers, data, done, running, error, llm, createCustomer, selectCustomer, run, approve],
  );
  return <C.Provider value={value}>{children}</C.Provider>;
}

export const useApp = () => {
  const v = useContext(C);
  if (!v) throw new Error("Provider missing");
  return v;
};
