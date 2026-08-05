from __future__ import annotations

from datetime import date
import re

import pandas as pd

from dkpi_monitoring.calendar.service import BusinessCalendarService
from dkpi_monitoring.models import KPIConfig, KPIReadinessResult, ReadyRuleConfig


class ReadyRuleParser:
    RULE_PATTERN = re.compile(r"^(M|D)\+(\d+)(BD|CD)$", re.IGNORECASE)

    @classmethod
    def parse(cls, expression: str) -> dict[str, str | int]:
        match = cls.RULE_PATTERN.match(expression.strip())
        if not match:
            raise ValueError(f"Unsupported ready rule expression: {expression}")
        base, offset, unit = match.groups()
        return {
            "base": base.upper(),
            "offset": int(offset),
            "unit": unit.upper(),
        }


class KPIReadinessEvaluator:
    def __init__(self, calendar_service: BusinessCalendarService):
        self.calendar_service = calendar_service

    def evaluate(
        self,
        kpi_config: KPIConfig,
        ready_rule: ReadyRuleConfig,
        source_data: pd.DataFrame,
        reference_date: date,
    ) -> KPIReadinessResult:
        expected_date = self._calculate_expected_ready_date(
            ready_rule.ready_rule,
            kpi_config.market,
            reference_date,
        )
        actual_date = self._determine_actual_ready_date(source_data, kpi_config.date_column)
        status, reason = self._determine_status(source_data, actual_date, expected_date)
        return KPIReadinessResult(
            channel=kpi_config.channel,
            market=kpi_config.market,
            kpi_name=kpi_config.kpi_name,
            frequency=kpi_config.frequency,
            expected_ready_date=expected_date,
            actual_ready_date=actual_date,
            status=status,
            missing_reason=reason,
            record_count=len(source_data),
            evaluation_details={
                "rule": ready_rule.ready_rule,
                "actual_rows": str(len(source_data)),
            },
        )

    def _calculate_expected_ready_date(
        self,
        rule: str,
        market: str,
        reference_date: date,
    ) -> date | None:
        parsed = ReadyRuleParser.parse(rule)
        if parsed["base"] == "M":
            month_end = reference_date.replace(day=1) + pd.offsets.MonthEnd(0)
            if parsed["unit"] == "BD":
                return self.calendar_service.add_business_days(market, month_end, parsed["offset"])
            return self.calendar_service.add_calendar_days(month_end, parsed["offset"])

        if parsed["base"] == "D":
            if parsed["unit"] == "BD":
                return self.calendar_service.add_business_days(market, reference_date, parsed["offset"])
            return self.calendar_service.add_calendar_days(reference_date, parsed["offset"])

        return None

    def _determine_actual_ready_date(self, source_data: pd.DataFrame, date_column: str) -> date | None:
        if source_data.empty or date_column not in source_data.columns:
            return None
        values = pd.to_datetime(source_data[date_column], errors="coerce")
        if values.isna().all():
            return None
        return values.max().date()

    def _determine_status(
        self,
        source_data: pd.DataFrame,
        actual_date: date | None,
        expected_date: date | None,
    ) -> tuple[str, str | None]:
        if source_data.empty:
            return "Missing", "No records found"
        if actual_date is None:
            return "Missing", "Actual date not available"
        if expected_date is None:
            return "Missing", "Unable to calculate expected ready date"
        if actual_date <= expected_date:
            return "Ready", None
        return "Late", f"Actual ready date {actual_date} is after expected {expected_date}"
