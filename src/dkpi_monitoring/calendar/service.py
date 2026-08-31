from __future__ import annotations

from datetime import date

from dkpi_monitoring.models import BusinessCalendarConfig


class BusinessCalendarService:
    def __init__(self, calendar_data: list[BusinessCalendarConfig]):
        self.calendar_data = calendar_data
        self._calendar_index = {
            (item.market, item.calendar_date): item.is_business_day
            for item in calendar_data
        }
        self._configured_markets = {item.market for item in calendar_data}

    def is_business_day(self, market: str, value: date) -> bool:
        return self._calendar_index.get((market, value), False)

    def add_business_days(self, market: str, start_date: date, offset: int) -> date:
        if market not in self._configured_markets:
            return self.add_calendar_days(start_date, offset)
        current = start_date
        step = 1 if offset >= 0 else -1
        remaining = abs(offset)
        while remaining:
            current = current.fromordinal(current.toordinal() + step)
            if (market, current) not in self._calendar_index:
                return self.add_calendar_days(start_date, offset)
            if self.is_business_day(market, current):
                remaining -= 1
        return current

    def add_calendar_days(self, start_date: date, offset: int) -> date:
        return start_date.fromordinal(start_date.toordinal() + offset)

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
            item
            for item in self.calendar_data
            if item.market == market
            and date_from <= item.calendar_date <= date_to
        ]
