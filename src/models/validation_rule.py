from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ValidationRuleType = Literal[
    "RECORD_EXISTS",
    "VALUE_NOT_NULL",
    "VALUE_GREATER_THAN_ZERO",
    "CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT",
    "DEVIATION_FROM_STANDARD_WITHIN_PERCENT",
    "EDL_MATCH_ANAPLAN",
    "EDL_MATCH_PBI",
]


class KPIValidationRule(BaseModel):
    """Configuration for one data validation rule applied to one KPI."""

    channel: str = Field(min_length=1)
    market: str = Field(min_length=1)
    kpi_id: str | None = None
    kpi_name: str = Field(min_length=1)
    frequency: Literal["Daily", "Monthly"]
    source_table: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    rule_type: ValidationRuleType
    rule_order: int = Field(default=1, ge=1)
    value_column: str | None = None
    threshold_percent: float | None = Field(default=None, ge=0)
    standard_value: float | None = None
    comparison_source: Literal["ANAPLAN", "PBI"] | None = None
    enabled: bool = True
    effective_from: date | None = None
    effective_to: date | None = None
    remark: str | None = None

    @model_validator(mode="after")
    def validate_rule_parameters(self) -> "KPIValidationRule":
        if self.enabled and self.rule_type in {
            "VALUE_NOT_NULL",
            "VALUE_GREATER_THAN_ZERO",
            "CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT",
            "DEVIATION_FROM_STANDARD_WITHIN_PERCENT",
            "EDL_MATCH_ANAPLAN",
            "EDL_MATCH_PBI",
        } and not self.value_column:
            raise ValueError("value_column is required for value-based validation rules")
        if self.enabled and self.rule_type in {
            "CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT",
            "DEVIATION_FROM_STANDARD_WITHIN_PERCENT",
        } and self.threshold_percent is None:
            raise ValueError("threshold_percent is required for comparison validation rules")
        expected_source = {
            "EDL_MATCH_ANAPLAN": "ANAPLAN",
            "EDL_MATCH_PBI": "PBI",
        }.get(self.rule_type)
        if expected_source and self.comparison_source not in {None, expected_source}:
            raise ValueError(f"comparison_source must be {expected_source} for {self.rule_type}")
        return self
