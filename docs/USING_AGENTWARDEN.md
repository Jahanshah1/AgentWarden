# Using AgentWarden

AgentWarden is a local OpenAI-compatible proxy for multi-step, tool-using
agents. It traces request context, optionally removes conservative repeated
context, and stores a local SQLite receipt. It runs beside the agent, not as a
hosted service.

## Install

Requirements: Python 3.11+, an OpenAI API key, and an agent using OpenAI Chat
Completions (`/v1/chat/completions`).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install agentwarden-ai
```

Keep the key in the shell or a secret manager, never in source or Git:

```bash
export OPENAI_API_KEY="your-key"
```

## Start The Proxy And Dashboard

```bash
agentwarden dashboard
```

Open `http://127.0.0.1:8080/dashboard`. This command starts the local proxy
and serves the bundled UI; users do not need Node.js or the dashboard source
folder. A `404` for `http://127.0.0.1:8080/` is expected because the UI route
is `/dashboard`.

Use another port when necessary:

```bash
agentwarden dashboard --host 127.0.0.1 --port 8090
```

`agentwarden serve` starts the same local proxy without the dashboard-oriented
instruction.

## Connect An Existing Agent

Start AgentWarden beside the agent, then change the OpenAI client's base URL
once. The API key remains with the agent and is forwarded to OpenAI.

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url="http://127.0.0.1:8080/v1",
    default_headers={"X-AgentWarden-Session": "lead-run-2026-07-19"},
)
```

For Node.js:

```javascript
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: "http://127.0.0.1:8080/v1",
  defaultHeaders: { "X-AgentWarden-Session": "lead-run-2026-07-19" },
});
```

## Sessions And Storage

`X-AgentWarden-Session` groups one agent run. Reuse one ID throughout a run;
choose a new ID for a new run or A/B test. Without it, requests use `default`.
Restarting the proxy does not create a session automatically.

Traces persist in `agentwarden.sqlite3` in the directory where the proxy was
started. Choose a durable path when needed:

```bash
export AGENTWARDEN_DB_PATH="$HOME/.agentwarden/traces.sqlite3"
agentwarden dashboard
```

## Commands

| Command | What it does |
| --- | --- |
| `agentwarden dashboard` | Starts the proxy and serves the dashboard at `/dashboard`. |
| `agentwarden serve` | Starts the local proxy. |
| `agentwarden doctor` | Checks a running proxy and prints the SDK base URL. |
| `agentwarden stats --session-id NAME` | Prints totals, segments, savings, and estimated cost. |
| `agentwarden demo` | Runs the packaged coding demo through a running proxy. It makes real OpenAI calls. |
| `agentwarden lead-demo` | Runs the packaged deterministic lead-enrichment demo through a running proxy. It makes real OpenAI calls. |
| `agentwarden verify` | Runs that coding task with optimizations off and on. It makes real OpenAI calls. |
| `agentwarden verify --no-judge` | Runs the same A/B test but skips only the extra answer-similarity judge call. |

Dashboard setting changes apply to the running proxy only. Set environment
variables before startup for durable defaults.

## Optimizers

All optimizers are **off by default**. With every flag off, AgentWarden is
byte-identical pass-through.

| Optimizer | When it helps | Important behavior |
| --- | --- | --- |
| Tool prune | Many offered tools but only a few used in a multi-step run. | Leaves the first three requests unchanged, then keeps previously used or explicitly named tools. |
| History trim | Long runs with older, large tool outputs. | Keeps recent turns and clips older tool-role content only. |
| Context dedup | Repeated content in old history. | Replaces repeated old blocks with a deterministic reference. |
| Cache order | Repeated static system/tool prefixes. | Stabilizes ordering for provider prompt caching; it may not reduce local token counts. |

Enable durable defaults before startup:

```bash
export AGENTWARDEN_ENABLE_TOOL_PRUNE=true
export AGENTWARDEN_ENABLE_HISTORY_TRIM=true
export AGENTWARDEN_ENABLE_CONTEXT_DEDUP=true
export AGENTWARDEN_ENABLE_CACHE_ORDER=true
export AGENTWARDEN_SESSION_BUDGET_USD=0.02
agentwarden dashboard
```

The budget setting adds `X-AgentWarden-Budget-Warning` when projected session
cost crosses the threshold. It warns; it does not stop an agent.

## Prove Savings Honestly

A short, tool-free request should show zero savings. That is correct: there is
nothing repeated to remove.

For the packaged A/B verifier:

```bash
export OPENAI_API_KEY="your-key"
agentwarden verify --no-judge
```

It launches isolated temporary proxies and compares the coding task with
optimizations off and on. Count the result as a valid proof only when:

- `tool_call_sequence_match` is `true`;
- both runs report `tests_passed: true`; and
- the optimized run shows lower input context or nonzero `tokens_saved`.

If tool sequences or outcomes differ, treat it as a failed verification, not a
savings claim.

For your own agent, run the same controlled task first with optimizers off and
session `lead-baseline`, then with optimizers on and session `lead-optimized`:

```bash
agentwarden stats --session-id lead-baseline
agentwarden stats --session-id lead-optimized
```

Compare input tokens, cost estimate, tool calls, and the business result. For
a lead agent, compare saved leads, scores, and outreach drafts, not only text.

The packaged lead agent gives a ready-made controlled workflow:

```bash
agentwarden lead-demo --session-id lead-baseline
```

It offers 15 tools: seven required enrichment tools and eight decoys. Its task
explicitly names the required tools, so tool pruning can remove only decoys
after warm-up. Run it once with optimizers off and once with them on using a
new session ID, then compare the dashboard receipts.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Requires-Python >=3.11` | Create the environment with `python3.11 -m venv .venv`. |
| `agentwarden: command not found` | Activate with `source .venv/bin/activate`, or run `.venv/bin/agentwarden`. |
| `OPENAI_API_KEY is required` | Export the variable in the terminal running the command. |
| Dashboard is raw text or `/_next` assets return 404 | Upgrade with `python -m pip install --upgrade agentwarden-ai`, then restart. |
| Stats show zero savings | Expected for short, tool-free runs or when optimizers are off. |
| `429 insufficient_quota` | The proxy forwarded the request; add API billing or use an account with quota. |

## Current Limits

- OpenAI Chat Completions only; `/v1/responses` is not proxied yet.
- Local, single-user operation; no hosted control plane or multi-tenancy.
- No model routing, response caching, other providers, or LLM history
  summarization.
- Optimizers are opt-in. Verify important workflows before relying on a
  savings claim.
