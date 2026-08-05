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
        kpi_configs = self.config_loader.get_active_kpi_config(channel, market, frequency)
        results: list[KPIReadinessResult] = []

        calendar_configs = self.config_loader.load_business_calendar_configs()
        calendar_service = BusinessCalendarService(calendar_configs)
        evaluator = KPIReadinessEvaluator(calendar_service=calendar_service)

        for kpi_config in kpi_configs:
            ready_rule = self.config_loader.get_ready_rule(
                kpi_config.channel,
                kpi_config.market,
                kpi_config.kpi_name,
                monitoring_date,
            )

            if frequency.lower() == "monthly":
                date_from = monitoring_date.replace(day=1)
                date_to = monitoring_date
            else:
                date_from = monitoring_date
                date_to = monitoring_date

            source_data = self.provider.get_table_data(
                source_table=kpi_config.source_table,
                date_from=date_from,
                date_to=date_to,
                filters={"date_column": kpi_config.date_column},
            )

            result = evaluator.evaluate(kpi_config, ready_rule, source_data, monitoring_date)
            results.append(result)

        self.result_persister.save_results(results)
        return results
