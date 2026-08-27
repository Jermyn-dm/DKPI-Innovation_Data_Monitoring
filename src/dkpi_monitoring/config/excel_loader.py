from __future__ import annotations

from datetime import date
from typing import Any

from dkpi_monitoring.config.loader import ConfigLoader
from dkpi_monitoring.models import (
    BusinessCalendarConfig,
    KPIConfig,
    ReadyRuleConfig,
    SourceTableMapping,
)
from dkpi_monitoring.providers.base import DataProvider


class ExcelConfigLoader(ConfigLoader):
    def __init__(self, provider: DataProvider, config_source: str):
        super().__init__(provider, config_source)

    def _load_dataframe(self, config_name: str) -> Any:
        raise NotImplementedError

    def load_kpi_configs(self) -> list[KPIConfig]:
        raise NotImplementedError

    def load_ready_rule_configs(self) -> list[ReadyRuleConfig]:
        raise NotImplementedError

    def load_business_calendar_configs(self) -> list[BusinessCalendarConfig]:
        raise NotImplementedError

    def load_source_table_mappings(self) -> list[SourceTableMapping]:
        raise NotImplementedError

    def get_active_kpi_config(self, channel: str, market: str, frequency: str) -> list[KPIConfig]:
        raise NotImplementedError

    def get_ready_rule(self, channel: str, market: str, kpi_name: str, effective_date: date) -> ReadyRuleConfig:
        raise NotImplementedError
