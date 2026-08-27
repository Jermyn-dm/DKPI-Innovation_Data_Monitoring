from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from dkpi_monitoring.models import (
    BusinessCalendarConfig,
    KPIConfig,
    KPIReadinessResult,
    ReadyRuleConfig,
    SourceTableMapping,
)


class ConfigurationRepository(ABC):
    """Contract for normalized monitoring configuration access."""

    @abstractmethod
    def load_kpi_configs(self) -> list[KPIConfig]:
        raise NotImplementedError

    @abstractmethod
    def load_ready_rule_configs(self) -> list[ReadyRuleConfig]:
        raise NotImplementedError

    @abstractmethod
    def load_business_calendar(
        self,
        market: str,
        date_from: date,
        date_to: date,
    ) -> list[BusinessCalendarConfig]:
        raise NotImplementedError

    @abstractmethod
    def load_source_table_mappings(self) -> list[SourceTableMapping]:
        raise NotImplementedError

    @abstractmethod
    def get_active_kpis(
        self,
        channel: str,
        market: str,
        frequency: str,
        monitoring_date: date,
    ) -> list[KPIConfig]:
        raise NotImplementedError

    @abstractmethod
    def get_ready_rule(
        self,
        channel: str,
        market: str,
        kpi_name: str,
        frequency: str,
        monitoring_date: date,
    ) -> ReadyRuleConfig:
        raise NotImplementedError

    @abstractmethod
    def get_source_mapping(
        self,
        source_table: str,
        market: str,
    ) -> SourceTableMapping:
        raise NotImplementedError

    @abstractmethod
    def validate(self) -> list[Any]:
        raise NotImplementedError


class ResultRepository(ABC):
    """Contract for monitoring result persistence and retrieval."""

    @abstractmethod
    def save_results(self, results: list[KPIReadinessResult]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_results(
        self,
        channel: str | None = None,
        market: str | None = None,
        frequency: str | None = None,
        status: str | None = None,
        monitoring_date: date | None = None,
    ) -> list[KPIReadinessResult]:
        raise NotImplementedError

    @abstractmethod
    def get_result_history(
        self,
        channel: str,
        market: str,
        kpi_name: str,
        frequency: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[KPIReadinessResult]:
        raise NotImplementedError

    @abstractmethod
    def get_results_by_execution(self, execution_id: str) -> list[KPIReadinessResult]:
        raise NotImplementedError
