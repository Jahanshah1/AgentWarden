import { ArrowDownRight, ArrowRight, BarChart3, CheckCircle2, CircleDollarSign, Code2, Eye, Github, Layers3, ShieldCheck, TerminalSquare, Wrench } from "lucide-react";

const repoUrl = "https://github.com/Jahanshah1/AgentWarden";

export default function Home() {
  return <main>
    <section className="hero" id="top">
      <nav className="nav container">
        <a className="brand" href="#top" aria-label="AgentWarden home"><span>AW</span>AgentWarden</a>
        <div className="nav-links"><a href="#how">How it works</a><a href="#proof">Proof</a><a href="#install">Install</a></div>
        <a className="nav-github" href={repoUrl} target="_blank" rel="noreferrer">GitHub <ArrowRight size={16} /></a>
      </nav>

      <div className="hero-copy container">
        <p className="kicker">Open-source AI agent infrastructure</p>
        <h1>AgentWarden<br /><em>makes every request count.</em></h1>
        <p className="hero-body">A local, drop-in OpenAI proxy that removes redundant agent context, shows precisely where tokens go, and gives you an evidence trail that the workflow still held.</p>
        <div className="hero-actions"><a className="button primary" href="#install">Start locally <ArrowRight size={18} /></a><a className="button ghost" href="#proof">See the proof <ArrowDownRight size={18} /></a></div>
      </div>
      <div className="hero-bottom container"><span>Built locally. Your API key stays with your agent.</span><span>Created by Jahan Shah</span></div>
    </section>

    <section className="statement-band"><div className="container statement-grid"><p>AI agents repeat themselves. Every loop often resends the full prompt, all tool schemas, and past tool outputs.</p><strong>AgentWarden removes the dead weight in transit.</strong></div></section>

    <section className="section container" id="how">
      <div className="section-heading"><p className="kicker">The problem</p><h2>Great agents become expensive<br />for a very ordinary reason.</h2></div>
      <div className="waste-grid">
        <article><span>01</span><h3>Tools grow stale</h3><p>Agents frequently send every tool schema on every turn, including tools they will never call.</p><Wrench size={21} /></article>
        <article><span>02</span><h3>History keeps growing</h3><p>Old tool results and duplicate content remain in the conversation long after they stopped helping.</p><Layers3 size={21} /></article>
        <article><span>03</span><h3>Costs compound</h3><p>Each next step can resend the accumulated context, creating an input-cost curve that rises with the loop.</p><CircleDollarSign size={21} /></article>
      </div>
    </section>

    <section className="process-section">
      <div className="container process-layout">
        <div className="section-heading"><p className="kicker">The answer</p><h2>One URL change.<br />A guarded path to OpenAI.</h2><p className="section-copy">AgentWarden sits between your existing agent and the OpenAI Chat Completions API. It forwards your request, preserves streaming, and records a local receipt for every run.</p></div>
        <div className="process-flow" aria-label="AgentWarden request flow">
          <div><span className="flow-number">1</span><Code2 size={22}/><strong>Your agent</strong><p>Same SDK. Same tools. Same API key.</p></div>
          <i /><div><span className="flow-number">2</span><ShieldCheck size={22}/><strong>AgentWarden</strong><p>Measures, trims, and relays locally.</p></div>
          <i /><div><span className="flow-number">3</span><TerminalSquare size={22}/><strong>OpenAI</strong><p>Receives the smaller compatible request.</p></div>
        </div>
      </div>
    </section>

    <section className="section container" id="proof">
      <div className="proof-header"><div className="section-heading"><p className="kicker">A receipt, not a promise</p><h2>Every savings claim comes<br />with the request-level evidence.</h2></div><p>Inspect the session that produced the number: input segments, tools offered, tools called, optimizer changes, latency, and estimated cost.</p></div>
      <div className="receipt" aria-label="Example AgentWarden savings receipt">
        <header><span className="receipt-mark">AW</span><div><small>Session receipt</small><strong>external-support-6bafe33b</strong></div><span className="verified"><CheckCircle2 size={16}/> Behavior held</span></header>
        <div className="receipt-stats"><div><small>Input avoided</small><strong>687</strong><span>tokens</span></div><div><small>Context reduction</small><strong>13.3%</strong><span>after warm-up</span></div><div><small>Tools offered</small><strong>11 → 5</strong><span>unused schemas removed</span></div><div><small>Requests traced</small><strong>6</strong><span>same tool sequence</span></div></div>
        <div className="receipt-track"><span className="before"/><span className="after"/></div>
        <div className="receipt-legend"><span><i className="before"/>Without AgentWarden · 5,161 input tokens</span><span><i className="after"/>With AgentWarden · 4,474 input tokens</span></div>
      </div>
    </section>

    <section className="feature-band"><div className="container feature-layout"><div><p className="kicker">What ships today</p><h2>A practical optimization layer<br />for tool-using agents.</h2></div><div className="feature-list"><Feature icon={<Eye />} title="Segmented tracing" text="See system, tools, history, and current-turn tokens separately."/><Feature icon={<Wrench />} title="Conservative tool pruning" text="After a warm-up, remove irrelevant tool schemas while keeping explicitly allowed tools."/><Feature icon={<BarChart3 />} title="Deterministic context cleanup" text="Trim older tool outputs, deduplicate old history, and stabilize cacheable prefixes."/><Feature icon={<ShieldCheck />} title="Budget guard and replay proof" text="Warn on session spend and compare optimized versus baseline runs."/></div></div></section>

    <section className="install-section" id="install"><div className="container install-layout"><div><p className="kicker">Get started</p><h2>Install once.<br />Keep your agent.</h2><p>AgentWarden is not a framework replacement. It is a local layer around the agent you already have.</p></div><div className="install-code"><header><span>Terminal</span><span>Python 3.11+</span></header><pre><code><span>$</span> pip install agentwarden-ai{`\n`}<span>$</span> agentwarden dashboard{`\n`}{`\n`}# In your existing agent{`\n`}base_url = "http://127.0.0.1:8080/v1"</code></pre><a href={repoUrl} target="_blank" rel="noreferrer">Read the installation guide <ArrowRight size={16}/></a></div></div></section>

    <section className="creator-section"><div className="container creator-layout"><div className="creator-mark">JS</div><div><p className="kicker">Independent and open source</p><h2>Created by <em>Jahan Shah.</em></h2><p>Built for developers who want their agents to stay capable while becoming meaningfully easier to understand and afford.</p></div><a className="button dark" href={repoUrl} target="_blank" rel="noreferrer"><Github size={18}/> View the project</a></div></section>

    <footer className="footer container"><span>AgentWarden</span><span>Open-source agent efficiency infrastructure</span><a href="#top">Back to top ↑</a></footer>
  </main>;
}

function Feature({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return <article><div>{icon}</div><span><h3>{title}</h3><p>{text}</p></span></article>;
}
