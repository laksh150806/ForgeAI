"use client";

import { FormEvent, useEffect, useState } from "react";

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

type BenchmarkResult = {
  metrics: {
    cases: number;
    top1_accuracy: number;
    topk_recall: number;
    mean_reciprocal_rank: number;
    symbol_accuracy: number | null;
    average_latency_ms: number;
    patch_generation_rate: number | null;
    validation_pass_rate: number | null;
    pr_gate_accuracy: number | null;
  };
  results: {
    id: string;
    repository: string;
    retrieval_mode: string;
    latency_ms: number;
    ranked_files: string[];
    top1_hit: boolean;
    topk_recall: number;
    reciprocal_rank: number;
    symbol_hit: boolean | null;
  }[];
};

type PullRequestResult = {
  repository: string;
  branch: string | null;
  pull_request_url: string | null;
  pull_request_number: number | null;
  status: string;
  committed_files: string[];
  message: string;
};

type WorkflowRun = {
  run_id: string;
  repository: string;
  task: string;
  status: string;
  stages: {
    name: string;
    status: string;
    duration_ms: number;
    details: Record<string, string | number | boolean | null>;
    error: string | null;
  }[];
  metrics: {
    total_duration_ms: number;
    stages_completed: number;
    stages_failed: number;
    retrieval_mode: string | null;
    evidence_count: number;
    patch_count: number;
    validation_commands: number;
    pr_gate_open: boolean;
  };
};

type RecentRun = {
  run_id: string;
  created_at: string;
  repository: string;
  task: string;
  status: string;
  total_duration_ms: number;
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

type SuspectCommit = {
  sha: string;
  short_sha: string;
  subject: string;
  authored_at: string;
  changed_files: string[];
  score: number;
  confidence: number;
  matching_terms: string[];
  reasons: string[];
};

type ImpactNode = {
  id: string;
  path: string;
  symbol: string;
  kind: string;
  line_start: number;
  line_end: number | null;
  entrypoint: boolean;
};

type ImpactAnalysis = {
  repository: string;
  commit_sha: string;
  graph_mode: string;
  graph_nodes: number;
  graph_edges: number;
  changed_symbols: ImpactNode[];
  runtime_matches: ImpactNode[];
  callers: ImpactNode[];
  downstream: ImpactNode[];
  affected_entrypoints: ImpactNode[];
  evidence_paths: string[][];
  blast_radius_score: number;
  confidence: number;
  explanation: string[];
};

type IncidentCorrelation = {
  repository: string;
  incident: string;
  head_sha: string;
  correlation_mode: string;
  suspected_commit: SuspectCommit | null;
  candidates: SuspectCommit[];
  investigation: Investigation;
  impact: ImpactAnalysis | null;
};

type TelemetryTimeline = {
  repository: string;
  service: string | null;
  window_start: string;
  window_end: string;
  first_failure_at: string | null;
  nearest_deploy: {
    event_id: string;
    observed_at: string;
    source: string;
    event_type: string;
    severity: string;
    service: string | null;
    message: string;
    deploy_sha: string | null;
    metadata: Record<string, unknown>;
  } | null;
  events: {
    event_id: string;
    observed_at: string;
    source: string;
    event_type: string;
    severity: string;
    service: string | null;
    message: string;
    deploy_sha: string | null;
    metadata: Record<string, unknown>;
  }[];
  correlation: IncidentCorrelation | null;
};

type RenderAdapterStatus = {
  configured: boolean;
  service_id: string | null;
  workspace_id: string | null;
  api_key_configured: boolean;
};

type RenderSyncResult = {
  service_id: string;
  workspace_id: string;
  deploy_events: number;
  log_events: number;
  accepted_events: number;
  storage: string;
  timeline: TelemetryTimeline | null;
};

type VercelAdapterStatus = {
  configured: boolean;
  project_id: string | null;
  team_id: string | null;
  token_configured: boolean;
  runtime_logs_mode: string;
};

type VercelSyncResult = {
  project_id: string;
  team_id: string | null;
  deployment_events: number;
  build_events: number;
  accepted_events: number;
  storage: string;
  runtime_logs_mode: string;
  timeline: TelemetryTimeline | null;
};

type SentryAdapterStatus = {
  configured: boolean;
  organization: string | null;
  project: string | null;
  environment: string | null;
  token_configured: boolean;
  ingestion_mode: string;
};

type SentrySyncResult = {
  organization: string;
  project: string;
  environment: string | null;
  error_events: number;
  accepted_events: number;
  storage: string;
  ingestion_mode: string;
  timeline: TelemetryTimeline | null;
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
  const [incident, setIncident] = useState("Production requests started returning 500 after the latest deploy.");
  const [runtimeEvidence, setRuntimeEvidence] = useState("");
  const [deploySha, setDeploySha] = useState("");
  const [incidentResult, setIncidentResult] = useState<IncidentCorrelation | null>(null);
  const [impactResult, setImpactResult] = useState<ImpactAnalysis | null>(null);
  const [telemetryService, setTelemetryService] = useState("forgeai-api");
  const [telemetryTimeline, setTelemetryTimeline] = useState<TelemetryTimeline | null>(null);
  const [renderStatus, setRenderStatus] = useState<RenderAdapterStatus | null>(null);
  const [renderSync, setRenderSync] = useState<RenderSyncResult | null>(null);
  const [vercelStatus, setVercelStatus] = useState<VercelAdapterStatus | null>(null);
  const [vercelSync, setVercelSync] = useState<VercelSyncResult | null>(null);
  const [sentryStatus, setSentryStatus] = useState<SentryAdapterStatus | null>(null);
  const [sentrySync, setSentrySync] = useState<SentrySyncResult | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [validation, setValidation] = useState<Validation | null>(null);
  const [workflowRun, setWorkflowRun] = useState<WorkflowRun | null>(null);
  const [prResult, setPrResult] = useState<PullRequestResult | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [prApproved, setPrApproved] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<"repo" | "code" | "investigate" | "incident" | "impact" | "telemetry" | "render" | "vercel" | "sentry" | "plan" | "validate" | "workflow" | "pr" | "benchmark" | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function loadRecentRuns() {
    try {
      const response = await fetch(`${apiUrl}/api/v1/runs/recent?limit=8`);
      if (!response.ok) return;
      setRecentRuns(await response.json());
    } catch {
      // Observability history is supplemental; do not break the core UI if it is unavailable.
    }
  }

  async function loadTrace(runId: string) {
    setError("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/runs/${runId}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Trace could not be loaded.");
      setWorkflowRun(payload);
      await loadRecentRuns();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Trace could not be loaded.");
    }
  }

  useEffect(() => {
    loadRecentRuns();
    fetch(`${apiUrl}/api/v1/integrations/render/status`)
      .then((response) => response.ok ? response.json() : null)
      .then((payload) => payload && setRenderStatus(payload))
      .catch(() => {});
    fetch(`${apiUrl}/api/v1/integrations/vercel/status`)
      .then((response) => response.ok ? response.json() : null)
      .then((payload) => payload && setVercelStatus(payload))
      .catch(() => {});
    fetch(`${apiUrl}/api/v1/integrations/sentry/status`)
      .then((response) => response.ok ? response.json() : null)
      .then((payload) => payload && setSentryStatus(payload))
      .catch(() => {});
  }, []);

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

  async function correlateIncident() {
    setLoading("incident");
    setError("");
    setIncidentResult(null);

    try {
      const response = await fetch(`${apiUrl}/api/v1/incidents/correlate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_url: repositoryUrl,
          incident,
          evidence: {
            error_message: runtimeEvidence || null,
            deploy_sha: deploySha || null,
          },
          lookback_commits: 10,
          code_limit: 6,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Incident correlation failed.");
      setIncidentResult(payload);
      if (payload.impact) setImpactResult(payload.impact);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Incident correlation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function analyzeBlastRadius() {
    setLoading("impact");
    setError("");
    setImpactResult(null);

    try {
      const response = await fetch(`${apiUrl}/api/v1/impact/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_url: repositoryUrl,
          commit_sha: incidentResult?.suspected_commit?.sha || deploySha || null,
          runtime_text: [incident, runtimeEvidence].filter(Boolean).join("\n"),
          lookback_commits: 20,
          max_depth: 3,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Blast-radius analysis failed.");
      setImpactResult(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Blast-radius analysis failed.");
    } finally {
      setLoading(null);
    }
  }

  async function ingestAndReconstructDemoTelemetry() {
    setLoading("telemetry");
    setError("");
    setTelemetryTimeline(null);

    try {
      const now = Date.now();
      const events = [
        {
          observed_at: new Date(now - 5 * 60_000).toISOString(),
          source: "demo",
          event_type: "deploy",
          severity: "info",
          service: telemetryService,
          message: "Deployment completed",
          deploy_sha: deploySha || null,
          metadata: { environment: "production" },
        },
        {
          observed_at: new Date(now - 2 * 60_000).toISOString(),
          source: "demo",
          event_type: "log",
          severity: "warning",
          service: telemetryService,
          message: runtimeEvidence || "Latency and error rate increased after deployment.",
          deploy_sha: null,
          metadata: {},
        },
        {
          observed_at: new Date(now - 60_000).toISOString(),
          source: "demo",
          event_type: "error",
          severity: "error",
          service: telemetryService,
          message: runtimeEvidence || "Production requests started returning 500.",
          deploy_sha: null,
          metadata: {},
        },
      ];

      const ingestResponse = await fetch(`${apiUrl}/api/v1/telemetry/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events }),
      });
      const ingestPayload = await ingestResponse.json();
      if (!ingestResponse.ok) {
        throw new Error(ingestPayload.detail ?? "Telemetry ingestion failed.");
      }

      const timelineResponse = await fetch(`${apiUrl}/api/v1/telemetry/timeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_url: repositoryUrl,
          service: telemetryService,
          lookback_minutes: 30,
          max_events: 100,
          lookback_commits: 20,
          code_limit: 6,
        }),
      });
      const timelinePayload = await timelineResponse.json();
      if (!timelineResponse.ok) {
        throw new Error(timelinePayload.detail ?? "Timeline reconstruction failed.");
      }
      setTelemetryTimeline(timelinePayload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Telemetry timeline failed.");
    } finally {
      setLoading(null);
    }
  }

  async function syncRenderTelemetry() {
    setLoading("render");
    setError("");
    setRenderSync(null);

    try {
      const response = await fetch(`${apiUrl}/api/v1/integrations/render/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_url: repositoryUrl,
          lookback_minutes: 60,
          log_limit: 100,
          deploy_limit: 20,
          reconstruct_timeline: true,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Render telemetry sync failed.");
      setRenderSync(payload);
      if (payload.timeline) setTelemetryTimeline(payload.timeline);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Render telemetry sync failed.");
    } finally {
      setLoading(null);
    }
  }

  async function syncVercelTelemetry() {
    setLoading("vercel");
    setError("");
    setVercelSync(null);

    try {
      const response = await fetch(`${apiUrl}/api/v1/integrations/vercel/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_url: repositoryUrl,
          lookback_minutes: 120,
          deploy_limit: 10,
          event_limit_per_deploy: 100,
          reconstruct_timeline: true,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Vercel telemetry sync failed.");
      setVercelSync(payload);
      if (payload.timeline) setTelemetryTimeline(payload.timeline);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Vercel telemetry sync failed.");
    } finally {
      setLoading(null);
    }
  }

  async function syncSentryTelemetry() {
    setLoading("sentry");
    setError("");
    setSentrySync(null);

    try {
      const response = await fetch(`${apiUrl}/api/v1/integrations/sentry/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_url: repositoryUrl,
          lookback_minutes: 120,
          event_limit: 20,
          reconstruct_timeline: true,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Sentry telemetry sync failed.");
      setSentrySync(payload);
      if (payload.timeline) setTelemetryTimeline(payload.timeline);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sentry telemetry sync failed.");
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

  async function runFullWorkflow() {
    setLoading("workflow");
    setError("");
    setWorkflowRun(null);

    try {
      const response = await fetch(`${apiUrl}/api/v1/runs/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_url: repositoryUrl,
          task,
          generate_patch: true,
          validate_patch: true,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Workflow run failed.");
      setWorkflowRun(payload);
      await loadRecentRuns();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Workflow run failed.");
    } finally {
      setLoading(null);
    }
  }

  async function createPullRequest() {
    if (!plan || plan.patches.length === 0) {
      setError("Generate a patch before creating a pull request.");
      return;
    }
    if (!validation?.safe_to_propose_pr) {
      setError("Run sandbox validation successfully before creating a pull request.");
      return;
    }
    if (!prApproved) {
      setError("Explicit approval is required before ForgeAI writes to GitHub.");
      return;
    }

    setLoading("pr");
    setError("");
    setPrResult(null);

    try {
      const response = await fetch(`${apiUrl}/api/v1/pull-requests/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_url: repositoryUrl,
          task,
          patches: plan.patches,
          approved: true,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Pull request creation failed.");
      setPrResult(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Pull request creation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function runBenchmark() {
    setLoading("benchmark");
    setError("");
    setBenchmark(null);

    const cases = [
      {
        id: "github-url-validation",
        repository_url: "https://github.com/laksh150806/ForgeAI",
        task: "Find the implementation responsible for validating GitHub repository URLs.",
        expected_files: ["apps/api/app/services/github_client.py"],
        expected_symbols: ["parse_github_repository_url"],
      },
      {
        id: "sandbox-patch-validation",
        repository_url: "https://github.com/laksh150806/ForgeAI",
        task: "Find the code that applies proposed patches and runs isolated validation.",
        expected_files: ["apps/api/app/services/sandbox_validation.py"],
        expected_symbols: ["validate_patches"],
      },
      {
        id: "pr-approval-gate",
        repository_url: "https://github.com/laksh150806/ForgeAI",
        task: "Find the code that requires approval and fresh validation before opening a GitHub pull request.",
        expected_files: ["apps/api/app/services/github_pr.py"],
        expected_symbols: ["create_validated_pull_request"],
      },
    ];

    try {
      const response = await fetch(`${apiUrl}/api/v1/evaluation/benchmark`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cases,
          top_k: 3,
          run_full_pipeline: false,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Benchmark failed.");
      setBenchmark(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Benchmark failed.");
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
        <div className="topBar">
          <div className="brandLockup">
            <span className="brandMark">F</span>
            <div>
              <strong>ForgeAI</strong>
              <span>Autonomous Software Engineering Platform</span>
            </div>
          </div>
          <div className="livePill"><span /> Production</div>
        </div>

        <div className="eyebrow">REPOSITORY INTELLIGENCE · AGENTS · VALIDATION · EVALUATION</div>
        <h1>From bug report to validated engineering evidence.</h1>
        <p className="lede">
          ForgeAI investigates repositories, ranks relevant code, builds an engineering plan,
          proposes patches, validates them behind safety gates, and produces auditable execution traces.
        </p>

        <div className="capabilityStrip">
          <span>Hybrid retrieval</span>
          <span>Evidence-backed investigation</span>
          <span>Patch planning</span>
          <span>Sandbox validation</span>
          <span>GitHub PR automation</span>
        </div>

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
            <button
              className="secondaryButton"
              disabled={loading !== null}
              type="button"
              onClick={runFullWorkflow}
            >
              {loading === "workflow" ? "Running workflow…" : "Run full workflow"}
            </button>
            <button
              className="secondaryButton"
              disabled={loading !== null}
              type="button"
              onClick={runBenchmark}
            >
              {loading === "benchmark" ? "Running benchmark…" : "Run benchmark"}
            </button>
          </div>
        </form>

        {error && <p className="error">{error}</p>}
      </section>

      <section className="panel incidentConsole">
        <div className="analysisHeader">
          <div>
            <span className="label">PRODUCTION INCIDENT CORRELATION</span>
            <h2>From runtime failure to suspect regression.</h2>
            <p>
              Add symptoms, an error or stack trace, and optionally the deployed commit.
              ForgeAI correlates runtime evidence with recent diffs and code retrieval.
            </p>
          </div>
          <span className="branch">runtime → commit → code</span>
        </div>

        <div className="incidentInputs">
          <label>
            <span>Incident</span>
            <textarea value={incident} onChange={(e) => setIncident(e.target.value)} />
          </label>
          <label>
            <span>Error / stack evidence</span>
            <textarea
              value={runtimeEvidence}
              onChange={(e) => setRuntimeEvidence(e.target.value)}
              placeholder="Paste an error message, stack trace, or relevant log lines"
            />
          </label>
          <label>
            <span>Deploy SHA (optional)</span>
            <input
              value={deploySha}
              onChange={(e) => setDeploySha(e.target.value)}
              placeholder="e.g. 174da2c9"
            />
          </label>
          <button disabled={loading !== null} type="button" onClick={correlateIncident}>
            {loading === "incident" ? "Correlating incident…" : "Find suspect regression"}
          </button>
        </div>

        {incidentResult && (
          <div className="incidentResult">
            <div className="suspectCard">
              <span className="label">PRIMARY SUSPECT</span>
              {incidentResult.suspected_commit ? (
                <>
                  <div className="suspectHeader">
                    <div>
                      <strong>{incidentResult.suspected_commit.short_sha}</strong>
                      <p>{incidentResult.suspected_commit.subject}</p>
                    </div>
                    <span className="score">
                      {Math.round(incidentResult.suspected_commit.confidence * 100)}%
                    </span>
                  </div>
                  <div className="symbols">
                    {incidentResult.suspected_commit.changed_files.slice(0, 6).map((path) => (
                      <code key={path}>{path}</code>
                    ))}
                  </div>
                  <ul>
                    {incidentResult.suspected_commit.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p>No recent commit crossed the evidence threshold.</p>
              )}
            </div>

            <div className="incidentHypothesis">
              <span className="label">CODE-LEVEL HYPOTHESIS</span>
              <h3>{incidentResult.investigation.hypothesis.summary}</h3>
              <p>
                Confidence {Math.round(incidentResult.investigation.hypothesis.confidence * 100)}%
                {" · "}{incidentResult.correlation_mode}
              </p>
            </div>

            <div className="candidateList">
              {incidentResult.candidates.slice(0, 4).map((candidate) => (
                <article key={candidate.sha}>
                  <div className="commandHeader">
                    <strong>{candidate.short_sha} · {candidate.subject}</strong>
                    <span>score {candidate.score.toFixed(2)}</span>
                  </div>
                  <p>{candidate.changed_files.slice(0, 3).join(" · ") || "No changed files detected"}</p>
                </article>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="analysisHeader">
          <div>
            <span className="label">DEPENDENCY / CALL GRAPH</span>
            <h2>Trace the regression&apos;s blast radius.</h2>
            <p>
              Map changed symbols to runtime evidence, upstream callers, downstream dependencies,
              and affected endpoints using a bounded static graph.
            </p>
          </div>
          <span className="branch">diff → symbol → runtime path</span>
        </div>

        <div className="validateAction">
          <button disabled={loading !== null} type="button" onClick={analyzeBlastRadius}>
            {loading === "impact" ? "Tracing blast radius…" : "Analyze blast radius"}
          </button>
        </div>

        {impactResult && (
          <div>
            <div className="metrics">
              <article><span>Blast radius</span><strong>{impactResult.blast_radius_score.toFixed(0)}/100</strong></article>
              <article><span>Graph nodes</span><strong>{impactResult.graph_nodes}</strong></article>
              <article><span>Affected entrypoints</span><strong>{impactResult.affected_entrypoints.length}</strong></article>
            </div>

            <div className="investigationGrid">
              <div>
                <h3>Changed symbols</h3>
                <div className="resultList">
                  {impactResult.changed_symbols.slice(0, 8).map((node) => (
                    <article className="resultCard" key={node.id}>
                      <div className="commandHeader">
                        <strong>{node.symbol}</strong>
                        <span>{node.kind} · L{node.line_start}</span>
                      </div>
                      <code>{node.path}</code>
                    </article>
                  ))}
                </div>
              </div>

              <div>
                <h3>Affected entrypoints</h3>
                {impactResult.affected_entrypoints.length > 0 ? (
                  <div className="resultList">
                    {impactResult.affected_entrypoints.slice(0, 8).map((node) => (
                      <article className="resultCard" key={node.id}>
                        <div className="commandHeader">
                          <strong>{node.symbol}</strong>
                          <span>L{node.line_start}</span>
                        </div>
                        <code>{node.path}</code>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="muted">No route/entrypoint reached within the bounded traversal.</p>
                )}
              </div>
            </div>

            <div className="validationNotes">
              <h3>Graph evidence</h3>
              <ul>
                {impactResult.explanation.map((item) => <li key={item}>{item}</li>)}
              </ul>
              {impactResult.evidence_paths.length > 0 && (
                <div className="commandList">
                  {impactResult.evidence_paths.slice(0, 6).map((path, index) => (
                    <code key={index}>{path.join(" → ")}</code>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      <section className="panel telemetryPanel">
        <div className="analysisHeader">
          <div>
            <span className="label">TELEMETRY TIMELINE</span>
            <h2>Reconstruct what happened around the failure.</h2>
            <p>
              ForgeAI persists deploy/error events, finds the first failure, locates the nearest
              preceding deploy, and sends that evidence into regression correlation.
            </p>
          </div>
          <span className="branch">events → timeline → cause</span>
        </div>

        <div className="telemetryControls">
          <label>
            <span>Service</span>
            <input value={telemetryService} onChange={(e) => setTelemetryService(e.target.value)} />
          </label>
          <button disabled={loading !== null} type="button" onClick={ingestAndReconstructDemoTelemetry}>
            {loading === "telemetry" ? "Reconstructing timeline…" : "Ingest demo telemetry + reconstruct"}
          </button>
        </div>

        <div className="runtimeProviders">
          <article>
            <div className="commandHeader">
              <strong>Render</strong>
              <span>{renderStatus?.configured ? "connected" : "not configured"}</span>
            </div>
            <p>Deploy history + application logs via Render REST API.</p>
            <button
              className="secondaryButton"
              disabled={loading !== null || renderStatus?.configured !== true}
              type="button"
              onClick={syncRenderTelemetry}
            >
              {loading === "render" ? "Syncing Render…" : "Sync Render"}
            </button>
            {renderSync && <small>{renderSync.accepted_events} events → {renderSync.storage}</small>}
          </article>

          <article>
            <div className="commandHeader">
              <strong>Vercel</strong>
              <span>{vercelStatus?.configured ? "connected" : "not configured"}</span>
            </div>
            <p>Deployments + build events. Runtime errors use generic telemetry or a Log Drain.</p>
            <button
              className="secondaryButton"
              disabled={loading !== null || vercelStatus?.configured !== true}
              type="button"
              onClick={syncVercelTelemetry}
            >
              {loading === "vercel" ? "Syncing Vercel…" : "Sync Vercel"}
            </button>
            {vercelSync && <small>{vercelSync.accepted_events} events → {vercelSync.storage}</small>}
          </article>

          <article>
            <div className="commandHeader">
              <strong>Sentry</strong>
              <span>{sentryStatus?.configured ? "connected" : "not configured"}</span>
            </div>
            <p>Exception events + stack traces + release metadata normalized into ForgeAI telemetry.</p>
            <button
              className="secondaryButton"
              disabled={loading !== null || sentryStatus?.configured !== true}
              type="button"
              onClick={syncSentryTelemetry}
            >
              {loading === "sentry" ? "Syncing Sentry…" : "Sync Sentry"}
            </button>
            {sentrySync && <small>{sentrySync.accepted_events} events → {sentrySync.storage}</small>}
          </article>
        </div>

        <p className="adapterStatus">
          Provider-independent telemetry: Render, Vercel, and Sentry normalize into the same ForgeAI event model.
        </p>

        {telemetryTimeline && (
          <div className="telemetryResult">
            <div className="timelineSummary">
              <article>
                <span>First failure</span>
                <strong>{telemetryTimeline.first_failure_at ? new Date(telemetryTimeline.first_failure_at).toLocaleTimeString() : "None"}</strong>
              </article>
              <article>
                <span>Nearest deploy</span>
                <strong>{telemetryTimeline.nearest_deploy?.deploy_sha ?? "No SHA"}</strong>
              </article>
              <article>
                <span>Events</span>
                <strong>{telemetryTimeline.events.length}</strong>
              </article>
            </div>

            <div className="telemetryEventList">
              {telemetryTimeline.events.map((event) => (
                <article key={event.event_id}>
                  <div className="commandHeader">
                    <strong>{event.event_type} · {event.severity}</strong>
                    <span>{new Date(event.observed_at).toLocaleTimeString()}</span>
                  </div>
                  <p>{event.message}</p>
                  {event.deploy_sha && <code>{event.deploy_sha}</code>}
                </article>
              ))}
            </div>

            {telemetryTimeline.correlation?.suspected_commit && (
              <div className="timelineCorrelation">
                <span className="label">CORRELATED REGRESSION</span>
                <h3>
                  {telemetryTimeline.correlation.suspected_commit.short_sha} ·
                  {" "}{telemetryTimeline.correlation.suspected_commit.subject}
                </h3>
                <p>
                  Confidence {Math.round(telemetryTimeline.correlation.suspected_commit.confidence * 100)}%
                </p>
              </div>
            )}
          </div>
        )}
      </section>

      {benchmark && (
        <section className="panel benchmarkPanel">
          <div className="analysisHeader">
            <div>
              <span className="label">EVALUATION BENCHMARK</span>
              <h2>Measured retrieval quality</h2>
              <p>{benchmark.metrics.cases} gold-labeled cases</p>
            </div>
          </div>

          <div className="benchmarkMetrics">
            <article><span>Top-1 accuracy</span><strong>{Math.round(benchmark.metrics.top1_accuracy * 100)}%</strong></article>
            <article><span>Top-3 recall</span><strong>{Math.round(benchmark.metrics.topk_recall * 100)}%</strong></article>
            <article><span>MRR</span><strong>{benchmark.metrics.mean_reciprocal_rank.toFixed(2)}</strong></article>
            <article><span>Avg latency</span><strong>{benchmark.metrics.average_latency_ms.toFixed(0)}ms</strong></article>
          </div>

          <div className="benchmarkCases">
            {benchmark.results.map((item) => (
              <article key={item.id}>
                <div className="commandHeader">
                  <strong>{item.id}</strong>
                  <span>{item.top1_hit ? "Top-1 hit" : "Top-1 miss"} · {item.latency_ms}ms</span>
                </div>
                <p>
                  Recall@3 {Math.round(item.topk_recall * 100)}% · MRR {item.reciprocal_rank.toFixed(2)} · {item.retrieval_mode}
                </p>
                <code>{item.ranked_files[0] ?? "No result"}</code>
              </article>
            ))}
          </div>
        </section>
      )}

      {recentRuns.length > 0 && (
        <section className="panel traceHistoryPanel">
          <div className="analysisHeader">
            <div>
              <span className="label">TRACE HISTORY</span>
              <h2>Recent agent runs</h2>
              <p>Latest workflow executions retained by the live API.</p>
            </div>
            <button className="secondaryButton" type="button" onClick={loadRecentRuns}>Refresh</button>
          </div>

          <div className="traceHistoryList">
            {recentRuns.map((run) => (
              <button key={run.run_id} type="button" onClick={() => loadTrace(run.run_id)}>
                <div>
                  <strong>#{run.run_id}</strong>
                  <span>{run.repository}</span>
                </div>
                <div>
                  <span>{run.status}</span>
                  <span>{run.total_duration_ms}ms</span>
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {workflowRun && (
        <section className="panel tracePanel">
          <div className="analysisHeader">
            <div>
              <span className="label">EXECUTION TRACE</span>
              <h2>Run #{workflowRun.run_id}</h2>
              <p>
                {workflowRun.status} · {(workflowRun.metrics.total_duration_ms / 1000).toFixed(2)}s total
              </p>
            </div>
            <span className={`validationBadge ${workflowRun.metrics.pr_gate_open ? "safe" : "blocked"}`}>
              {workflowRun.metrics.pr_gate_open ? "PR gate open" : "PR gate blocked"}
            </span>
          </div>

          <div className="traceMetrics">
            <article><span>Evidence</span><strong>{workflowRun.metrics.evidence_count}</strong></article>
            <article><span>Patches</span><strong>{workflowRun.metrics.patch_count}</strong></article>
            <article><span>Validation checks</span><strong>{workflowRun.metrics.validation_commands}</strong></article>
            <article><span>Retrieval</span><strong>{workflowRun.metrics.retrieval_mode ?? "n/a"}</strong></article>
          </div>

          <div className="timeline">
            {workflowRun.stages.map((stage, index) => (
              <article className="timelineStage" key={`${stage.name}-${index}`}>
                <div className="timelineMarker">{String(index + 1).padStart(2, "0")}</div>
                <div className="timelineBody">
                  <div className="commandHeader">
                    <strong>{stage.name.replaceAll("_", " ")}</strong>
                    <span>{stage.status} · {stage.duration_ms}ms</span>
                  </div>
                  {Object.keys(stage.details).length > 0 && (
                    <div className="traceDetails">
                      {Object.entries(stage.details).map(([key, value]) => (
                        <code key={key}>{key}: {String(value)}</code>
                      ))}
                    </div>
                  )}
                  {stage.error && <p className="traceError">{stage.error}</p>}
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

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

      {validation?.safe_to_propose_pr && plan && plan.patches.length > 0 && (
        <section className="panel prPanel">
          <div className="analysisHeader">
            <div>
              <span className="label">HUMAN APPROVAL GATE</span>
              <h2>Create validated GitHub pull request</h2>
              <p>
                ForgeAI will re-run server-side validation before any branch, commit, or PR is created.
              </p>
            </div>
          </div>

          <label className="approvalControl">
            <input
              type="checkbox"
              checked={prApproved}
              onChange={(event) => setPrApproved(event.target.checked)}
            />
            <span>
              I approve ForgeAI creating a branch, committing the validated patch, and opening a pull request.
            </span>
          </label>

          <button disabled={!prApproved || loading !== null} type="button" onClick={createPullRequest}>
            {loading === "pr" ? "Creating pull request…" : "Create validated PR"}
          </button>

          {prResult && (
            <div className="prResult">
              <strong>{prResult.message}</strong>
              {prResult.pull_request_url && (
                <a href={prResult.pull_request_url} target="_blank" rel="noreferrer">
                  Open PR #{prResult.pull_request_number}
                </a>
              )}
              {prResult.branch && <code>{prResult.branch}</code>}
            </div>
          )}
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

      <section className="productProof">
        <article>
          <span>01</span>
          <strong>Evidence before generation</strong>
          <p>ForgeAI retrieves and ranks concrete code before planning or proposing changes.</p>
        </article>
        <article>
          <span>02</span>
          <strong>Validation before writes</strong>
          <p>Repository mutation stays gated behind explicit approval and fresh server-side validation.</p>
        </article>
        <article>
          <span>03</span>
          <strong>Measured agent quality</strong>
          <p>Gold-labeled benchmarks report localization accuracy, recall, MRR, latency, and gate behavior.</p>
        </article>
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
