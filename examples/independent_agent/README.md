# Independent Agent Test

This is a deliberately separate consumer agent. It does not import
AgentWarden or any source from this repository; it uses only the public
`openai` Python package and a normal tool-calling loop.

Run AgentWarden in one terminal with your desired optimizer flags, then run
this from the repository root in another terminal:

```bash
.venv/bin/python examples/independent_agent/agent.py
```

It will make the model resolve a fictional support ticket using five required
tools plus six plausible but irrelevant tools. Copy the returned `session_id`
and inspect the actual proxy receipt:

```bash
.venv/bin/agentwarden stats --session-id external-support-PASTE_ID
```

To prove the same agent runs without AgentWarden, point it directly at OpenAI:

```bash
.venv/bin/python examples/independent_agent/agent.py \
  --base-url https://api.openai.com/v1
```

The direct run has no AgentWarden receipt. The proxied run should produce the
same kind of support answer while recording traces and, once the warm-up is
past, removing irrelevant tool schemas from later requests.
