# Decisions

- Day 1: With every optimizer flag off, AgentWarden forwards the original request bytes instead of reserializing parsed JSON.
- Day 1: System and developer messages form the system segment; the final non-system message is the current turn, and earlier non-system messages are history.
- Day 2: tool_prune stays conservative after warmup by pruning only to previously called or explicitly named tools, and leaves the original tool list intact if that set would be empty.
- Day 3: history_trim only clips older tool-role content, while context_dedup skips the current turn and tool-call-bearing assistant messages to keep behavior risk low.
- Day 3: budget_guard warns from the earliest deterministic signal available for both normal and streaming requests: prior session spend plus the current request's input-token estimate.
