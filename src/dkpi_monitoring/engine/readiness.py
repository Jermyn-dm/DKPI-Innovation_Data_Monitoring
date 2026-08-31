from __future__ import annotations

from datetime import date
import re
import pandas as pd

from dkpi_monitoring.calendar.service import BusinessCalendarService
from dkpi_monitoring.models import KPIConfig, KPIReadinessResult


class TargetAvailabilityParser:
    RULE_PATTERN = re.compile(r"^(M|D|T)\+(\d+)(BD|CD)$", re.IGNORECASE)
    T_RULE_PATTERN = re.compile(r"^T\+((?:BD|CD))(\d+)$", re.IGNORECASE)

    @classmethod
    def parse(cls, expression: str) -> dict[str, str | int]:
        value = expression.strip()
        match = cls.RULE_PATTERN.fullmatch(value)
        if not match:
            t_match = cls.T_RULE_PATTERN.fullmatch(value)
            if t_match:
                unit, offset = t_match.groups()
                return {"anchor": "T", "offset": int(offset), "unit": unit.upper()}
        if not match:
            raise ValueError(f"Unsupported target availability: {expression}")
        anchor, offset, unit = match.groups()
        return {"anchor": anchor.upper(), "offset": int(offset), "unit": unit.upper()}


class KPIReadinessEvaluator:
    def __init__(self, calendar_service: BusinessCalendarService):
        self.calendar_service = calendar_service

    def evaluate(
        self,
        kpi_config: KPIConfig,
        target_availability: str,
        source_data: pd.DataFrame,
        reference_date: date,
    ) -> KPIReadinessResult:
        expected_date = self._calculate_expected_ready_date(
            target_availability,
            kpi_config.country_cd,
            reference_date,
        )
        raise NotImplementedError

    def _calculate_expected_ready_date(
        self,
        rule: str,
        market: str,
        reference_date: date,
    ) -> date | None:
        parsed = TargetAvailabilityParser.parse(rule)
        anchor_date = reference_date
        if parsed["anchor"] == "M":
            anchor_date = (pd.Timestamp(reference_date) + pd.offsets.MonthEnd(0)).date()
        if parsed["anchor"] == "T":
            anchor_date = reference_date
        if parsed["unit"] == "BD":
            return self.calendar_service.add_business_days(market, anchor_date, parsed["offset"])
        return self.calendar_service.add_calendar_days(anchor_date, parsed["offset"])

    def _determine_actual_ready_date(self, source_data: pd.DataFrame, date_column: str) -> date | None:
        raise NotImplementedError

    def _determine_status(
        self,
        source_data: pd.DataFrame,
        actual_date: date | None,
        expected_date: date | None,
    ) -> tuple[str, str | None]:
        raise NotImplementedError
