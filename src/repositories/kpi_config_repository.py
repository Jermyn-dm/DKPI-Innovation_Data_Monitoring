from __future__ import annotations

from typing import Any

import pandas as pd

from models import KPIConfig, SourceTableMapping
from repositories.base_config_repository import BaseConfigurationRepository, ConfigurationDataSource


class KPIConfigRepository(BaseConfigurationRepository):
    """Repository for KPI metadata and logical source mappings."""

    def __init__(self, data_source: ConfigurationDataSource) -> None:
        self.data_source = data_source

    def load_kpi_configs(self) -> list[KPIConfig]:
        return [KPIConfig.model_validate(self._normalize_record(row)) for row in self.data_source.read_table("kpi_config").to_dict("records")]

    @staticmethod
    def _normalize_record(row: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(row)
        for field in ("monthly", "daily", "integration", "active"):
            normalized[field] = str(normalized.get(field, "N")).strip().upper() == "Y"
        for field in ("kpi_id", "run_batch", "mvp1/mvp2", "derivation logic", "target availability", "remark"):
            value = normalized.get(field)
            if pd.isna(value):
                normalized[field] = None
        return normalized

    def load_validation_rules(self) -> list[Any]:
        raise NotImplementedError

    def load_business_calendar(self, calendar_code: str | None = None, market: str | None = None) -> list[Any]:
        raise NotImplementedError

    def validate_configuration(self) -> list[str]:
        return []

    def load_source_mappings(self) -> list[SourceTableMapping]:
        return [
            SourceTableMapping.model_validate(row)
            for row in self.data_source.read_table("source_table_mapping").to_dict("records")
        ]
