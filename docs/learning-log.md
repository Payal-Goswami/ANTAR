# Learning log

## Day 1
- Read CSV headers before pandas so duplicate names are caught before pandas can rename them.
- Read fields as text first to preserve labels such as `NA`; only explicit missing tokens are converted.
- Numeric inference and target cleanup are separate because feature values and labels have different policies.

## Day 3
- Train-only diagnostics are the right place for feature flags because the test split is for measurement, not model setup.
- Repeated feature vectors are reported as a ceiling on what a model can possibly get right, not as rows to delete.
- Whole-number ID-like columns need an explicit decision because a consecutive row ID is useful metadata, while a random identifier is noise.

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
