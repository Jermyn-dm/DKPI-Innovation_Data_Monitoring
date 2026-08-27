from __future__ import annotations

from datetime import date
from typing import Any

from dkpi_monitoring.config.loader import ConfigLoader
from dkpi_monitoring.models import KPIReadinessResult
from dkpi_monitoring.providers.base import DataProvider
from dkpi_monitoring.engine.readiness import KPIReadinessEvaluator
from dkpi_monitoring.calendar.service import BusinessCalendarService


class MonitoringOrchestrator:
    def __init__(
        self,
        provider: DataProvider,
        config_loader: ConfigLoader,
        result_persister: Any,
    ):
        self.provider = provider
        self.config_loader = config_loader
        self.result_persister = result_persister

    def run_monitoring(
        self,
        channel: str,
        market: str,
        frequency: str,
        monitoring_date: date,
    ) -> list[KPIReadinessResult]:
        raise NotImplementedError
