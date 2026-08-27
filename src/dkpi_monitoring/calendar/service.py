from __future__ import annotations

from datetime import date

from dkpi_monitoring.models import BusinessCalendarConfig


class BusinessCalendarService:
    def __init__(self, calendar_data: list[BusinessCalendarConfig]):
        self.calendar_data = calendar_data

    def is_business_day(self, market: str, value: date) -> bool:
        raise NotImplementedError

    def add_business_days(self, market: str, start_date: date, offset: int) -> date:
        raise NotImplementedError

    def add_calendar_days(self, start_date: date, offset: int) -> date:
        raise NotImplementedError

    def next_business_day(self, market: str, start_date: date) -> date:
        raise NotImplementedError

    def previous_business_day(self, market: str, start_date: date) -> date:
        raise NotImplementedError

    def get_calendar_range(
        self,
        market: str,
        date_from: date,
        date_to: date,
    ) -> list[BusinessCalendarConfig]:
        raise NotImplementedError
