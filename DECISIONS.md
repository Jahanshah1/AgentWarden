# Decisions

- Day 1: With every optimizer flag off, AgentWarden forwards the original request bytes instead of reserializing parsed JSON.
- Day 1: System and developer messages form the system segment; the final non-system message is the current turn, and earlier non-system messages are history.
