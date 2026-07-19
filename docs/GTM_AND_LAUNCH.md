# AgentWarden Launch Playbook

This plan focuses on earning trust from developers with a usable local product, a reproducible receipt, and a clear reason to install it on one real agent.

## Positioning

**Category:** Open-source local optimization and observability middleware for tool-using OpenAI agents.

**First users:** developers who own multi-step Python or Node agents in coding, support, research, operations, or lead enrichment. Do not market first to one-shot chatbot builders, Responses API users, or buyers seeking hosted multi-tenant governance. Those are outside v1.

**Core message:**

> Observability tools show you the bill. AgentWarden shrinks it and proves nothing broke.

Companion sentence: change one OpenAI SDK base URL, inspect where agent tokens go, and remove conservative repeated context locally.

### Claims Discipline

Never lead with an unqualified "saves 40–60%" promise. Lead with a receipt from a named workload, such as: "687 input tokens avoided (13.3%) on a six-request support-agent run after warm-up." Smaller reproducible numbers earn more trust than large generic numbers.

State the limits plainly: local alpha, Chat Completions only, optimizers off by default, and important workflows should be replay-verified.

## Readiness Before Promotion

- `pip install agentwarden-ai` works in a clean Python 3.11 environment.
- `agentwarden dashboard` opens a styled local UI at `/dashboard`.
- An external OpenAI SDK example works after only the base-URL change.
- `agentwarden verify --no-judge` produces matching tool sequence and matching test outcome on a funded API account.
- The repository is public, licensed, and links to current docs.
- The Vercel site uses the exact PyPI command and links to GitHub and PyPI.

Before launch day, record one clean receipt from a support or lead-style agent, capture a 20–40 second screen recording, and ask two developers to install from an empty folder. Fix every point of confusion they encounter.

## Site And GitHub Plan

### Public Site

1. Keep the visible command exact: `pip install agentwarden-ai`.
2. Add direct PyPI, GitHub, and user-guide links.
3. Add a real dashboard screenshot or short GIF. Show token segments, tools offered, and savings, not only marketing imagery.
4. Add a compatibility block: Chat Completions works; `/v1/responses` and non-OpenAI providers do not yet.
5. Make the adoption path visible: install, start dashboard, change `base_url`.
6. Use receipts instead of broad savings promises. Explain that savings depend on repeated tools and history.
7. Keep Jahan Shah visible as creator while putting product outcome first.

### GitHub

1. Keep the three-command quick start at the README top.
2. Link the user guide and this playbook near it.
3. Add working PyPI, Python, and license badges.
4. Add `CONTRIBUTING.md` and a bug template requesting Python version, CLI version, and sanitized traces.
5. Publish concise GitHub Release notes for every PyPI version.
6. Add a roadmap that separates current scope from future ideas.

## 90-Second Demo Script

1. In a clean terminal: `pip install agentwarden-ai`.
2. Start `agentwarden dashboard`; open the local dashboard.
3. Run a tool-heavy agent with 10–15 offered tools on a six-plus-step task.
4. Show the first three requests retaining the full tool list.
5. Show later requests offering fewer tools and nonzero `tokens_saved`.
6. Show the final business output and request-level trace table together.
7. Show the verifier result or matched workflow outcome.
8. Close with the one-line adoption change: local `base_url`.

For a lead agent, use deterministic local CRM/prospect fixtures. The packaged `agentwarden lead-demo` now provides this workflow: seven required enrichment tools, eight decoys, saved-lead/outreach output, and an outcome check. The goal is to prove context reduction; live scraping noise makes the proof weaker.

## Hackathon Submission

Treat the specific event rules as source of truth. Verify required tools, deadline timezone, video duration, and "try it" requirements before submitting.

### Asset Checklist

- **Name:** AgentWarden
- **Tagline:** A local proxy that cuts AI-agent context waste and proves workflows held.
- **Pitch:** Change one OpenAI SDK base URL to trace, reduce, and verify repeated agent context locally.
- **Try it:** PyPI project, public GitHub repository, and deployed Vercel site.
- **Video:** 60–90 seconds using the demo script above.
- **Images:** homepage, dashboard, before/after receipt, architecture.
- **Built with:** Python, FastAPI, SQLite, OpenAI SDK/API, tiktoken, Next.js, and Vercel for the public site.

### Description Outline

1. Agent loops resend tools and history, compounding input cost.
2. AgentWarden is a local compatible proxy with deterministic cleanup passes.
3. It provides per-segment tracing, receipts, and A/B replay verification.
4. Adoption is install, start locally, and change `base_url`.
5. Limits are local, single-user, and Chat Completions only.

Devpost guidance highlights repository links, images, a public demo video, and a final proofreading pass. Review the official [submission steps](https://help.devpost.com/article/126-know-your-submission-steps) and [project-entry guide](https://help.devpost.com/article/122-how-to-enter-a-submission) against the event rules. Submit early enough to correct eligibility issues.

## Product Hunt

Launch only when visitors can install, read docs, and see a real walkthrough. Product Hunt prioritizes live, usable products; an email-only waitlist is a poor fit. See the official [featuring guidelines](https://help.producthunt.com/en/articles/9883485-product-hunt-featuring-guidelines).

### Launch Page

- **Name:** AgentWarden
- **Tagline:** Cut repeated AI-agent context locally, with a receipt for every run.
- **Gallery 1:** an actual dashboard receipt showing tool reduction and savings.
- **Gallery 2:** the three-line Python integration.
- **Gallery 3:** Agent → local AgentWarden → OpenAI architecture, with API key remaining in the agent.
- **Maker comment:** intended user, local-first privacy, measured receipt, limits, and requested integrations.

### Launch-Day Rules

1. Be present and answer questions with technical specifics.
2. Ask which agent framework needs the next example.
3. Do not ask for upvotes or use engagement groups; ask users to try install.
4. Turn questions and friction into GitHub issues or launch notes.
5. Ship only tested fixes and never make unverified savings claims.

## Distribution And Feedback

For the first 30 users, prefer hands-on developers over broad impressions.

- Offer short install-and-receipt sessions to people building tool-using agents.
- Publish a technical build note with one external-agent receipt and its verification conditions.
- Share a short recording on X, LinkedIn, and relevant communities, following each community's self-promotion rules.
- Submit a `Show HN` only with source, docs, product, and a real receipt.
- Publish framework-specific examples before posting to those communities.

Ask every early user: framework, typical steps/tools per run, whether the UI exposed waste, whether optimization changed behavior, and what proof would make them comfortable enabling it.

Track manually at first: PyPI installs, first-proxy success, first receipt, valid verifier passes, median input tokens avoided, and framework requests. The north-star metric is not downloads. It is agent runs where a developer can point to a receipt, confirm behavior held, and keep AgentWarden enabled.

## Two-Week Execution Order

### Days 1–2

- Fix every issue found by two clean external-user installations.
- Build a lead-enrichment example with deterministic data and an outcome check.
- Record the demo and capture one real receipt.

### Days 3–4

- Deploy `site/` to Vercel.
- Update README, screenshots, PyPI description, and docs.
- Prepare the hackathon submission and have someone proofread it.

### Days 5–7

- Submit before the event deadline.
- Publish the demo video and technical build note.
- Begin targeted developer outreach and record installation friction.

### Week 2

- Ship high-frequency integration and documentation fixes.
- Launch on Product Hunt after the first-user path is clean.
- Publish a follow-up with a measured receipt and user-driven changes.
