# ForgeAI Architecture

## Product goal

ForgeAI converts a software-engineering task into an auditable workflow:

```
Repository -> Index -> Retrieve -> Investigate -> Plan -> Patch -> Validate -> Report
```

## Initial system boundaries

### Web
Next.js application responsible for repository onboarding, engineering-task input,
agent execution visualization, diffs, validation results, and evaluation metrics.

### API
FastAPI service responsible for authentication boundaries, repository ingestion,
task orchestration, retrieval, model/tool adapters, validation jobs, and persistence.

### Code intelligence
Source-aware retrieval subsystem using AST/symbol extraction, lexical ranking, and
optional embedding-based semantic reranking. Retrieval degrades safely to lexical mode
when no embedding provider is configured.

### Agent runtime
The first investigation stage is evidence-driven: it consumes ranked repository evidence,
produces a bounded-confidence hypothesis, and recommends verification steps. Later stages
will extend this into planning, patching, validation, and review while preserving explicit
state transitions and observable inputs/outputs.

### Validation sandbox
Patch proposals are applied only to a temporary clone after `git apply --check` succeeds.
ForgeAI derives validation commands from repository structure instead of accepting
arbitrary browser-provided shell commands. Docker execution is network-isolated, drops all
Linux capabilities, uses `no-new-privileges`, limits memory/CPU/PIDs, and uses a read-only
container root filesystem. The disposable repository mount is the only writable project
surface. If Docker is unavailable, ForgeAI performs only a non-executing Git diff check and
keeps the PR gate closed.

## Design principles

1. Evidence before generation.
2. Every proposed code change must be attributable to repository context.
3. No autonomous write to a repository without validation and an approval boundary.
4. Model providers remain swappable.
5. Agent execution must be observable and benchmarkable.
6. ForgeAI should fail safely when repository context or validation is insufficient.

## MVP milestones

1. Repository URL ingestion.
2. Repository file inventory.
3. Code chunking and index.
4. Task-to-file retrieval.
5. Structured investigation report.
6. Patch proposal and diff preview.
7. Validation execution.
8. Final engineering report.


### Planning and patch proposal

The planning stage converts investigation evidence into ordered implementation steps,
target files, risk notes, and validation commands. Patch generation is intentionally
separate from planning: a model may propose a unified diff only for source files that
ForgeAI fetched from the repository and supplied as context. Generated diffs are
review-only artifacts and cannot mutate repositories in this phase. This preserves the
human approval boundary before execution or GitHub writes.


### Observability and execution traces

ForgeAI exposes an orchestrated workflow run that records each major agent stage as a
structured trace span. A span stores its name, status, duration, details, and bounded error
text. Run-level metrics aggregate total latency, completed/failed stages, retrieval mode,
evidence count, patch count, validation-command count, and the final PR-gate decision.
This creates an auditable execution timeline without exposing internal chain-of-thought.
Persistent storage and provider usage/cost metrics are future extensions of the same model.


### Human-approved repository writes

Repository mutation is a separate gated stage. ForgeAI requires an explicit approval
boolean and then reruns sandbox validation server-side before any GitHub write. A passing
client-side state is never trusted. If the fresh validation gate opens, ForgeAI creates a
dedicated branch from the default branch, commits only materialized files from the
validated patch, and opens a pull request with a generated validation report. Direct
commits to the default branch are not used.


### Evaluation

The evaluation layer consumes gold-labeled benchmark cases containing a repository task
and expected implementation files/symbols. It measures Top-1 localization accuracy,
Recall@K, Mean Reciprocal Rank, symbol accuracy, and retrieval latency. Optional full
workflow evaluation additionally records whether patches are generated, sandbox
validation passes, and the PR gate matches an expected outcome. Benchmark scoring logic
is deterministic and unit-tested independently of model credentials.
