# ForgeAI Measured Benchmarks

## Live seed benchmark — 2026-10-05

Environment:
- API: Render, Singapore
- Web: Render, Singapore
- Retrieval mode: lexical fallback (no production embedding key configured)
- Corpus: 3 gold-labeled ForgeAI self-repository tasks
- Verification: external GitHub Actions live smoke against the deployed API

### Ranking v2 results

| Metric | Result |
| --- | ---: |
| Top-1 file accuracy | 66.67% |
| Recall@3 | 100.00% |
| Mean Reciprocal Rank | 0.8333 |
| Symbol hit accuracy | 100.00% |
| Mean task-ranking latency | 99.67 ms |

### Before / after structural reranking

| Metric | Initial live ranker | Ranking v2 |
| --- | ---: | ---: |
| Top-1 accuracy | 33.33% | 66.67% |
| Recall@3 | 66.67% | 100.00% |
| MRR | 0.5278 | 0.8333 |
| Symbol hit accuracy | 100.00% | 100.00% |

Ranking v2 improved file localization by giving stronger weight to structural evidence
(file paths and code symbols), adding lightweight software-engineering concept expansion,
and reducing unrelated test-file noise.

## Seed cases

1. GitHub repository URL validation
2. Sandboxed patch validation
3. Human approval + fresh validation before GitHub PR creation

## Interpretation

These numbers are useful as a regression baseline, not as a claim of broad software-
engineering benchmark performance. The seed set currently contains only three tasks from
ForgeAI's own repository. Results should therefore be described publicly as a
**3-case seed benchmark**.

The next evaluation milestone is a larger multi-repository corpus with known bugs and
implementation locations, followed by patch and validation outcome benchmarks.
