# Day 10 acceptance checks

These checks cover the V1 acceptance criteria in the SRS. The local backend suite, frontend checks, and Compose smoke tests were run on the Windows host described in the README. This is local verification, not a CI claim.

| # | Acceptance check | Result and evidence |
|---|---|---|
| 1 | The bundled sample completes through the UI. | Pass — the Breast Cancer sample completed in the browser. |
| 2 | A numeric/categorical CSV with missing values completes with three selected models. | Pass — the 4,000-row UCI Adult extract ran through the UI with explicit `?` missing tokens. |
| 3 | Requirements are implemented and automated checks pass. | Pass locally — 65 backend tests pass; frontend lint and production build pass. |
| 4 | A concurrent submission receives HTTP 409 without interrupting the active run. | Pass — covered by the backend run-control tests. |
| 5 | Models use the same test row IDs stored in the split. | Pass — covered by split-alignment and runner tests. |
| 6 | A run cannot override the target, seed, or test size. | Pass — covered by API validation tests. |
| 7 | Invalid targets, splits, and wide headers are rejected with readable errors. | Pass — covered by CSV, split, and API validation tests. |
| 8 | Test-partition feature changes do not affect train-only diagnostics. | Pass — covered by the diagnostic leakage tests. |
| 9 | `NA` is preserved as a target unless explicitly declared missing. | Pass — covered by missing-token tests. |
| 10 | Subsampling preserves rare classes and is deterministic for a seed. | Pass — covered by split tests. |
| 11 | An unresolved identifier-like feature blocks a run. | Pass — covered by feature-decision tests. |
| 12 | McNemar and Holm results match expected fixture values, including no discordance. | Pass — covered by paired-statistics tests. |
| 13 | API outputs contain no NaN or infinity. | Pass — responses and statistics are checked with strict JSON serialization tests. |
| 14 | Binary and multiclass disagreement cases are handled correctly. | Pass — covered by binary and multiclass pair tests. |
| 15 | History survives restart and retention keeps the newest 20 runs. | Pass — three Compose runs remained available after a backend restart; retention behavior is covered by store tests. |
| 16 | An active run is marked interrupted after shutdown and its upload/split are removed. | Pass — a forced backend-container stop during an Adult run was followed by recovery; the run became interrupted and its upload, metadata, and split files were removed. |
| 17 | Compose starts the app with host access bound to `127.0.0.1`. | Pass — the frontend is published only on `127.0.0.1:8080`; the backend has no host-published port. |
| 18 | README includes setup, architecture, limitations, hardware-qualified timings, and a real finding. | Pass — see the README and findings report. |

The backend tests emit two known warnings: a Starlette/httpx deprecation notice and a scikit-learn undefined ROC-AUC warning for a single-class test fixture.

Compose was built and run from the current worktree; a separate fresh-clone reproduction was not performed.
