from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from dkpi_monitoring.models import (
    ChannelSummary,
    KPIMetrics,
    MarketSummary,
    MonitoringSummary,
    TrendPoint,
)


class DashboardDataProvider:
    def __init__(self, result_store: Any):
        self.result_store = result_store

    def get_overview_metrics(self) -> MonitoringSummary:
        results = self.result_store.load_recent_results()
        total = len(results)
        ready = sum(1 for result in results if result.status == "Ready")
        late = sum(1 for result in results if result.status == "Late")
        missing = sum(1 for result in results if result.status == "Missing")
        readiness_pct = (ready / total * 100) if total else 0.0
        return MonitoringSummary(
            total_kpis=total,
            ready_count=ready,
            late_count=late,
            missing_count=missing,
            readiness_pct=readiness_pct,
        )

    def get_channel_metrics(self, channel: str | None = None) -> list[ChannelSummary]:
        results = self.result_store.load_recent_results(channel=channel)
        summary: dict[str, dict[str, int]] = defaultdict(lambda: {"ready": 0, "late": 0, "missing": 0, "total": 0})
        for result in results:
            bucket = summary[result.channel]
            bucket["total"] += 1
            bucket[result.status.lower()] += 1

        return [
            ChannelSummary(
                channel=channel_name,
                readiness_pct=(values["ready"] / values["total"] * 100) if values["total"] else 0.0,
                late_count=values["late"],
                missing_count=values["missing"],
            )
            for channel_name, values in summary.items()
        ]

    def get_market_metrics(self, market: str | None = None) -> list[MarketSummary]:
        results = self.result_store.load_recent_results(market=market)
        summary: dict[str, dict[str, int | str]] = defaultdict(lambda: {"ready": 0, "late": 0, "missing": 0, "total": 0, "latest_status": ""})
        for result in results:
            bucket = summary[result.market]
            bucket["total"] += 1
            bucket[result.status.lower()] += 1
            bucket["latest_status"] = result.status

        return [
            MarketSummary(
                market=market_name,
                kpi_count=values["total"],
                readiness_pct=(values["ready"] / values["total"] * 100) if values["total"] else 0.0,
                latest_status=values["latest_status"],
            )
            for market_name, values in summary.items()
        ]

    def get_kpi_metrics(
        self,
        channel: str | None = None,
        market: str | None = None,
        status: str | None = None,
    ) -> list[KPIMetrics]:
        results = self.result_store.load_recent_results(channel=channel, market=market)
        if status:
            results = [result for result in results if result.status == status]
        return [
            KPIMetrics(
                kpi_name=result.kpi_name,
                expected_ready_date=result.expected_ready_date,
                actual_ready_date=result.actual_ready_date,
                status=result.status,
            )
            for result in results
        ]

    def get_trend_data(
        self,
        channel: str | None = None,
        market: str | None = None,
        kpi_name: str | None = None,
        window_days: int = 30,
    ) -> list[TrendPoint]:
        start_date = date.today() - timedelta(days=window_days)
        results = self.result_store.load_recent_results(channel=channel, market=market, date_from=start_date)
        if kpi_name:
            results = [result for result in results if result.kpi_name == kpi_name]

        trend: dict[date, dict[str, int]] = defaultdict(lambda: {"ready": 0, "late": 0, "missing": 0, "total": 0})
        for result in results:
            point_date = result.expected_ready_date or date.today()
            bucket = trend[point_date]
            bucket["total"] += 1
            bucket[result.status.lower()] += 1

        return [
            TrendPoint(
                date=point_date,
                readiness_pct=(values["ready"] / values["total"] * 100) if values["total"] else 0.0,
                late_count=values["late"],
                missing_count=values["missing"],
            )
            for point_date, values in sorted(trend.items())
        ]
