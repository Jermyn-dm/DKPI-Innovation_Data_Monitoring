from __future__ import annotations

from datetime import date
from typing import Any

from dkpi_monitoring.models import KPIReadinessResult


class InMemoryResultStore:
    def __init__(self) -> None:
        self._results: list[KPIReadinessResult] = []

    def save_results(self, results: list[KPIReadinessResult]) -> None:
        self._results.extend(results)

    def load_recent_results(
        self,
        channel: str | None = None,
        market: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[KPIReadinessResult]:
        return [
            result
            for result in self._results
            if (channel is None or result.channel == channel)
            and (market is None or result.market == market)
            and (date_from is None or (result.expected_ready_date and result.expected_ready_date >= date_from))
            and (date_to is None or (result.expected_ready_date and result.expected_ready_date <= date_to))
        ]

    def load_historical_trend(
        self,
        channel: str,
        market: str,
        kpi_name: str,
        window_days: int,
    ) -> list[KPIReadinessResult]:
        return [
            result
            for result in self._results
            if result.channel == channel
            and result.market == market
            and result.kpi_name == kpi_name
        ]
