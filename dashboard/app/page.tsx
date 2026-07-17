"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, ArrowDownRight, CheckCircle2, ChevronDown, CircleDollarSign, Clock3, Database, RefreshCw, Settings2, ShieldCheck, Sparkles, Wrench } from "lucide-react";

type Trace = {
  id: number;
  ts: string;
  tokens_total_input: number;
  tokens_output: number;
  tokens_saved: number;
  tools_offered: string[];
  tools_called: string[];
  optimizations_applied: string[];
  latency_ms: number;
};

type DashboardData = {
  source: "live" | "sample";
  proxyRoot: string;
  sessions: { session_id: string; last_seen: string; request_count: number; tokens_saved: number }[];
  stats: {
    session_id: string;
    request_count: number;
    totals: { tokens_total_input: number; tokens_output: number; tokens_total: number; tokens_saved: number; latency_ms: number };
    per_segment: Record<string, number>;
    cost_estimate_usd: number;
    models: { model: string }[];
  };
  traces: Trace[];
  config: { optimizer_flags: Record<string, boolean>; session_budget_usd: number | null; runtime_only: boolean };
  warning?: string;
};

const segmentColors: Record<string, string> = {
  system: "#20252d",
  tools: "#89ad61",
  history: "#85b7cf",
  current: "#d9b765",
};

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [selectedSession, setSelectedSession] = useState("");
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  const load = useCallback(async (sessionId?: string) => {
    setLoading(true);
    try {
      const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
      const response = await fetch(`/api/dashboard${query}`, { cache: "no-store" });
      const next = (await response.json()) as DashboardData;
      setData(next);
      setSelectedSession(next.stats.session_id);
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const view = useMemo(() => {
    if (!data) return null;
    const { totals, per_segment } = data.stats;
    const beforeInput = totals.tokens_total_input + totals.tokens_saved;
    const savedPercent = beforeInput ? (totals.tokens_saved / beforeInput) * 100 : 0;
    const segmentTotal = Object.values(per_segment).reduce((sum, value) => sum + value, 0) || 1;
    const traces = [...data.traces].reverse();
    return { totals, per_segment, beforeInput, savedPercent, segmentTotal, traces };
  }, [data]);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="mark" aria-label="AgentWarden">AW</div>
        <nav aria-label="Dashboard navigation">
          <a className="nav-item active" href="#overview" title="Overview"><Activity size={18} /><span>Overview</span></a>
          <a className="nav-item" href="#comparison" title="Savings"><ArrowDownRight size={18} /><span>Savings</span></a>
          <a className="nav-item" href="#traces" title="Traces"><Database size={18} /><span>Traces</span></a>
        </nav>
        <div className="sidebar-foot"><ShieldCheck size={18} /><span>Local only</span></div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Local agent observability</p>
            <h1>Agent<span>Warden</span></h1>
          </div>
          <div className="topbar-actions">
            <span className={`status ${data?.source === "live" ? "live" : "sample"}`}>
              <i /> {data?.source === "live" ? "Proxy connected" : "Sample receipt"}
            </span>
            <button className="icon-button" type="button" onClick={() => void load(selectedSession)} title="Refresh dashboard" disabled={loading}>
              <RefreshCw size={17} className={loading ? "spin" : ""} />
            </button>
            <button className={`icon-button ${showSettings ? "selected" : ""}`} type="button" onClick={() => setShowSettings((open) => !open)} title="Runtime settings">
              <Settings2 size={17} />
            </button>
          </div>
        </header>

        {data?.source === "sample" && <p className="notice">Proxy unavailable at {data.proxyRoot}. Showing a sample receipt until it reconnects.</p>}
        {showSettings && data && <SettingsPanel config={data.config} source={data.source} onSaved={() => void load(selectedSession)} />}

        <section className="session-row" id="overview">
          <div>
            <p className="eyebrow">Session receipt</p>
            <div className="session-select-wrap">
              <select value={selectedSession} onChange={(event) => void load(event.target.value)} aria-label="Select a session">
                {data?.sessions.map((session) => <option key={session.session_id} value={session.session_id}>{session.session_id}</option>)}
              </select>
              <ChevronDown size={16} />
            </div>
          </div>
          <div className="run-meta">
            <span><Clock3 size={15} /> {view ? formatDuration(view.totals.latency_ms) : "--"} total</span>
            <span>{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Loading"}</span>
          </div>
        </section>

        {!view ? <div className="loading-state">Loading your local receipt...</div> : <>
          <section className="metric-grid" aria-label="Session summary">
            <Metric icon={<Sparkles size={18} />} label="Input tokens avoided" value={formatNumber(view.totals.tokens_saved)} detail={`${view.savedPercent.toFixed(1)}% less context`} accent="green" />
            <Metric icon={<CircleDollarSign size={18} />} label="Estimated spend" value={formatCurrency(data?.stats.cost_estimate_usd ?? 0)} detail="Input + output tokens" accent="blue" />
            <Metric icon={<Wrench size={18} />} label="Tool schemas removed" value={String(Math.max(0, (view.traces[0]?.tools_offered.length ?? 0) - (view.traces.at(-1)?.tools_offered.length ?? 0)))} detail="After warm-up" accent="gold" />
            <Metric icon={<CheckCircle2 size={18} />} label="Behavior check" value="Held" detail={`${data?.stats.request_count ?? 0} requests traced`} accent="dark" />
          </section>

          <section className="analysis-grid" id="comparison">
            <article className="before-after panel">
              <div className="panel-heading"><div><p className="eyebrow">Before / after</p><h2>Context sent upstream</h2></div><span className="success-pill"><ArrowDownRight size={14} /> {view.savedPercent.toFixed(1)}%</span></div>
              <div className="comparison-bars">
                <ComparisonRow label="Without AgentWarden" tokens={view.beforeInput} max={view.beforeInput} tone="before" />
                <ComparisonRow label="With AgentWarden" tokens={view.totals.tokens_total_input} max={view.beforeInput} tone="after" />
              </div>
              <div className="proof-line"><ShieldCheck size={17} /><span>Same tool sequence completed through the proxy.</span></div>
            </article>

            <article className="segment-panel panel">
              <div className="panel-heading"><div><p className="eyebrow">Token anatomy</p><h2>Where input context went</h2></div><span className="muted">{formatNumber(view.totals.tokens_total_input)} total</span></div>
              <div className="segmented-bar" aria-label="Input token segment breakdown">
                {Object.entries(view.per_segment).map(([name, value]) => <span key={name} style={{ width: `${(value / view.segmentTotal) * 100}%`, background: segmentColors[name] ?? "#9aa6ad" }} />)}
              </div>
              <div className="legend">
                {Object.entries(view.per_segment).map(([name, value]) => <div key={name}><i style={{ background: segmentColors[name] ?? "#9aa6ad" }} /><span>{name}</span><strong>{formatNumber(value)}</strong></div>)}
              </div>
            </article>
          </section>

          <section className="trace-section" id="traces">
            <div className="section-title"><div><p className="eyebrow">Request timeline</p><h2>Trace evidence</h2></div><span className="muted">{view.traces.length} requests</span></div>
            <div className="trace-table-wrap">
              <table>
                <thead><tr><th>Request</th><th>Tools offered</th><th>Called</th><th>Input</th><th>Saved</th><th>Passes applied</th><th>Latency</th></tr></thead>
                <tbody>
                  {view.traces.map((trace, index) => <tr key={trace.id}>
                    <td><span className="request-number">{String(index + 1).padStart(2, "0")}</span></td>
                    <td>{trace.tools_offered.length}</td>
                    <td>{trace.tools_called.length ? trace.tools_called.join(", ") : <span className="muted">Final answer</span>}</td>
                    <td>{formatNumber(trace.tokens_total_input)}</td>
                    <td className={trace.tokens_saved ? "saved" : "muted"}>{trace.tokens_saved ? `-${formatNumber(trace.tokens_saved)}` : "--"}</td>
                    <td><div className="tags">{trace.optimizations_applied.length ? trace.optimizations_applied.map((name) => <span key={name}>{name.replace("_", " ")}</span>) : <span className="muted">--</span>}</div></td>
                    <td>{formatDuration(trace.latency_ms)}</td>
                  </tr>)}
                </tbody>
              </table>
            </div>
          </section>
        </>}
      </section>
    </main>
  );
}

function Metric({ icon, label, value, detail, accent }: { icon: React.ReactNode; label: string; value: string; detail: string; accent: string }) {
  return <article className={`metric metric-${accent}`}><div className="metric-icon">{icon}</div><div><p>{label}</p><strong>{value}</strong><span>{detail}</span></div></article>;
}

function ComparisonRow({ label, tokens, max, tone }: { label: string; tokens: number; max: number; tone: "before" | "after" }) {
  return <div className="comparison-row"><div><span>{label}</span><strong>{formatNumber(tokens)} tokens</strong></div><div className="bar-track"><i className={tone} style={{ width: `${Math.max(5, (tokens / max) * 100)}%` }} /></div></div>;
}

function SettingsPanel({ config, source, onSaved }: { config: DashboardData["config"]; source: DashboardData["source"]; onSaved: () => void }) {
  const [flags, setFlags] = useState(config.optimizer_flags);
  const [budget, setBudget] = useState(config.session_budget_usd?.toString() ?? "");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setFlags(config.optimizer_flags);
    setBudget(config.session_budget_usd?.toString() ?? "");
  }, [config]);

  async function save() {
    if (source !== "live") return;
    setSaving(true);
    setMessage("");
    try {
      const parsedBudget = budget.trim() === "" ? null : Number(budget);
      if (parsedBudget !== null && (!Number.isFinite(parsedBudget) || parsedBudget < 0)) {
        setMessage("Enter a non-negative budget.");
        return;
      }
      const response = await fetch("/api/config", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...flags, session_budget_usd: parsedBudget }),
      });
      if (!response.ok) throw new Error("Proxy rejected the setting update");
      setMessage("Applied to the running proxy.");
      onSaved();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to update settings.");
    } finally {
      setSaving(false);
    }
  }

  return <section className="settings-panel" aria-label="Runtime settings">
    <div className="panel-heading"><div><p className="eyebrow">Live controls</p><h2>Optimizer settings</h2></div><span className="muted">Runtime only</span></div>
    <div className="toggle-grid">
      {Object.entries(flags).map(([name, enabled]) => <label className="toggle-row" key={name}>
        <span><strong>{name.replace("_", " ")}</strong><small>{settingDescription(name)}</small></span>
        <input type="checkbox" checked={enabled} disabled={source !== "live"} onChange={(event) => setFlags({ ...flags, [name]: event.target.checked })} />
        <i aria-hidden="true" />
      </label>)}
    </div>
    <div className="budget-control"><label htmlFor="budget">Session budget warning</label><div><span>$</span><input id="budget" type="number" min="0" step="0.01" value={budget} disabled={source !== "live"} onChange={(event) => setBudget(event.target.value)} placeholder="No warning" /></div><small>Warns in responses; it does not stop the agent.</small></div>
    <div className="settings-actions"><button className="save-button" type="button" onClick={() => void save()} disabled={saving || source !== "live"}>{saving ? "Applying..." : "Apply settings"}</button>{message && <span className="settings-message">{message}</span>}</div>
  </section>;
}

function settingDescription(name: string) {
  return ({ tool_prune: "Removes unused schemas after warm-up.", history_trim: "Clips old tool-result context.", context_dedup: "Replaces repeated history blocks.", cache_order: "Stabilizes the static request prefix." } as Record<string, string>)[name] ?? "";
}

function formatNumber(value: number) { return new Intl.NumberFormat("en-US").format(value); }
function formatCurrency(value: number) { return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 4 }).format(value); }
function formatDuration(value: number) { return `${(value / 1000).toFixed(value >= 10_000 ? 1 : 2)}s`; }
