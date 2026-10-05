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
  indexed_files: number;
  indexed_chunks: number;
  results: SearchResult[];
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
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<"repo" | "code" | null>(null);

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
          <button disabled={loading !== null} type="submit">
            {loading === "code" ? "Searching code…" : "Find relevant code"}
          </button>
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

      {search && (
        <section className="panel retrieval">
          <div className="analysisHeader">
            <div>
              <span className="label">TASK-TO-CODE RETRIEVAL</span>
              <h2>Relevant engineering evidence</h2>
              <p>{search.indexed_files} files · {search.indexed_chunks} code chunks indexed</p>
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
