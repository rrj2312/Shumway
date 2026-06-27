const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface WatchlistEntry {
  company_id: string;
  quarter: string;
  hazard_probability: number;
  risk_tier: "LOW" | "ELEVATED" | "HIGH";
  score_delta: number | null;
  red_signal_count: number;
}

export interface Signal {
  name: string;
  value: number | null;
  unit: string;
  status: "GREEN" | "AMBER" | "RED" | "UNKNOWN";
  description: string;
}

export interface HistoryEntry {
  quarter: string;
  hazard_probability: number;
  risk_tier: string;
  score_delta: number | null;
  red_signal_count: number;
}

export interface AlertEntry {
  company_id: string;
  signal: string;
  severity: "warning" | "critical";
  message: string;
  created_at: string;
}

export interface DatasetStats {
  total_companies: number;
  total_company_years: number;
  documented_distress_events: number;
  year_range: { min: string; max: string };
  note: string;
}

export interface KnownDistressEvent {
  distress: number;
  event_type: string;
  source_note: string;
}

export interface CompanyDashboard {
  company_id: string;
  score: {
    quarter: string;
    hazard_probability: number;
    risk_tier: string;
    score_delta: number | null;
    red_signal_count: number;
  } | null;
  features: Record<string, number | null> | null;
  history: HistoryEntry[];
  known_distress_event: KnownDistressEvent | null;
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`);
  return res.json();
}

export const api = {
  stats:     ()           => apiFetch<DatasetStats>("/stats"),
  watchlist: (limit = 50) => apiFetch<WatchlistEntry[]>(`/watchlist?limit=${limit}`),
  dashboard: (id: string) => apiFetch<CompanyDashboard>(`/company/${encodeURIComponent(id)}`),
  signals:   (id: string) => apiFetch<{ signals: Signal[] }>(`/company/${encodeURIComponent(id)}/signals`),
  history:   (id: string) => apiFetch<{ history: HistoryEntry[] }>(`/company/${encodeURIComponent(id)}/history`),
  alerts:    (limit = 50) => apiFetch<AlertEntry[]>(`/alerts?limit=${limit}`),
  search:    (q: string)  => apiFetch<string[]>(`/search?q=${encodeURIComponent(q)}`),
};