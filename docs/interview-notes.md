# Interview notes

## Explain-back: the build

### Parsing and split

- **Why read columns as text first?** It keeps parsing policy explicit: labels are not silently coerced, missing markers are controlled, and numeric inference happens only after the header and values have been checked.
- **What happens to a class called `NA`?** It stays a literal label unless the user explicitly lists `NA` as a missing token.
- **Why validate the header before pandas?** Duplicate or invalid names must be detected before a dataframe library can rename or normalize them.
- **What is schema inference?** It classifies columns from their values across the uploaded file. It describes representation; it does not fit a model or use a target-driven feature decision.
- **What does stratification guarantee?** It preserves class proportions as far as integer row counts allow. It does not guarantee every class has enough examples for both partitions; that is checked after splitting.
- **Why can random subsampling hurt rare classes?** A small class can disappear or become too small to split. The per-class floor of `ceil(1 / test_size)` preserves enough examples for the requested split.
- **Why split before feature decisions?** Feature diagnostics must be based only on training rows, and the split needs only target, seed, and test size.
- **Why save row IDs and split parameters?** Every model and result must refer to the exact reviewed partition, rather than a later recomputation that might differ.

### Diagnostics and training

- **Why train-only diagnostics?** Looking at test features to choose exclusions or preprocessing would let evaluation data influence the analysis.
- **What does a 0.75 repeated-vector ceiling mean?** Among repeated training feature vectors, at most 75% can be matched to their most frequent label. It is not a test-set or whole-dataset accuracy ceiling.
- **Why report duplicates instead of deleting them?** Repeats may be legitimate observations; conflicting labels are evidence worth reviewing, not permission to silently change the data.
- **Why ask about integer ID-like columns?** A uniqueness heuristic can flag a useful count or measurement. The user, not an automatic rule, decides whether the column belongs.
- **Why put imputation and scaling in a pipeline?** Each transformer is fitted on training rows only, then applied unchanged to test rows.
- **Why scale only logistic regression?** Its optimization depends on feature scale; decision trees split on thresholds and do not need standardization.
- **What does macro averaging do?** It computes a metric per class and gives each class equal weight. It can differ from accuracy when class sizes are uneven.
- **What does the Dummy baseline show?** It supplies a simple reference (most-frequent class); it does not establish that a model is useful in another setting.
- **Why encode the target once?** Every estimator receives consistent numeric labels, while result formatting can map predictions back to the original labels.
- **Why record per-model failures?** One estimator can fail without hiding successful model results or discarding the run's other diagnostics.

### Statistics and API

- **Why McNemar, not a paired t-test?** The outcome is paired correctness on the same rows and is binary; McNemar tests the discordant correctness pairs directly.
- **What are `b` and `c`?** `b` counts rows where A is correct and B is wrong; `c` counts rows where A is wrong and B is correct. Concordant rows do not inform this test.
- **Why use the exact test?** It avoids a large-sample chi-square approximation and remains defined for small discordant counts. With zero discordances, the result is explicitly undefined rather than NaN.
- **Why Holm-adjust p-values?** It controls family-wise error across the model-pair tests. It does not adjust slice exploration or prove practical importance.
- **Disagreement versus discordance?** Different predictions are disagreements; discordance means exactly one prediction is correct. In multiclass data both models can be wrong in different ways.
- **Why are slices exploratory?** They are post-hoc subgroup views with many possible comparisons and can be unstable when support is small.
- **Why stream uploads?** The server can enforce the byte cap while writing chunks without retaining the entire upload in memory.
- **Why validate IDs as UUIDs?** IDs are path components; validating them before path construction prevents user-supplied path text from selecting arbitrary files.
- **Why can preflight recompute?** It is deterministic from the stored upload, reviewed split, and explicit choices; it avoids stale cached diagnostics.
- **What does `prepare()` guarantee?** It reloads the exact stored partition, applies explicit missing-token and column decisions, fits no estimator, and returns validated train/test data ready for the run.
- **Why a lock instead of a queue?** The product allows one active local run; a non-blocking lock rejects extra work immediately with 409 instead of accepting an unpromised queue.
- **What happens after a mid-training stop?** The next startup marks persisted running work interrupted and removes its temporary upload and split records; completed results remain on disk.
- **Why release the lock in `finally`?** Success and every error path must allow a later run.
- **Why persist status and poll?** The UI can reconnect to file-backed state after navigation or a process restart. A local single-run workflow does not need websocket infrastructure.

### Frontend

- **Where does workflow state live?** React holds the current screen state, while the API persists uploads, splits, and completed runs so history is not tied to one component lifetime.
- **Why a development proxy rather than CORS?** The frontend and API use one origin; the proxy forwards API paths without broadening the API's cross-origin surface.
- **Why poll instead of WebSockets?** A status request is simple and sufficient for one local training job; live bidirectional messaging adds machinery without a product need.
- **What disables Start?** Missing or stale preflight, unresolved column decisions, an invalid model count, unconfirmed datetime-like features, or a request already being submitted.
- **How do you read the pair table?** Compare each pair's accuracy and discordant counts, then read the raw and Holm-adjusted McNemar p-values with their test-set scope.
- **Why does Holm p differ from raw p?** It accounts for the run's family of pairwise tests and is usually at least as conservative as the unadjusted value.
- **Why grey low-support slices?** Few rows or events produce noisy estimates; the style warns against over-interpreting them rather than declaring them invalid.
- **What does “undefined” mean?** The statistic's mathematical preconditions were not met (for example no discordant rows for McNemar or no probability output for AUC); the UI presents a reason instead of a non-finite number.
- **What should you check before saying one model is better?** Test split and class balance, metrics beyond accuracy, discordant counts, adjusted p-value, practical effect size, slice support, and whether the result repeats under other seeds or data.

## Data handling in three separate steps

Schema inference describes how each input column is represented, using text values from the uploaded file. Fitted preprocessing (such as medians, frequent categories, and scaling) is learned inside each model pipeline from training rows only and then applied to held-out rows. Feature diagnostics are a separate review: they inspect training rows to flag possible leakage, identifiers, duplicates, or missingness, and any inclusion decision remains explicit. None of these steps uses test rows to fit a transformation.

## Four-row paired example

| Row | Actual | Model A | Model B | A correct? | B correct? |
|---:|---|---|---|---|---|
| 1 | yes | yes | no | yes | no |
| 2 | no | no | no | yes | yes |
| 3 | yes | no | no | no | no |
| 4 | no | yes | no | no | yes |

Check 1: predictions disagree on rows 1 and 4 (two rows), while row 3 is a different-prediction-free, both-wrong case. Check 2: `b = 1` (row 1: A correct, B wrong) and `c = 1` (row 4: A wrong, B correct); row 2 is concordant-correct and row 3 concordant-incorrect, so neither enters McNemar's test. In this example `b + c = 2`.

## SRS section 15: design decisions

| Decision | Defence |
|---|---|
| Python and React | The model stack is Python; a Node backend would only forward requests. |
| Train-partition diagnostics | The held-out partition is for evaluation, not feature decisions. |
| Stored split record | It preserves the exact row IDs and parameters the user reviewed. |
| Exact McNemar | It matches paired binary correctness and handles small counts. |
| Holm across all pairs | It controls family-wise error for the run's pairwise tests. |
| Preprocessing in pipelines | Each transform is learned from training rows and reused on test rows. |
| Validate after splitting | A class minimum cannot guarantee that both partitions contain the class. |
| Rare-class subsample floor | It protects classes from becoming too small to split. |
| Empty fields only by default | Tokens like `NA` may be genuine labels or categories. |
| `sample_weight` for optional weighting | One interface supports binary and multiclass estimators; the Dummy stays unweighted. |
| Report, do not delete, duplicates | Repeated and conflicting observations can be meaningful evidence. |
| User decides integer IDs | Heuristics cannot distinguish every identifier from a useful integer feature. |
| Fixed default parameters | It keeps the comparison predictable and avoids hidden tuning advantages. |
| Wilson intervals and support flags | Small-slice rates need uncertainty context. |
| Thread, lock, and 409 | It is the smallest design matching a single-user local concurrency contract. |
| Files rather than a database | V1 needs durable run artifacts, not cross-run queries. |
| Fixed registry | It avoids accepting executable model code or pickles. |
| Two interfaces (`RunStore`, `JobRunner`) | A hosted deployment can replace storage and execution without changing the ML core. |
| Local-only privacy boundary | There is no authentication; the app must not be exposed to an untrusted network. |
