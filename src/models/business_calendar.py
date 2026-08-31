from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class BusinessCalendarEntry(BaseModel):
    calendar_code: str = Field(min_length=1)
    market: str = Field(min_length=1)
    calendar_date: date
    is_business_day: bool
    holiday_name: str | None = None
    day_type: Literal["business_day", "weekend", "public_holiday", "market_holiday"]
