# Decisions

- Day 1: With every optimizer flag off, AgentWarden forwards the original request bytes instead of reserializing parsed JSON.
- Day 1: System and developer messages form the system segment; the final non-system message is the current turn, and earlier non-system messages are history.
- Day 2: tool_prune stays conservative after warmup by pruning only to previously called or explicitly named tools, and leaves the original tool list intact if that set would be empty.
- Day 3: history_trim only clips older tool-role content, while context_dedup skips the current turn and tool-call-bearing assistant messages to keep behavior risk low.
- Day 3: budget_guard warns from the earliest deterministic signal available for both normal and streaming requests: prior session spend plus the current request's input-token estimate.
- Day 4: the demo repository lives outside the main `tests/` path so it can stay intentionally broken while AgentWarden's own test suite remains green.
- Day 4: replay verification launches two isolated local proxy processes with different optimizer flags so "off" and "on" runs compare the same task against fresh workspaces.
2026-07-18: The dashboard discovers local runs through a read-only `/sessions` endpoint rather than requiring users to paste session IDs.
2026-07-18: Dashboard configuration changes affect only the currently running local proxy; environment variables remain the durable configuration source.
2026-07-18: The public website deploys separately to Vercel; the local dashboard is bundled inside the Python package and served by the proxy at `/dashboard`.
2026-07-19: The packaged replay demo includes pytest and explicitly names its essential coding tools so verification does not mistake a delayed necessary tool for a removable decoy.
2026-07-19: Each replay verifier run uses new temporary SQLite databases, preventing prior traces from changing either side of an A/B comparison.
2026-07-19: The lead-enrichment demo uses deterministic local fixture data and names all necessary tools in its task so it can measure decoy-schema removal without making a live data provider part of the proof.
