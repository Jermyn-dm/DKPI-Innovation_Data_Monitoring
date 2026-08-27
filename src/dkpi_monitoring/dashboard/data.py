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
        raise NotImplementedError

    def get_channel_metrics(self, channel: str | None = None) -> list[ChannelSummary]:
        raise NotImplementedError

    def get_market_metrics(self, market: str | None = None) -> list[MarketSummary]:
        raise NotImplementedError

    def get_kpi_metrics(
        self,
        channel: str | None = None,
        market: str | None = None,
        status: str | None = None,
    ) -> list[KPIMetrics]:
        raise NotImplementedError

    def get_trend_data(
        self,
        channel: str | None = None,
        market: str | None = None,
        kpi_name: str | None = None,
        window_days: int = 30,
    ) -> list[TrendPoint]:
        raise NotImplementedError
