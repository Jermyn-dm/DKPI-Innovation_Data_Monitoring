from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from models import BusinessCalendarEntry, KPIConfig, KPIValidationRule


class ConfigurationDataSource(Protocol):
    """Source boundary for configuration tables only."""

    def read_table(self, table_name: str) -> pd.DataFrame:
        ...


class ExcelConfigurationDataSource:
    """Reads configuration workbooks without implementing KPI data access."""

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def read_table(self, table_name: str) -> pd.DataFrame:
        return pd.read_excel(self.config_path / f"{table_name}.xlsx")


class BaseConfigurationRepository(ABC):
    """Stable repository contract for configuration-backed monitoring metadata."""

    @abstractmethod
    def load_kpi_configs(self) -> list[KPIConfig]:
        raise NotImplementedError

    @abstractmethod
    @abstractmethod
    def load_validation_rules(self) -> list[KPIValidationRule]:
        raise NotImplementedError

    @abstractmethod
    def load_business_calendar(
        self,
        calendar_code: str | None = None,
        market: str | None = None,
    ) -> list[BusinessCalendarEntry]:
        raise NotImplementedError

    @abstractmethod
    def validate_configuration(self) -> list[str]:
        raise NotImplementedError

    def get_active_kpis(
        self,
        channel: str,
        market: str,
        frequency: str,
        monitoring_date: date,
    ) -> list[KPIConfig]:
        return [
            config
            for config in self.load_kpi_configs()
            if config.active
            and config.channel == channel
            and config.country_cd == market
            and self._supports_frequency(config, frequency)
            and (config.effective_from is None or config.effective_from <= monitoring_date)
            and (config.effective_to is None or config.effective_to >= monitoring_date)
        ]

    @staticmethod
    def _supports_frequency(config: KPIConfig, frequency: str) -> bool:
        if frequency == "Monthly":
            return config.monthly
        if frequency == "Daily":
            return config.daily
        return False

    def get_target_availability(
        self,
        channel: str,
        market: str,
        kpi_id: str,
        frequency: str,
        monitoring_date: date,
    ) -> str:
        for config in self.get_active_kpis(channel, market, frequency, monitoring_date):
            if config.kpi_id == kpi_id:
                if not config.target_availability:
                    raise LookupError(f"No target availability for {channel}/{market}/{kpi_id}/{frequency}")
                return config.target_availability
        raise LookupError(f"No KPI configuration for {channel}/{market}/{kpi_id}/{frequency}")
