# Decisions

- Day 1: With every optimizer flag off, AgentWarden forwards the original request bytes instead of reserializing parsed JSON.
- Day 1: System and developer messages form the system segment; the final non-system message is the current turn, and earlier non-system messages are history.
- Day 2: tool_prune stays conservative after warmup by pruning only to previously called or explicitly named tools, and leaves the original tool list intact if that set would be empty.
