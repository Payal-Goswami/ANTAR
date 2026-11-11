# Learning log

## Day 1
- Read CSV headers before pandas so duplicate names are caught before pandas can rename them.
- Read fields as text first to preserve labels such as `NA`; only explicit missing tokens are converted.
- Numeric inference and target cleanup are separate because feature values and labels have different policies.

## Day 2
- Stratification preserves class proportions but cannot guarantee a valid split for every class; validate the actual partitions.
- A saved split record makes reviewed row IDs part of the run contract rather than relying on a later recomputation.
- Rare-class floors make deterministic subsampling safer without pretending it is perfectly proportional.

## Day 3
- Train-only diagnostics are the right place for feature flags because the test split is for measurement, not model setup.
- Repeated feature vectors are reported as a ceiling on what a model can possibly get right, not as rows to delete.
- Whole-number ID-like columns need an explicit decision because a consecutive row ID is useful metadata, while a random identifier is noise.

## Day 4
- Put imputers, encoders, and scalers inside each model pipeline so they learn from training rows only.
- Compare every model on the same test row IDs; otherwise pairwise disagreement is not a paired comparison.
- Macro-F1 and per-class recall reveal class failures that accuracy can hide.

## Day 5
- Pairwise model comparison is a disagreement problem: the information lives in discordant rows, not in overall accuracy alone.
- McNemar's exact test is the right check for paired predictions because each row is a paired observation with two models.
- Holm adjustment protects the family-wise error rate when comparing multiple model pairs, while Wilson intervals communicate uncertainty for small slice sizes.

## Day 6
- Uploads are streamed to a temporary file so size limits and SHA-256 fingerprints are enforced without keeping the whole file in memory.
- Validate opaque IDs before constructing filesystem paths; a UUID-shaped ID is part of path safety, not just formatting.
- Preflight is deterministic from the upload, saved split, and explicit feature choices, so it can be recomputed rather than stored as stale state.
- Keep API errors in one `{code, message, details}` envelope so clients can handle validation and domain failures consistently.

## Day 7
- A non-blocking lock enforces the single-active-run product rule; a queue would accept work the product explicitly promises to reject.
- Persist status and outputs as files so polling and server restarts do not depend on in-memory job state.
- Put lock release and upload cleanup in `finally` paths: success, training failures and exceptions must all unblock the next run.
- Startup recovery marks abandoned running jobs interrupted and removes their temporary inputs; completed results remain available in history.

## Day 8
- Keep the workflow explicit: upload and split, review train-only diagnostics, then start a run.
- A same-origin API proxy avoids adding CORS configuration to a local-only app.
- Polling persisted run status is enough for this single-job workflow and survives a page refresh.

## Day 9
- A pair table needs both effect context and discordant counts; a p-value alone is not a model ranking.
- Multiclass prediction disagreement is broader than McNemar discordance because two wrong labels can still differ.
- Filters and slices are exploratory views over saved predictions, not new model fits or confirmatory tests.

## Day 10
- Compose networking lets Nginx reach the API by service name while exposing only the loopback frontend port.
- A bind-mounted data directory preserves run history across container recreation without checking user data into Git.
- Pin base image tags and exclude data, local dependencies, and build output from Docker contexts for repeatable and private builds.
- Report the machine, container limit, exact dataset protocol, and measured timings together; do not present local measurements as general performance guarantees.
