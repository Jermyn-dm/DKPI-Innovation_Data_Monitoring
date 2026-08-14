from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class KPIReadinessResult:
    channel: str
    market: str
    kpi_name: str
    frequency: str
    expected_ready_date: date | None
    actual_ready_date: date | None
    status: str
    missing_reason: str | None
    record_count: int | None
    evaluation_details: dict[str, str] | None


@dataclass
class MonitoringSummary:
    total_kpis: int
    ready_count: int
    late_count: int
    missing_count: int
    readiness_pct: float


@dataclass
class ChannelSummary:
    channel: str
    readiness_pct: float
    late_count: int
    missing_count: int


@dataclass
class MarketSummary:
    market: str
    kpi_count: int
    readiness_pct: float
    latest_status: str


@dataclass
class KPIMetrics:
    kpi_name: str
    expected_ready_date: date | None
    actual_ready_date: date | None
    status: str


@dataclass
class TrendPoint:
    date: date
    readiness_pct: float
    late_count: int
    missing_count: int
