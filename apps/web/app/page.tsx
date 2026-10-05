"use client";

import { FormEvent, useState } from "react";

type LanguageStat = { language: string; files: number; share: number };
type Analysis = {
  repository: {
    full_name: string;
    description: string | null;
    default_branch: string;
    total_files: number;
    source_files: number;
    ignored_files: number;
    languages: LanguageStat[];
    important_files: string[];
  };
};

type SearchResult = {
  path: string;
  language: string | null;
  score: number;
  reasons: string[];
  symbols: { name: string; kind: string; line_start: number }[];
  snippet: string;
};

type CodeSearch = {
  repository: string;
  task: string;
  retrieval_mode: string;
  indexed_files: number;
  indexed_chunks: number;
  results: SearchResult[];
};

type Patch = {
  path: string;
  rationale: string;
  unified_diff: string;
};

type Plan = {
  repository: string;
  task: string;
  patch_status: string;
  approval_required: boolean;
  plan: {
    summary: string;
    confidence: number;
    target_files: string[];
    steps: {
      order: number;
      title: string;
      description: string;
      files: string[];
      verification: string;
    }[];
    risks: string[];
    validation_commands: string[];
  };
  patches: Patch[];
};

type Validation = {
  repository: string;
  sandbox: string;
  status: string;
  passed: boolean;
  safe_to_propose_pr: boolean;
  patch: {
    status: string;
    files: string[];
    message: string;
  };
  commands: {
    command: string;
    status: string;
    exit_code: number | null;
    duration_ms: number;
    stdout: string;
    stderr: string;
  }[];
  notes: string[];
};

type Investigation = {
  repository: string;
  task: string;
  retrieval_mode: string;
  hypothesis: {
    summary: string;
    confidence: number;
    rationale: string[];
  };
  evidence: SearchResult[];
  suggested_next_actions: string[];
};

const stages = [
  "Repository connected",
  "Codebase indexed",
  "Issue investigated",
  "Patch planned",
  "Changes validated",
];

export default function Home() {
  const [repositoryUrl, setRepositoryUrl] = useState("https://github.com/laksh150806/ForgeAI");
  const [task, setTask] = useState("Find the code responsible for repository URL validation and GitHub API failures.");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [search, setSearch] = useState<CodeSearch | null>(null);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [validation, setValidation] = useState<Validation | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<"repo" | "code" | "investigate" | "plan" | "validate" | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function analyzeRepository(event: FormEvent) {
    event.preventDefault();
    setLoading("repo");
    setError("");
    setAnalysis(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/repositories/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: repositoryUrl }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Repository analysis failed.");
      setAnalysis(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Repository analysis failed.");
    } finally {
      setLoading(null);
    }
  }

  async function runInvestigation() {
    setLoading("investigate");
    setError("");
    setInvestigation(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/investigations/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: repositoryUrl, task, limit: 6 }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Investigation failed.");
      setInvestigation(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Investigation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function generatePlan() {
    setLoading("plan");
    setError("");
    setPlan(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/plans/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: repositoryUrl, task, generate_patch: true }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Planning failed.");
      setPlan(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Planning failed.");
    } finally {
      setLoading(null);
    }
  }

  async function validatePatch() {
    if (!plan || plan.patches.length === 0) {
      setError("Generate a patch before running validation.");
      return;
    }

    setLoading("validate");
    setError("");
    setValidation(null);

    try {
      const response = await fetch(`${apiUrl}/api/v1/validation/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_url: repositoryUrl,
          patches: plan.patches,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Validation failed.");
      setValidation(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Validation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function searchCode(event: FormEvent) {
    event.preventDefault();
    setLoading("code");
    setError("");
    setSearch(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/code/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: repositoryUrl, task, limit: 8 }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Code search failed.");
      setSearch(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Code search failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="eyebrow">FORGEAI / ENGINEERING INTELLIGENCE</div>
        <h1>Understand the code that matters.</h1>
        <p className="lede">
          ForgeAI maps a repository, extracts code structure, and ranks the files and
          symbols most relevant to an engineering task before an agent proposes changes.
        </p>

        <form className="repoForm" onSubmit={analyzeRepository}>
          <input value={repositoryUrl} onChange={(e) => setRepositoryUrl(e.target.value)} required />
          <button disabled={loading !== null} type="submit">
            {loading === "repo" ? "Analyzing…" : "Analyze repository"}
          </button>
        </form>

        <form className="taskForm" onSubmit={searchCode}>
          <textarea value={task} onChange={(e) => setTask(e.target.value)} required />
          <div className="taskActions">
            <button disabled={loading !== null} type="submit">
              {loading === "code" ? "Searching code…" : "Find relevant code"}
            </button>
            <button
              className="secondaryButton"
              disabled={loading !== null}
              type="button"
              onClick={runInvestigation}
            >
              {loading === "investigate" ? "Investigating…" : "Run investigation"}
            </button>
            <button
              className="secondaryButton"
              disabled={loading !== null}
              type="button"
              onClick={generatePlan}
            >
              {loading === "plan" ? "Planning…" : "Generate plan + patch"}
            </button>
          </div>
        </form>

        {error && <p className="error">{error}</p>}
      </section>

      {analysis && (
        <section className="analysis panel">
          <div className="analysisHeader">
            <div>
              <span className="label">REPOSITORY INTELLIGENCE</span>
              <h2>{analysis.repository.full_name}</h2>
              <p>{analysis.repository.description ?? "No repository description."}</p>
            </div>
            <span className="branch">{analysis.repository.default_branch}</span>
          </div>

          <div className="metrics">
            <article><span>Total files</span><strong>{analysis.repository.total_files}</strong></article>
            <article><span>Source files</span><strong>{analysis.repository.source_files}</strong></article>
            <article><span>Ignored noise</span><strong>{analysis.repository.ignored_files}</strong></article>
          </div>
        </section>
      )}

      {investigation && (
        <section className="panel investigation">
          <div className="analysisHeader">
            <div>
              <span className="label">INVESTIGATION AGENT</span>
              <h2>{investigation.hypothesis.summary}</h2>
              <p>
                Confidence {Math.round(investigation.hypothesis.confidence * 100)}% · {investigation.retrieval_mode}
              </p>
            </div>
          </div>
          <div className="investigationGrid">
            <div>
              <h3>Why ForgeAI thinks this</h3>
              <ul>
                {investigation.hypothesis.rationale.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div>
              <h3>Suggested next actions</h3>
              <ol>
                {investigation.suggested_next_actions.map((item) => <li key={item}>{item}</li>)}
              </ol>
            </div>
          </div>
        </section>
      )}

      {plan && (
        <section className="panel planPanel">
          <div className="analysisHeader">
            <div>
              <span className="label">ENGINEERING PLAN</span>
              <h2>{plan.plan.summary}</h2>
              <p>
                Confidence {Math.round(plan.plan.confidence * 100)}% · Patch status {plan.patch_status}
              </p>
            </div>
            {plan.approval_required && <span className="approvalBadge">Approval required</span>}
          </div>

          <div className="planGrid">
            <div>
              <h3>Implementation steps</h3>
              <div className="planSteps">
                {plan.plan.steps.map((step) => (
                  <article key={step.order}>
                    <span>0{step.order}</span>
                    <strong>{step.title}</strong>
                    <p>{step.description}</p>
                    <small>{step.verification}</small>
                  </article>
                ))}
              </div>
            </div>

            <div>
              <h3>Risk controls</h3>
              <ul>
                {plan.plan.risks.map((risk) => <li key={risk}>{risk}</li>)}
              </ul>
              <h3>Validation commands</h3>
              <div className="commandList">
                {plan.plan.validation_commands.map((command) => <code key={command}>{command}</code>)}
              </div>
            </div>
          </div>

          {plan.patches.length > 0 ? (
            <div className="patches">
              <h3>Proposed patch</h3>
              {plan.patches.map((patch) => (
                <article className="patchCard" key={patch.path}>
                  <div className="patchHeader">
                    <strong>{patch.path}</strong>
                    <span>Preview only</span>
                  </div>
                  <p>{patch.rationale}</p>
                  <pre>{patch.unified_diff}</pre>
                </article>
              ))}
            </div>
          ) : (
            <p className="muted">
              No patch was generated. The engineering plan is still available for review.
            </p>
          )}

          {plan.patches.length > 0 && (
            <div className="validateAction">
              <button disabled={loading !== null} type="button" onClick={validatePatch}>
                {loading === "validate" ? "Validating in sandbox…" : "Validate patch in sandbox"}
              </button>
            </div>
          )}
        </section>
      )}

      {validation && (
        <section className={`panel validationPanel ${validation.passed ? "validationPass" : "validationFail"}`}>
          <div className="analysisHeader">
            <div>
              <span className="label">SANDBOX VALIDATION</span>
              <h2>{validation.passed ? "Patch validated" : "Validation did not pass"}</h2>
              <p>
                Sandbox {validation.sandbox} · Patch {validation.patch.status} · {validation.status}
              </p>
            </div>
            <span className={`validationBadge ${validation.safe_to_propose_pr ? "safe" : "blocked"}`}>
              {validation.safe_to_propose_pr ? "PR gate open" : "PR gate blocked"}
            </span>
          </div>

          <div className="validationCommands">
            {validation.commands.map((command, index) => (
              <article key={`${command.command}-${index}`}>
                <div className="commandHeader">
                  <strong>{command.command}</strong>
                  <span>{command.status} · {command.duration_ms}ms</span>
                </div>
                {(command.stdout || command.stderr) && (
                  <pre>{[command.stdout, command.stderr].filter(Boolean).join("\n")}</pre>
                )}
              </article>
            ))}
          </div>

          <div className="validationNotes">
            <h3>Safety notes</h3>
            <ul>
              {validation.notes.map((note) => <li key={note}>{note}</li>)}
            </ul>
          </div>
        </section>
      )}

      {search && (
        <section className="panel retrieval">
          <div className="analysisHeader">
            <div>
              <span className="label">TASK-TO-CODE RETRIEVAL</span>
              <h2>Relevant engineering evidence</h2>
              <p>
                {search.indexed_files} files · {search.indexed_chunks} code chunks indexed · {search.retrieval_mode}
              </p>
            </div>
          </div>

          <div className="resultList">
            {search.results.map((result, index) => (
              <article className="resultCard" key={`${result.path}-${index}`}>
                <div className="resultTop">
                  <div>
                    <span className="rank">#{index + 1}</span>
                    <strong>{result.path}</strong>
                  </div>
                  <span className="score">{result.score.toFixed(2)}</span>
                </div>
                {result.symbols.length > 0 && (
                  <div className="symbols">
                    {result.symbols.slice(0, 6).map((symbol) => (
                      <code key={`${symbol.name}-${symbol.line_start}`}>
                        {symbol.name} · L{symbol.line_start}
                      </code>
                    ))}
                  </div>
                )}
                <p className="reason">{result.reasons.join(" · ")}</p>
                <pre>{result.snippet}</pre>
              </article>
            ))}
          </div>
        </section>
      )}

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
