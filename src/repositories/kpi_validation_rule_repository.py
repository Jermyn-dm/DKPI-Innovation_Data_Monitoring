from __future__ import annotations

from typing import Any

import pandas as pd

from models import KPIValidationRule
from repositories.base_config_repository import BaseConfigurationRepository, ConfigurationDataSource


class KPIValidationRuleRepository(BaseConfigurationRepository):
    """Repository for KPI validation-rule configuration rows."""

    def __init__(self, data_source: ConfigurationDataSource) -> None:
        self.data_source = data_source

    def load_kpi_configs(self) -> list:
        raise NotImplementedError

    def load_validation_rules(self) -> list[KPIValidationRule]:
        records = self.data_source.read_table("kpi_validation_rule_config").to_dict("records")
        return [KPIValidationRule.model_validate(self._normalize_record(record)) for record in records]

    @staticmethod
    def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(record)
        for field in ("enabled",):
            normalized[field] = str(normalized.get(field, "N")).strip().upper() == "Y"
        for field in ("kpi_id", "value_column", "threshold_percent", "standard_value", "effective_from", "effective_to", "remark"):
            if pd.isna(normalized.get(field)):
                normalized[field] = None
        return normalized

    def load_business_calendar(self, calendar_code: str | None = None, market: str | None = None) -> list:
        raise NotImplementedError

    def validate_configuration(self) -> list[str]:
        raise NotImplementedError
