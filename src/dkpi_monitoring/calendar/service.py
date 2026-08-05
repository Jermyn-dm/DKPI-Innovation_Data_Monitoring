from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

import pandas as pd

from dkpi_monitoring.models import BusinessCalendarConfig


class BusinessCalendarService:
    def __init__(self, calendar_data: list[BusinessCalendarConfig]):
        self.calendar_index = {
            (item.market, item.calendar_date): item.is_business_day
            for item in calendar_data
        }

    def is_business_day(self, market: str, value: date) -> bool:
        return self.calendar_index.get((market, value), False)

    def add_business_days(self, market: str, start_date: date, offset: int) -> date:
        current = start_date
        step = 1 if offset >= 0 else -1
        remaining = abs(offset)
        while remaining > 0:
            current = current + timedelta(days=step)
            if self.is_business_day(market, current):
                remaining -= 1
        return current

    def add_calendar_days(self, start_date: date, offset: int) -> date:
        return start_date + timedelta(days=offset)

    def next_business_day(self, market: str, start_date: date) -> date:
        return self.add_business_days(market, start_date, 1)

    def previous_business_day(self, market: str, start_date: date) -> date:
        return self.add_business_days(market, start_date, -1)

    def get_calendar_range(
        self,
        market: str,
        date_from: date,
        date_to: date,
    ) -> list[BusinessCalendarConfig]:
        return [
            BusinessCalendarConfig(market=market, calendar_date=dt, is_business_day=self.is_business_day(market, dt))
            for dt in pd.date_range(date_from, date_to).date
        ]
