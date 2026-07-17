import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type Session = {
  session_id: string;
  last_seen: string;
  request_count: number;
  tokens_saved: number;
};

const proxyRoot = (process.env.AGENTWARDEN_URL ?? "http://127.0.0.1:8080").replace(/\/$/, "");

export async function GET(request: NextRequest) {
  const requestedSession = request.nextUrl.searchParams.get("session_id");
  try {
    const sessionsResponse = await fetch(`${proxyRoot}/sessions`, { cache: "no-store" });
    if (!sessionsResponse.ok) throw new Error(`sessions returned ${sessionsResponse.status}`);
    const sessionsPayload = (await sessionsResponse.json()) as { sessions: Session[] };
    const sessions = sessionsPayload.sessions ?? [];
    const sessionId = requestedSession || sessions[0]?.session_id || "default";
    const [statsResponse, tracesResponse, configResponse] = await Promise.all([
      fetch(`${proxyRoot}/stats?session_id=${encodeURIComponent(sessionId)}`, { cache: "no-store" }),
      fetch(`${proxyRoot}/traces?session_id=${encodeURIComponent(sessionId)}`, { cache: "no-store" }),
      fetch(`${proxyRoot}/config`, { cache: "no-store" }),
    ]);
    if (!statsResponse.ok || !tracesResponse.ok || !configResponse.ok) throw new Error("proxy endpoints unavailable");
    return NextResponse.json({
      source: "live",
      proxyRoot,
      sessions,
      stats: await statsResponse.json(),
      traces: (await tracesResponse.json()).traces ?? [],
      config: await configResponse.json(),
    });
  } catch (error) {
    return NextResponse.json({
      source: "sample",
      proxyRoot,
      sessions: sample.sessions,
      stats: sample.stats,
      traces: sample.traces,
      config: sample.config,
      warning: error instanceof Error ? error.message : "Unable to reach AgentWarden",
    });
  }
}

const sample = {
  sessions: [
    { session_id: "external-support-demo", last_seen: new Date().toISOString(), request_count: 6, tokens_saved: 687 },
  ],
  stats: {
    session_id: "external-support-demo",
    request_count: 6,
    totals: { tokens_total_input: 4474, tokens_output: 211, tokens_total: 4685, tokens_saved: 687, latency_ms: 11840 },
    per_segment: { system: 486, tools: 1893, history: 1748, current: 347 },
    cost_estimate_usd: 0.01435,
    models: [{ model: "gpt-5.6-terra", request_count: 6, tokens_total_input: 4474, tokens_output: 211, cost_estimate_usd: 0.01435 }],
  },
  traces: [
    { id: 1, ts: "2026-07-18T00:00:00Z", tokens_total_input: 560, tokens_output: 21, tokens_saved: 0, tools_offered: ["get_ticket", "get_customer_plan", "search_knowledge_base", "get_recent_incidents", "get_escalation_policy", "refund_invoice", "change_subscription", "disable_account", "rotate_api_key", "create_sales_lead", "send_marketing_email"], tools_called: ["get_ticket"], optimizations_applied: ["cache_order"], latency_ms: 2067 },
    { id: 2, ts: "2026-07-18T00:00:02Z", tokens_total_input: 689, tokens_output: 22, tokens_saved: 0, tools_offered: ["get_ticket", "get_customer_plan", "search_knowledge_base", "get_recent_incidents", "get_escalation_policy", "refund_invoice", "change_subscription", "disable_account", "rotate_api_key", "create_sales_lead", "send_marketing_email"], tools_called: ["get_customer_plan"], optimizations_applied: ["cache_order"], latency_ms: 1814 },
    { id: 3, ts: "2026-07-18T00:00:04Z", tokens_total_input: 800, tokens_output: 23, tokens_saved: 0, tools_offered: ["get_ticket", "get_customer_plan", "search_knowledge_base", "get_recent_incidents", "get_escalation_policy", "refund_invoice", "change_subscription", "disable_account", "rotate_api_key", "create_sales_lead", "send_marketing_email"], tools_called: ["search_knowledge_base"], optimizations_applied: ["cache_order"], latency_ms: 1902 },
    { id: 4, ts: "2026-07-18T00:00:06Z", tokens_total_input: 693, tokens_output: 23, tokens_saved: 229, tools_offered: ["get_ticket", "get_customer_plan", "search_knowledge_base", "get_recent_incidents", "get_escalation_policy"], tools_called: ["get_recent_incidents"], optimizations_applied: ["tool_prune", "cache_order"], latency_ms: 1465 },
    { id: 5, ts: "2026-07-18T00:00:08Z", tokens_total_input: 805, tokens_output: 24, tokens_saved: 229, tools_offered: ["get_ticket", "get_customer_plan", "search_knowledge_base", "get_recent_incidents", "get_escalation_policy"], tools_called: ["get_escalation_policy"], optimizations_applied: ["tool_prune", "cache_order"], latency_ms: 1524 },
    { id: 6, ts: "2026-07-18T00:00:10Z", tokens_total_input: 927, tokens_output: 98, tokens_saved: 229, tools_offered: ["get_ticket", "get_customer_plan", "search_knowledge_base", "get_recent_incidents", "get_escalation_policy"], tools_called: [], optimizations_applied: ["tool_prune", "cache_order"], latency_ms: 3068 },
  ],
  config: {
    optimizer_flags: { tool_prune: true, history_trim: true, context_dedup: true, cache_order: true },
    session_budget_usd: 0.02,
    runtime_only: true,
  },
};
