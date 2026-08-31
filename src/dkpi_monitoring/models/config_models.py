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
class BusinessCalendarConfig:
    market: str
    calendar_date: date
    is_business_day: bool


@dataclass
class SourceTableMapping:
    market: str
    source_table_name: str
