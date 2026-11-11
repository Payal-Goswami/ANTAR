from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SplitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = Field(min_length=1)
    target_missing_tokens: list[str] = Field(default_factory=list)
    seed: int = 42
    test_size: float = 0.2


class PreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    split_id: str
    missing_tokens: list[str] = Field(default_factory=list)
    column_decisions: dict[str, str] = Field(default_factory=dict)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    upload_id: str
    split_id: str
    missing_tokens: list[str] = Field(default_factory=list)
    column_decisions: dict[str, str] = Field(default_factory=dict)
    models: list[str]
    class_weight: bool = False
    independence_confirmed: bool = False
