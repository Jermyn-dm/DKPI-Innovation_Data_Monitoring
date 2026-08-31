from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class KPIConfig(BaseModel):
    country_cd: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    kpi_id: str | None = None
    kpi_name: str = Field(min_length=1)
    monthly: bool
    daily: bool
    run_batch: str | int | None = None
    mvp1_mvp2: str | None = Field(default=None, validation_alias="mvp1/mvp2")
    derivation_logic: str | None = Field(default=None, validation_alias="derivation logic")
    integration: bool
    target_availability: str | None = Field(default=None, validation_alias="target availability")
    remark: str | None = None
    source_table: str = Field(min_length=1)
    active: bool = True
    effective_from: date | None = None
    effective_to: date | None = None


Frequency = str


class SourceTableMapping(BaseModel):
    source_table: str = Field(min_length=1)
    market: str = Field(min_length=1)
    provider_type: Literal["excel", "databricks"]
    physical_object_name: str = Field(min_length=1)
