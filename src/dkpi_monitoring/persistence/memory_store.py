from __future__ import annotations

from datetime import date
from typing import Any

from dkpi_monitoring.models import KPIReadinessResult


class InMemoryResultStore:
    def __init__(self) -> None:
        pass

    def save_results(self, results: list[KPIReadinessResult]) -> None:
        raise NotImplementedError

    def load_recent_results(
        self,
        channel: str | None = None,
        market: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[KPIReadinessResult]:
        raise NotImplementedError

    def load_historical_trend(
        self,
        channel: str,
        market: str,
        kpi_name: str,
        window_days: int,
    ) -> list[KPIReadinessResult]:
        raise NotImplementedError
