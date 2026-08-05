from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class KPIConfig:
    channel: str
    market: str
    kpi_name: str
    frequency: str
    source_table: str
    date_column: str
    active: bool


@dataclass
class ReadyRuleConfig:
    channel: str
    market: str
    kpi_name: str
    ready_rule: str
    business_calendar: str
    effective_from: date
    effective_to: date | None


@dataclass
class BusinessCalendarConfig:
    market: str
    calendar_date: date
    is_business_day: bool


@dataclass
class SourceTableMapping:
    market: str
    source_table_name: str
