from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

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

    def _load_dataframe(self, config_name: str) -> pd.DataFrame:
        return self.provider.get_config_table(config_name)

    def load_kpi_configs(self) -> list[KPIConfig]:
        df = self._load_dataframe("kpi_config")
        return [
            KPIConfig(
                channel=row["channel"],
                market=row["market"],
                kpi_name=row["kpi_name"],
                frequency=row["frequency"],
                source_table=row["source_table"],
                date_column=row["date_column"],
                active=bool(row["active"]),
            )
            for _, row in df.iterrows()
        ]

    def load_ready_rule_configs(self) -> list[ReadyRuleConfig]:
        df = self._load_dataframe("ready_rule_config")
        return [
            ReadyRuleConfig(
                channel=row["channel"],
                market=row["market"],
                kpi_name=row["kpi_name"],
                ready_rule=row["ready_rule"],
                business_calendar=row["business_calendar"],
                effective_from=row["effective_from"],
                effective_to=row.get("effective_to", None),
            )
            for _, row in df.iterrows()
        ]

    def load_business_calendar_configs(self) -> list[BusinessCalendarConfig]:
        df = self._load_dataframe("calendar_config")
        return [
            BusinessCalendarConfig(
                market=row["market"],
                calendar_date=row["calendar_date"],
                is_business_day=bool(row["is_business_day"]),
            )
            for _, row in df.iterrows()
        ]

    def load_source_table_mappings(self) -> list[SourceTableMapping]:
        df = self._load_dataframe("source_table_mapping")
        return [
            SourceTableMapping(
                market=row["market"],
                source_table_name=row["source_table_name"],
            )
            for _, row in df.iterrows()
        ]

    def get_active_kpi_config(self, channel: str, market: str, frequency: str) -> list[KPIConfig]:
        configs = self.load_kpi_configs()
        return [
            config
            for config in configs
            if config.channel == channel
            and config.market == market
            and config.frequency == frequency
            and config.active
        ]

    def get_ready_rule(self, channel: str, market: str, kpi_name: str, effective_date: date) -> ReadyRuleConfig:
        rules = self.load_ready_rule_configs()
        candidates = [
            rule
            for rule in rules
            if rule.channel == channel
            and rule.market == market
            and rule.kpi_name == kpi_name
            and rule.effective_from <= effective_date
            and (rule.effective_to is None or rule.effective_to >= effective_date)
        ]
        if not candidates:
            raise ValueError(f"No ready rule found for {channel}/{market}/{kpi_name} at {effective_date}")
        return sorted(candidates, key=lambda r: (r.effective_from, r.effective_to or date.max), reverse=True)[0]
