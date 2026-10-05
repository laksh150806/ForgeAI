"use client";

import { FormEvent, useState } from "react";

type LanguageStat = {
  language: string;
  files: number;
  share: number;
};

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

const stages = [
  "Repository connected",
  "Codebase indexed",
  "Issue investigated",
  "Patch planned",
  "Changes validated",
];

export default function Home() {
  const [repositoryUrl, setRepositoryUrl] = useState(
    "https://github.com/laksh150806/ForgeAI",
  );
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function analyzeRepository(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setAnalysis(null);

    try {
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/v1/repositories/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: repositoryUrl }),
      });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail ?? "Repository analysis failed.");
      }

      setAnalysis(payload);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Repository analysis failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="eyebrow">FORGEAI / ENGINEERING INTELLIGENCE</div>
        <h1>Understand a codebase before changing it.</h1>
        <p className="lede">
          ForgeAI inventories a repository, identifies the engineering surface,
          filters generated noise, and prepares evidence for autonomous investigation.
        </p>

        <form className="repoForm" onSubmit={analyzeRepository}>
          <input
            aria-label="GitHub repository URL"
            value={repositoryUrl}
            onChange={(event) => setRepositoryUrl(event.target.value)}
            placeholder="https://github.com/owner/repository"
            required
          />
          <button disabled={loading} type="submit">
            {loading ? "Analyzing…" : "Analyze repository"}
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
            <article>
              <span>Total files</span>
              <strong>{analysis.repository.total_files}</strong>
            </article>
            <article>
              <span>Source files</span>
              <strong>{analysis.repository.source_files}</strong>
            </article>
            <article>
              <span>Ignored noise</span>
              <strong>{analysis.repository.ignored_files}</strong>
            </article>
          </div>

          <div className="analysisGrid">
            <div>
              <h3>Languages</h3>
              <div className="languageList">
                {analysis.repository.languages.slice(0, 8).map((item) => (
                  <div className="language" key={item.language}>
                    <span>{item.language}</span>
                    <strong>{Math.round(item.share * 100)}%</strong>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3>Important files</h3>
              <div className="fileList">
                {analysis.repository.important_files.length ? (
                  analysis.repository.important_files.map((file) => (
                    <code key={file}>{file}</code>
                  ))
                ) : (
                  <span className="muted">No standard project files detected.</span>
                )}
              </div>
            </div>
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
