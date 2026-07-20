import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Code2,
  Eye,
  Github,
  Layers3,
  Package,
  ShieldCheck,
  TerminalSquare,
  Wrench,
} from "lucide-react";

const repoUrl = "https://github.com/Jahanshah1/AgentWarden";
const pypiUrl = "https://pypi.org/project/agentwarden-ai/";

export default function Home() {
  return (
    <main>
      <section className="hero" id="top">
        <nav className="nav container">
          <a className="brand" href="#top" aria-label="AgentWarden home">
            <img src="/screenshots/logoward.png" alt="AgentWarden logo" />
            <span>AgentWarden</span>
          </a>
          <div className="nav-links">
            <a href="#proof">Proof</a>
            <a href="#anatomy">Token anatomy</a>
            <a href="#optimizers">Optimizers</a>
            <a href="#dashboard">Dashboard</a>
          </div>
          <a className="nav-github" href={repoUrl} target="_blank" rel="noreferrer">
            GitHub <ArrowUpRight size={16} />
          </a>
        </nav>

        <div className="hero-layout container">
          <div className="hero-copy">
            <p className="kicker hero-kicker"><ShieldCheck size={14} /> Built locally. Your API key stays with your agent.</p>
            <h1>AgentWarden reduces your agent tokens <em>drastically.</em></h1>
            <p className="hero-body">A local Python package with two simple steps to use, track, and reduce your OpenAI token usage.</p>
            <div className="hero-actions">
              <a className="button primary" href={repoUrl} target="_blank" rel="noreferrer"><Github size={18} /> Jahanshah1/AgentWarden</a>
              <a className="button ghost" href={pypiUrl} target="_blank" rel="noreferrer"><Package size={17} /> View on PyPI</a>
            </div>
          </div>

          <section className="hero-code" id="install" aria-label="AgentWarden installation steps">
            <header><span>Two steps</span><span>Python 3.11+</span></header>
            <div className="code-block">
              <p><i>01</i><code><b>$</b> pip install agentwarden-ai</code></p>
              <p><i>02</i><code><b>$</b> agentwarden dashboard</code></p>
            </div>
            <div className="code-divider" />
            <p className="code-caption">In your existing OpenAI client</p>
            <pre><code>base_url = "http://127.0.0.1:8080/v1"</code></pre>
            <p className="code-note">Same SDK. Same API key. Local proof for every session.</p>
          </section>
        </div>
      </section>

      <section className="proof-section" id="proof">
        <div className="container proof-layout">
          <div className="section-heading">
            <p className="kicker">Measured savings</p>
            <h2>A receipt, not a promise.</h2>
            <p className="section-copy">A real local lead-agent run reduced context after warm-up while preserving the completed workflow. The request-level receipt shows exactly what changed.</p>
            <div className="proof-points">
              <span><CheckCircle2 size={17} /> Same tool sequence</span>
              <span><CheckCircle2 size={17} /> Local SQLite receipt</span>
              <span><CheckCircle2 size={17} /> Per-request evidence</span>
            </div>
          </div>
          <figure className="product-shot savings-shot">
            <img src="/screenshots/tokens-saved.png" alt="AgentWarden before and after context receipt showing 8.8 percent reduction" />
            <figcaption>Controlled lead-enrichment workflow. Savings depend on repeated agent context.</figcaption>
          </figure>
        </div>
      </section>

      <section className="optimizer-section" id="optimizers">
        <div className="container optimizer-layout">
          <div className="section-heading optimizer-copy">
            <p className="kicker">Turn them on</p>
            <h2>Four conservative passes. <em>Opt in explicitly.</em></h2>
            <p className="section-copy">Every optimizer starts off. Open the dashboard settings button, enable the passes you want, then apply them to the running local proxy. The settings reset when the proxy stops, so use environment variables when you want durable defaults.</p>
            <p className="savings-callout"><strong>Longer agent loops create more opportunity.</strong> Tool Prune learns from the session after three unchanged warm-up requests. In tool-heavy workflows, 10-15+ requests can reduce input cost by roughly 16-50%, depending on repeated tools and history.</p>
          </div>
          <figure className="product-shot tools-shot">
            <img src="/screenshots/tools.png" alt="AgentWarden dashboard optimizer settings with four toggles" />
            <figcaption>Open settings in the local dashboard, enable the toggles, then apply them.</figcaption>
          </figure>
        </div>
        <div className="container optimizer-grid">
          <Optimizer title="Tool Prune" text="After three warm-up requests, removes unused tool schemas while retaining tools already called or named in the current request." />
          <Optimizer title="History Trim" text="Keeps recent turns intact and clips older tool-result messages that no longer need full detail." />
          <Optimizer title="Context Dedup" text="Replaces repeated history blocks with a deterministic reference to the original content." />
          <Optimizer title="Cache Order" text="Stabilizes the system-and-tools prefix so provider prompt caching has a better chance to apply." />
        </div>
        <p className="container optimizer-disclaimer">The 16-50% range is a workload-dependent potential, not a guarantee. Your local receipt shows the actual result for each session.</p>
      </section>

      <section className="anatomy-section" id="anatomy">
        <div className="container anatomy-layout">
          <figure className="product-shot anatomy-shot">
            <img src="/screenshots/utility-meter.png" alt="AgentWarden token anatomy showing system, tools, history, and current context" />
          </figure>
          <div className="section-heading">
            <p className="kicker">Know the waste</p>
            <h2>See where every input token went.</h2>
            <p className="section-copy">AgentWarden separates system instructions, tool schemas, conversation history, and the current turn. You can see whether tools or history are creating the cost before enabling an optimizer.</p>
            <div className="anatomy-list">
              <span><i className="system" />System prompt</span>
              <span><i className="tools" />Tool schemas</span>
              <span><i className="history" />Conversation history</span>
              <span><i className="current" />Current turn</span>
            </div>
          </div>
        </div>
      </section>

      <section className="dashboard-section" id="dashboard">
        <div className="container dashboard-intro">
          <div className="section-heading">
            <p className="kicker">Local dashboard</p>
            <h2>Inspect every agent run<br />without shipping its data elsewhere.</h2>
          </div>
          <p>Start one local command, select a session, then inspect cost, tokens avoided, tools offered, latency, and the exact optimization passes used.</p>
        </div>
        <div className="container dashboard-frame">
          <img src="/screenshots/dashboard.png" alt="AgentWarden local dashboard showing token savings and request trace evidence" />
        </div>
      </section>

      <section className="process-section" id="how">
        <div className="container process-layout">
          <div className="section-heading">
            <p className="kicker">How it works</p>
            <h2>One URL change.<br />A guarded path to OpenAI.</h2>
            <p className="section-copy">AgentWarden runs between your existing agent and the OpenAI Chat Completions API. Streaming stays intact, and your authorization header passes through from your own process.</p>
          </div>
          <div className="process-flow" aria-label="AgentWarden request flow">
            <div><span className="flow-number">1</span><Code2 size={22} /><strong>Your agent</strong><p>Same SDK and tools.</p></div>
            <i /><div><span className="flow-number">2</span><ShieldCheck size={22} /><strong>AgentWarden</strong><p>Measures, trims, and relays locally.</p></div>
            <i /><div><span className="flow-number">3</span><TerminalSquare size={22} /><strong>OpenAI</strong><p>Receives the compatible request.</p></div>
          </div>
        </div>
      </section>

      <section className="feature-band">
        <div className="container feature-layout">
          <div className="section-heading"><p className="kicker">What ships today</p><h2>A practical optimization layer for tool-using agents.</h2></div>
          <div className="feature-list">
            <Feature icon={<Eye />} title="Segmented tracing" text="See system, tools, history, and current-turn tokens separately." />
            <Feature icon={<Wrench />} title="Conservative tool pruning" text="After warm-up, remove unused schemas while retaining explicitly needed tools." />
            <Feature icon={<Layers3 />} title="Deterministic cleanup" text="Trim older tool outputs, deduplicate old history, and stabilize cacheable prefixes." />
            <Feature icon={<BarChart3 />} title="Budget and replay proof" text="Warn on projected session spend and validate important workflows." />
          </div>
        </div>
      </section>

      <section className="creator-section">
        <div className="container creator-layout">
          <img className="creator-logo" src="/screenshots/logoward.png" alt="AgentWarden logo" />
          <div><p className="kicker">Independent and open source</p><h2>Created by <em>Jahan Shah.</em></h2><p>Built for developers who want their agents to stay capable while becoming meaningfully easier to understand and afford.</p></div>
          <a className="button dark" href={repoUrl} target="_blank" rel="noreferrer"><Github size={18} /> View the project <ArrowRight size={16} /></a>
        </div>
      </section>

      <footer className="footer container"><span>AgentWarden</span><span>Open-source agent efficiency infrastructure</span><a href="#top">Back to top</a></footer>
    </main>
  );
}

function Feature({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return <article><div>{icon}</div><span><h3>{title}</h3><p>{text}</p></span></article>;
}

function Optimizer({ title, text }: { title: string; text: string }) {
  return <article><span>Opt-in pass</span><h3>{title}</h3><p>{text}</p></article>;
}
