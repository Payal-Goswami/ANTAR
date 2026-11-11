# Model Disagreement Explorer: initial real-data run

## Dataset and protocol

- **Dataset:** Covertype, from the [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/31/covertype), DOI [10.24432/C50K5N](https://doi.org/10.24432/C50K5N).
- **Attribution and license:** Blackard, J. (1998). *Covertype*. UCI Machine Learning Repository. CC BY 4.0.
- **Extract:** 4,000 rows selected with stratification and random state 2026 from the 581,012-row dataset. A derived `WildernessZone` categorical feature was created from the four one-hot wilderness-area columns; a five-bin elevation feature was also included.
- **Target:** `Cover_Type`, seven classes.
- **Split:** seed 42, 20% test; 3,200 train rows and 800 test rows. No rows were subsampled by MDE's 20,000-row cap.
- **Models:** Dummy baseline, logistic regression, decision tree and random forest, using registry defaults. Feature review required no manual decisions.

The downloaded data and generated CSV are validation inputs only; they are not committed.

## Results

| Model | Test accuracy |
|---|---:|
| Dummy baseline | 0.4875 |
| Logistic regression | 0.7238 |
| Decision tree | 0.6800 |
| Random forest | 0.7750 |

| Pair | Exact McNemar p | Holm-adjusted p |
|---|---:|---:|
| Logistic regression vs. decision tree | 0.017906 | 0.017906 |
| Logistic regression vs. random forest | 0.000046 | 0.000092 |
| Decision tree vs. random forest | 0.000000009 | 0.000000028 |

The three pairwise tests use the same 800 test rows. The p-values indicate paired correctness differences for this split; they do not measure practical value or guarantee performance on new data.

## API responsiveness check

The local API completed upload, split, preflight, training and results retrieval in **11.88 seconds**. The client polled the run-status endpoint 49 times while training; the longest observed status request took **1.31 seconds**. This is a local TestClient timing, not a production latency benchmark.

## Interpretation and limitations

On this stratified extract, all three selected models exceeded the most-frequent-class baseline, and random forest had the highest test accuracy. Pairwise results show the models made meaningfully different correct/incorrect decisions on this particular split. The extract is only 4,000 rows, one seed and default model settings; the results are exploratory and do not establish which model will perform best on another sample.

## Additional real-data run: Adult

- **Source:** UCI Adult (Census Income), [dataset page](https://archive.ics.uci.edu/dataset/2/adult), DOI [10.24432/C5XW20](https://doi.org/10.24432/C5XW20). The original `adult.data` input and this extract are local validation files, not committed. Follow the UCI page's attribution and reuse terms.
- **Extract:** 4,000 uniformly sampled rows from the 32,561-row `adult.data` file using Python `random.Random(42).sample`. The source has no header; the standard 14 feature names and `income` target were added, and field whitespace was stripped. The extract contains 554 `?` markers across feature cells; `?` was explicitly supplied as a missing token.
- **Split:** target `income`, seed 42, stratified 80/20 split; 3,200 train rows and 800 test rows. The extract has 3,035 `<=50K` and 965 `>50K` labels. All 14 features were included.
- **Models:** Dummy baseline, logistic regression, decision tree, and random forest with registry defaults.

| Model | Test accuracy | Macro-F1 |
|---|---:|---:|
| Dummy baseline | 0.75875 | 0.43141 |
| Logistic regression | 0.84375 | 0.77643 |
| Decision tree | 0.81500 | 0.75333 |
| Random forest | 0.84375 | 0.77816 |

| Pair | Discordant `b`, `c` | Exact McNemar p | Holm-adjusted p |
|---|---:|---:|---:|
| Logistic regression vs. decision tree | 78, 55 | 0.056028 | 0.112056 |
| Logistic regression vs. random forest | 35, 35 | 1.000000 | 1.000000 |
| Decision tree vs. random forest | 43, 66 | 0.034615 | 0.103846 |

At the 0.05 level, no pair is significant after Holm adjustment. The decision-tree/random-forest raw p-value is below 0.05 but its adjusted p-value is not; the logistic-regression/decision-tree raw p-value is already above 0.05. These results do not establish equivalence. They describe paired correctness on this 800-row test partition, not training randomness, practical value, or performance on another sample.

This run used the local FastAPI `TestClient` before the Compose smoke test. Upload/profile took 0.249 s, split took 0.244 s, and the complete background run took 5.724 s. These are local workflow timings, not production benchmarks.

### Compose smoke run

The same Adult workflow was exercised through the Compose API on the Windows host described in the README. Upload/profile took 0.738 s, split took 0.387 s, and the complete run took 8.935 s wall-clock. These timings include local container and browser/API overhead and are not production benchmarks.

The bundled Breast Cancer sample was also measured through the Compose API: upload/profile took 1.110 s, split took 1.208 s, and the complete run took 2.632 s wall-clock. Both workflows used seed 42 and an 80/20 split; the sample run used logistic regression, decision tree and random forest, while the Adult run used the same three selected models.

Docker Desktop reported 4 CPUs and 3.75 GiB available to its VM; this is not a per-container memory limit. A short `docker stats` sampling run observed a 249.1 MiB peak for the backend, but only four samples were captured, so this is an observation rather than a reliable memory benchmark.

After the row-serialization fix, the rebuilt backend returned HTTP 200 with 25 rows from the Adult disagreement endpoint. The three original stored runs remained available after restarting the backend through Compose. A separate forced backend stop during an Adult run recovered it as `interrupted` and removed its upload, metadata, and split. The frontend remained bound only to `127.0.0.1:8080`.
