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
