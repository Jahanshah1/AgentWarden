# AgentWarden — Project Context

## Mission
AgentWarden is an open-source, drop-in proxy that sits between an AI agent
and the OpenAI API. It automatically reduces input-token waste (typically
40–60%) WITHOUT changing the agent's behavior, and PROVES quality held via
a replay verifier. One-line adoption: the developer changes only
`base_url` to point at AgentWarden.

Tagline: "Observability tools show you the bill. AgentWarden shrinks it —
and proves nothing broke."

This is a 5-day hackathon build (OpenAI Build Week, deadline July 21).
Bias every decision toward: working > perfect, demoable > complete,
deterministic > clever.

## Why the waste exists (core insight)
Agents are loops. Every loop step re-sends the ENTIRE conversation —
system prompt, all tool schemas, every past tool output — so input cost
grows quadratically with steps. Most of that re-sent context is dead
weight: tool schemas that are never invoked, stale tool outputs from
10 steps ago, duplicated file contents. AgentWarden removes the dead
weight in transit.

## What it does (v1 scope — ONLY these)
1. TRANSPARENT PROXY: OpenAI-compatible `/v1/chat/completions`,
   streaming (SSE) and non-streaming, client's own Authorization header
   passed through. Never store or log API keys.
2. TRACING: per-request token accounting by segment (system / tools /
   history / current turn), persisted to SQLite.
3. OPTIMIZER PASSES (each independently toggleable in config):
   a. tool_prune  — forward only tool schemas the session has actually
      used (learned from traces), plus any tool named in the current
      user message. First N=3 requests of a new session pass untouched.
   b. history_trim — keep last N=5 turns verbatim; clip older
      tool-role messages to first 300 tokens + "…[trimmed by
      agentwarden]". NEVER touch: system message, any assistant message
      containing tool_calls, the current turn.
   c. context_dedup — identical content blocks appearing multiple times
      in history: keep first occurrence, replace later ones with
      "[duplicate of earlier content — see above]".
   d. cache_order — serialize the static prefix (system + tools)
      byte-identically across requests in a session so provider-side
      prompt caching fires.
4. BUDGET GUARD: per-session cost threshold in config; when crossed,
   add response header `X-AgentWarden-Budget-Warning` and log loudly.
5. REPLAY VERIFIER (`replay/verify.py`): re-runs a recorded task with
   optimizations OFF vs ON, reports: tokens & cost each, tool-call
   sequence diff (exact match), tests passed (when the task has a test
   suite), answer similarity (GPT-5.6-as-judge, single call, secondary
   signal only).
6. DASHBOARD (Next.js, /dashboard dir): live session cost, segment
   waterfall, before/after comparison, savings metrics panel,
   no-regression badge.
7. DEMO AGENT (`demo_agent/`): a minimal coding agent (~15 tools:
   read_file, write_file, run_tests, grep, list_dir + plausible decoys)
   pointed at `demo_agent/sample_repo/` which contains 3–4 planted bugs
   and a pytest suite of 8 tests. Task: "make all tests pass."
   Deterministic where possible. This is both the test harness and the
   demo video star.

## Explicit NON-goals (do not build, do not suggest)
- Model routing to cheaper models (contradicts the "same behavior,
  verified" story; out of scope)
- LLM summarization of history (deletion is deterministic and can't
  hallucinate; summarization is at most a future off-by-default flag)
- Auth, multi-tenancy, rate limiting, non-OpenAI providers, response
  caching. v1 is localhost, single user.

## Architecture & layout
proxy/
  server.py        FastAPI app; endpoint + forwarding via httpx (async)
  analyzer.py      request → segments → tiktoken counts
  optimizers/      one file per pass; each pass: (request, trace_ctx) → request
  pipeline.py      applies enabled passes in order: prune → trim → dedup → order
  store.py         SQLite read/write (schema below)
  config.py        all thresholds, price table, master + per-pass flags
replay/verify.py
dashboard/         Next.js
demo_agent/
tests/             pytest; every optimizer pass gets unit tests with
                   fixture requests; test_passthrough.py proves
                   byte-identical behavior when optimizations disabled
DECISIONS.md       one line per design decision, appended as we go

SQLite `traces` table: id, ts, session_id (from X-AgentWarden-Session
header, default "default"), model, tokens_system, tokens_tools,
tokens_history, tokens_current, tokens_total_input, tokens_output,
tokens_saved (post-optimization delta), tools_offered (JSON),
tools_called (JSON), optimizations_applied (JSON), latency_ms.

## Hard invariants (never violate)
- With all optimizations disabled, the proxy is byte-identical
  pass-through. This is tested and stays green forever.
- Optimizations NEVER delay or break streaming; stream chunks relay
  immediately, accounting happens after.
- An optimizer pass that errors falls back to forwarding the original
  request untouched, and logs. The proxy must never be the reason an
  agent run fails.
- Upstream errors return to the client unchanged.

## Working conventions
- Small, frequent commits with descriptive messages.
- When you make a non-obvious design choice, append one line to
  DECISIONS.md.
- Propose improvements freely — but if a proposal deviates from the
  architecture or scope above, ASK before implementing.
- Python 3.11+, type hints, no heavy dependencies beyond:
  fastapi, uvicorn, httpx, tiktoken, pytest, openai (for demo/replay).

## Milestones
Day 1: pass-through proxy + tracing + /traces + /stats endpoints
Day 2: demo coding agent + tool_prune
Day 3: history_trim + context_dedup + cache_order + budget guard +
       replay verifier working end-to-end
Day 4: dashboard + README + packaging + receipts (savings table)
Day 5: demo video + submission. NO new features.
