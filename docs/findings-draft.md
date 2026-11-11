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
