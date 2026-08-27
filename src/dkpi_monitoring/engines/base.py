from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from dkpi_monitoring.models import KPIReadinessResult


class MonitoringEngine(ABC):
    """Contract for future monitoring orchestration implementations."""

    @abstractmethod
    def run_monitoring(
        self,
        channel: str,
        market: str,
        frequency: str,
        monitoring_date: date,
    ) -> list[KPIReadinessResult]:
        raise NotImplementedError
