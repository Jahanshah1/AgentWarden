# AgentWarden

AgentWarden is a local, OpenAI-compatible proxy for tool-using agents. It
measures where each request spends input tokens, removes conservative dead
weight from long-running conversations, and keeps a per-session savings
receipt in SQLite.

> Observability tools show you the bill. AgentWarden shrinks it and proves
> nothing broke.

## What works today

- Transparent `/v1/chat/completions` proxy for OpenAI, including streaming.
- Per-request tracing: system prompt, tool schemas, conversation history, and
  current turn token counts.
- Independently enabled optimizers: unused tool pruning, old tool-output
  trimming, duplicate-history removal, and stable static-prefix ordering.
- Per-session budget warning, local SQLite traces, a demo coding agent, and a
  replay verifier that compares optimizations off versus on.

It supports applications that use the **Chat Completions** API. The proxy is
language-neutral: a Python, Node.js, or other HTTP client can use it. The
current v1 does not yet proxy OpenAI's `/v1/responses` endpoint or other model
providers.

## Quick start

Requirements: Python 3.11+ and an OpenAI API key. Your key stays in your
application process and is forwarded directly to OpenAI; AgentWarden does not
persist it.

Install directly from this repository:

```bash
python3.11 -m venv .venv
.venv/bin/pip install "git+https://github.com/Jahanshah1/AgentWarden.git"
```

Start the proxy with all current optimizers enabled:

```bash
export AGENTWARDEN_ENABLE_TOOL_PRUNE=true
export AGENTWARDEN_ENABLE_HISTORY_TRIM=true
export AGENTWARDEN_ENABLE_CONTEXT_DEDUP=true
export AGENTWARDEN_ENABLE_CACHE_ORDER=true
export AGENTWARDEN_SESSION_BUDGET_USD=0.02
.venv/bin/agentwarden serve
```

In a second terminal, check it is up:

```bash
.venv/bin/agentwarden doctor
```

The proxy listens on `http://127.0.0.1:8080`. Its OpenAI-compatible SDK base
URL is `http://127.0.0.1:8080/v1`.

## Add it to an existing agent

Keep the agent's `OPENAI_API_KEY` exactly where it already is. Run
AgentWarden beside the agent, then point the OpenAI client at the local proxy.

Python:

```python
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url="http://127.0.0.1:8080/v1",
)
```

Node.js:

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: "http://127.0.0.1:8080/v1",
});
```

For useful per-agent receipts, send a stable session header with each agent
run. This is optional; without it, traces use the `default` session.

```python
client.chat.completions.create(
    model="gpt-5.6-terra",
    messages=messages,
    extra_headers={"X-AgentWarden-Session": "support-agent-run-42"},
)
```

Then inspect the local receipt:

```bash
curl "http://127.0.0.1:8080/stats?session_id=support-agent-run-42"
curl "http://127.0.0.1:8080/traces?session_id=support-agent-run-42"
```

## Verify the project

For contributors working from a clone:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -m 'not live' -q
```

To exercise a real OpenAI API key through the proxy:

```bash
export OPENAI_API_KEY="your-key"
.venv/bin/python scripts/smoke.py
```

To run the complete coding-agent demo and then inspect its receipt:

```bash
.venv/bin/agentwarden demo
.venv/bin/agentwarden stats --session-id demo-REPLACE_ME
```

For a separate consumer-agent proof that imports only the OpenAI SDK, run the
[independent support-agent example](examples/independent_agent/README.md).

To compare the same demo task with optimizations off and on:

```bash
.venv/bin/agentwarden verify --no-judge
```

## Configuration

All flags default to `false`, preserving byte-identical pass-through.

| Variable | Meaning |
| --- | --- |
| `AGENTWARDEN_ENABLE_TOOL_PRUNE` | After three warm-up requests, sends only previously used or explicitly mentioned tools. |
| `AGENTWARDEN_ENABLE_HISTORY_TRIM` | Clips old tool-result messages while preserving recent turns. |
| `AGENTWARDEN_ENABLE_CONTEXT_DEDUP` | Replaces repeated old history content with a deterministic reference. |
| `AGENTWARDEN_ENABLE_CACHE_ORDER` | Makes the system-and-tools prefix stable to help provider prompt caching. |
| `AGENTWARDEN_SESSION_BUDGET_USD` | Adds a warning response header after the projected session cost crosses this amount. |
| `AGENTWARDEN_DB_PATH` | SQLite trace database location; defaults to `agentwarden.sqlite3`. |

## Dashboard

The local dashboard reads sessions, trace receipts, and runtime configuration
from the running proxy. Start the proxy first, then in a second terminal:

```bash
cd dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The dashboard can select
any recorded session, show before/after input context, inspect every request,
and change optimizer flags or the budget-warning threshold for the currently
running proxy. Runtime changes take effect immediately but reset when the proxy
is restarted; use environment variables for durable defaults.

## Current status

This is a working hackathon prototype, not a hosted multi-tenant service. It
is designed to run locally beside one developer's agent. Before a broad public
release, the next work is the dashboard, packaged releases on PyPI, stronger
live replay coverage, and support for the Responses API.
