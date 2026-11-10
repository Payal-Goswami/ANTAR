# Learning log

## Day 1
- Read CSV headers before pandas so duplicate names are caught before pandas can rename them.
- Read fields as text first to preserve labels such as `NA`; only explicit missing tokens are converted.
- Numeric inference and target cleanup are separate because feature values and labels have different policies.
