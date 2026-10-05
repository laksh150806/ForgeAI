const stages = [
  "Repository connected",
  "Codebase indexed",
  "Issue investigated",
  "Patch planned",
  "Changes validated",
];

export default function Home() {
  return (
    <main className="shell">
      <section className="hero">
        <div className="eyebrow">FORGEAI / ENGINEERING INTELLIGENCE</div>
        <h1>From issue report to validated engineering change.</h1>
        <p className="lede">
          ForgeAI is an autonomous software-engineering platform that understands
          repositories, investigates failures, proposes fixes, and validates them.
        </p>
        <div className="actions">
          <button>Connect repository</button>
          <a href="#pipeline">View pipeline</a>
        </div>
      </section>

      <section id="pipeline" className="panel">
        <div>
          <span className="label">MVP WORKFLOW</span>
          <h2>Engineering task pipeline</h2>
        </div>
        <div className="stages">
          {stages.map((stage, index) => (
            <div className="stage" key={stage}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{stage}</strong>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
