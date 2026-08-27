from __future__ import annotations

from datetime import date
from dkpi_monitoring.calendar.service import BusinessCalendarService
from dkpi_monitoring.models import KPIConfig, KPIReadinessResult, ReadyRuleConfig


class ReadyRuleParser:
    @classmethod
    def parse(cls, expression: str) -> dict[str, str | int]:
        raise NotImplementedError


class KPIReadinessEvaluator:
    def __init__(self, calendar_service: BusinessCalendarService):
        self.calendar_service = calendar_service

    def evaluate(
        self,
        kpi_config: KPIConfig,
        ready_rule: ReadyRuleConfig,
        source_data: pd.DataFrame,
        reference_date: date,
    ) -> KPIReadinessResult:
        raise NotImplementedError

    def _calculate_expected_ready_date(
        self,
        rule: str,
        market: str,
        reference_date: date,
    ) -> date | None:
        raise NotImplementedError

    def _determine_actual_ready_date(self, source_data: pd.DataFrame, date_column: str) -> date | None:
        raise NotImplementedError

    def _determine_status(
        self,
        source_data: pd.DataFrame,
        actual_date: date | None,
        expected_date: date | None,
    ) -> tuple[str, str | None]:
        raise NotImplementedError
