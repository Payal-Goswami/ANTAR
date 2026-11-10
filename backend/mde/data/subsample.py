from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import pandas as pd


def allocate(counts: dict[str, int], cap: int, test_size: float) -> dict[str, int]:
    if cap <= 0:
        raise ValueError("cap must be positive")
    total = sum(counts.values())
    if total <= cap:
        return dict(counts)

    reserve = {label: min(n, max(1, math.ceil(1 / test_size))) for label, n in counts.items()}
    total_reserve = sum(reserve.values())
    if total_reserve > cap:
        raise ValueError("The reserve exceeds the cap.")

    remaining = cap - total_reserve
    room = {label: max(0, counts[label] - reserve[label]) for label in counts}
    total_room = sum(room.values())
    if total_room == 0:
        return dict(reserve)

    quotas = {}
    for label in sorted(counts):
        raw = remaining * room[label] / total_room
        quotas[label] = math.floor(raw)

    leftover = remaining - sum(quotas.values())
    if leftover > 0:
        ordered = sorted(
            counts,
            key=lambda label: (-(remaining * room[label] / total_room - quotas[label]), label),
        )
        for label in ordered[:leftover]:
            quotas[label] += 1

    result = {label: reserve[label] + quotas[label] for label in counts}
    if sum(result.values()) != cap:
        raise AssertionError("Allocation does not sum to the cap.")

    for label, value in result.items():
        if value > counts[label]:
            raise AssertionError(f"Allocated too many rows for {label}.")
    return result


def subsample_ids(y: pd.Series, cap: int, test_size: float, seed: int) -> list[int]:
    counts = y.value_counts().to_dict()
    target_counts = allocate({str(k): int(v) for k, v in counts.items()}, cap, test_size)
    rng = np.random.default_rng(seed)
    chosen: list[int] = []
    for label in sorted(target_counts):
        ids = y.index[y.astype(str) == str(label)].tolist()
        sample_size = target_counts[str(label)]
        if sample_size <= 0:
            continue
        if len(ids) <= sample_size:
            chosen.extend(ids)
        else:
            picked = rng.choice(ids, size=sample_size, replace=False)
            chosen.extend(int(v) for v in picked)
    chosen.sort()
    return chosen
