from __future__ import annotations

from datetime import date, timedelta
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from dkpi_monitoring.calendar.service import BusinessCalendarService
from dkpi_monitoring.engine.readiness import TargetAvailabilityParser
from models import KPIValidationRule


class KPIValidationService:
    """Evaluates configured KPI validation rules against normalized source data."""

    RESULT_FILE = Path("data/results/kpi_validation_results.csv")
    STANDARD_VALUES_FILE = Path("data/reference/kpi_standard_values.xlsx")
    RESULT_COLUMNS = [
        "record_type",
        "channel",
        "market",
        "kpi_id",
        "kpi_name",
        "frequency",
        "source_table",
        "aggregation_level",
        "aggregation_detail",
        "rule_id",
        "rule_type",
        "rule_order",
        "period",
        "execution_date",
        "execution_timestamp",
        "expected_ready_date",
        "data_ready_time",
        "ready_status",
        "ready_delay_days",
        "status",
        "passed",
        "actual_value",
        "previous_period_value",
        "threshold_percent",
        "standard_value",
        "reason",
    ]

    def __init__(self, standard_values_path: Path | None = None) -> None:
        path = standard_values_path or self.STANDARD_VALUES_FILE
        self.standard_values = self._load_standard_values(path)

    @staticmethod
    def _load_standard_values(path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        values = pd.read_excel(path)
        values.columns = [str(column).strip().lower() for column in values.columns]
        values["frequency"] = values["frequency"].astype(str).str.strip().str.capitalize()
        values["period"] = values["period"].astype(str).str.strip()
        return values

    def validate(
        self,
        rules: list[KPIValidationRule],
        source_data: pd.DataFrame,
        period: date,
        target_availability: str | None = None,
        calendar_service: BusinessCalendarService | None = None,
        execution_timestamp: datetime | None = None,
    ) -> list[dict[str, Any]]:
        execution_timestamp = execution_timestamp or datetime.now().astimezone()
        if not rules:
            return []

        ready_result = self._evaluate_ready_timing(
            rules[0],
            source_data,
            period,
            execution_timestamp,
            target_availability,
            calendar_service,
        )
        if ready_result["ready_status"] == "NOT_DUE":
            return [self._summary_result(rules[0], period, execution_timestamp, "NOT_DUE", ready_result)]

        results: list[dict[str, Any]] = []
        for rule in sorted(rules, key=lambda item: item.rule_order):
            if not rule.enabled:
                continue
            status, actual_value, previous_value, standard_value, reason = self._evaluate_rule(rule, source_data, period)
            results.append(
                {
                    "channel": rule.channel,
                    "market": rule.market,
                    "kpi_id": rule.kpi_id,
                    "kpi_name": rule.kpi_name,
                    "frequency": rule.frequency,
                    "source_table": rule.source_table,
                    "aggregation_level": "Agency",
                    "aggregation_detail": "ALL",
                    "rule_id": rule.rule_id,
                    "rule_type": rule.rule_type,
                    "rule_order": rule.rule_order,
                    "period": period.isoformat(),
                    "execution_date": execution_timestamp.date().isoformat(),
                    "execution_timestamp": execution_timestamp.isoformat(),
                    **ready_result,
                    "status": status,
                    "passed": status == "PASSED",
                    "actual_value": actual_value,
                    "previous_period_value": previous_value,
                    "threshold_percent": rule.threshold_percent,
                    "standard_value": standard_value,
                    "reason": reason,
                }
            )
        final_status = self._final_status(results)
        if results:
            results.append(self._summary_result(rules[0], period, execution_timestamp, final_status, ready_result))
        for result in results:
            result.setdefault("record_type", "RULE")
        return results

    @staticmethod
    def _summary_reason(status: str) -> str:
        reasons = {
            "PASSED": "All enabled validation rules passed",
            "FAILED": "One or more validation rules failed",
            "PREVIOUS_PERIOD_MISSING": "Previous period data is unavailable",
            "STANDARD_VALUE_MISSING": "Standard value is unavailable",
            "NOT_DUE": "Target availability has not been reached; validation skipped",
            "VALIDATION_INCOMPLETE": "Validation could not be completed",
        }
        return reasons[status]

    @staticmethod
    def _summary_result(
        rule: KPIValidationRule,
        period: date,
        execution_timestamp: datetime,
        status: str,
        ready_result: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "record_type": "KPI_SUMMARY",
            "channel": rule.channel,
            "market": rule.market,
            "kpi_id": rule.kpi_id,
            "kpi_name": rule.kpi_name,
            "frequency": rule.frequency,
            "source_table": rule.source_table,
            "aggregation_level": "Agency",
            "aggregation_detail": "ALL",
            "rule_id": "KPI_RESULT",
            "rule_type": "KPI_SUMMARY",
            "rule_order": None,
            "period": period.isoformat(),
            "execution_date": execution_timestamp.date().isoformat(),
            "execution_timestamp": execution_timestamp.isoformat(),
            **ready_result,
            "status": status,
            "passed": status == "PASSED",
            "actual_value": None,
            "previous_period_value": None,
            "threshold_percent": None,
            "standard_value": None,
            "reason": KPIValidationService._summary_reason(status),
        }

    @staticmethod
    def _final_status(results: list[dict[str, Any]]) -> str:
        statuses = {result["status"] for result in results}
        if statuses == {"PASSED"}:
            return "PASSED"
        if "FAILED" in statuses:
            return "FAILED"
        if "STANDARD_VALUE_MISSING" in statuses:
            return "STANDARD_VALUE_MISSING"
        if "PREVIOUS_PERIOD_MISSING" in statuses:
            return "PREVIOUS_PERIOD_MISSING"
        return "VALIDATION_INCOMPLETE"

    def validate_and_save(
        self,
        rules: list[KPIValidationRule],
        source_data: pd.DataFrame,
        period: date,
        output_path: Path | None = None,
        target_availability: str | None = None,
        calendar_service: BusinessCalendarService | None = None,
        execution_timestamp: datetime | None = None,
    ) -> list[dict[str, Any]]:
        execution_timestamp = execution_timestamp or datetime.now().astimezone()
        results = self.validate(rules, source_data, period, target_availability, calendar_service, execution_timestamp)
        path = output_path or self.RESULT_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        new_results = pd.DataFrame(results)
        new_results = new_results.reindex(columns=self.RESULT_COLUMNS)
        if path.exists():
            existing = pd.read_csv(path)
            existing = existing.reindex(columns=self.RESULT_COLUMNS)
            existing = self._normalize_aggregation_level(existing)
            same_run = (
                existing["execution_date"].eq(execution_timestamp.date().isoformat())
                & existing["channel"].eq(rules[0].channel)
                & existing["market"].eq(rules[0].market)
                & existing["kpi_id"].eq(str(rules[0].kpi_id))
                & existing["frequency"].eq(rules[0].frequency)
                & existing["period"].eq(period.isoformat())
            )
            existing = existing.loc[~same_run]
            existing = existing.drop(columns=["kpi_validation_status"], errors="ignore")
            frames = [frame.dropna(axis=1, how="all") for frame in (existing, new_results) if not frame.empty]
            new_results = pd.concat(frames, ignore_index=True).reindex(columns=self.RESULT_COLUMNS)
        self._normalize_aggregation_level(new_results).to_csv(path, index=False)
        return results

    @staticmethod
    def _normalize_aggregation_level(results: pd.DataFrame) -> pd.DataFrame:
        if "aggregation_level" not in results.columns:
            return results
        normalized = results.copy()
        level = normalized["aggregation_level"].astype("string").str.strip()
        normalized.loc[level.str.upper().eq("MARKET"), "aggregation_level"] = "Agency"
        return normalized

    def _evaluate_ready_timing(
        self,
        rule: KPIValidationRule,
        source_data: pd.DataFrame,
        period: date,
        execution_timestamp: datetime,
        target_availability: str | None,
        calendar_service: BusinessCalendarService | None,
    ) -> dict[str, Any]:
        if not target_availability:
            return {
                "expected_ready_date": None,
                "data_ready_time": None,
                "ready_status": "VALIDATION_INCOMPLETE",
                "ready_delay_days": None,
            }
        expected_ready_date = self._calculate_expected_ready_date(
            target_availability,
            rule.market,
            period,
            calendar_service,
        )
        execution_date = execution_timestamp.date()
        if execution_date < expected_ready_date:
            return {
                "expected_ready_date": expected_ready_date.isoformat(),
                "data_ready_time": None,
                "ready_status": "NOT_DUE",
                "ready_delay_days": None,
            }

        period_rows = source_data[source_data["PERIOD"].eq(period.isoformat())]
        kpi_rows = self._filter_kpi_rows(rule, period_rows)
        data_ready_time = self._data_ready_time(kpi_rows, execution_timestamp)
        if data_ready_time is None:
            delay_days = self._delay_days(expected_ready_date, execution_date, target_availability, rule.market, calendar_service)
            return {
                "expected_ready_date": expected_ready_date.isoformat(),
                "data_ready_time": None,
                "ready_status": "DELAYED",
                "ready_delay_days": delay_days,
            }

        ready_date = data_ready_time.date()
        if ready_date <= expected_ready_date:
            return {
                "expected_ready_date": expected_ready_date.isoformat(),
                "data_ready_time": data_ready_time.isoformat(),
                "ready_status": "READY_ON_TIME",
                "ready_delay_days": 0,
            }
        delay_days = self._delay_days(expected_ready_date, ready_date, target_availability, rule.market, calendar_service)
        return {
            "expected_ready_date": expected_ready_date.isoformat(),
            "data_ready_time": data_ready_time.isoformat(),
            "ready_status": "READY_DELAYED",
            "ready_delay_days": delay_days,
        }

    @staticmethod
    def _data_ready_time(kpi_rows: pd.DataFrame, execution_timestamp: datetime) -> datetime | None:
        if kpi_rows.empty:
            return None
        ready_times: list[datetime] = []
        for row in kpi_rows.to_dict("records"):
            create_date = pd.to_datetime(row.get("CREATE_DATE"), errors="coerce")
            update_date = pd.to_datetime(row.get("UPDATE_DATE"), errors="coerce")
            if pd.isna(create_date) and pd.isna(update_date):
                ready_times.append(execution_timestamp)
            elif pd.notna(create_date) and pd.isna(update_date):
                ready_times.append(create_date.to_pydatetime())
            elif pd.notna(create_date) and pd.notna(update_date) and update_date > create_date:
                ready_times.append(update_date.to_pydatetime())
            elif pd.notna(create_date):
                ready_times.append(create_date.to_pydatetime())
            elif pd.notna(update_date):
                ready_times.append(update_date.to_pydatetime())
        return max(ready_times) if ready_times else None

    @staticmethod
    def _calculate_expected_ready_date(
        target_availability: str,
        market: str,
        period: date,
        calendar_service: BusinessCalendarService | None,
    ) -> date:
        parsed = TargetAvailabilityParser.parse(target_availability)
        anchor_date = period
        if parsed["anchor"] == "M":
            anchor_date = (pd.Timestamp(period) + pd.offsets.MonthEnd(0)).date()
        if parsed["unit"] == "BD" and calendar_service is not None:
            return calendar_service.add_business_days(market, anchor_date, parsed["offset"])
        return anchor_date.fromordinal(anchor_date.toordinal() + int(parsed["offset"]))

    @staticmethod
    def _delay_days(
        expected_ready_date: date,
        actual_date: date,
        target_availability: str,
        market: str,
        calendar_service: BusinessCalendarService | None,
    ) -> int:
        parsed = TargetAvailabilityParser.parse(target_availability)
        if parsed["unit"] == "BD" and calendar_service is not None and market in calendar_service._configured_markets:
            current = expected_ready_date
            days = 0
            while current < actual_date:
                current = current.fromordinal(current.toordinal() + 1)
                if calendar_service.is_business_day(market, current):
                    days += 1
            return days
        return max((actual_date - expected_ready_date).days, 0)

    def _evaluate_rule(
        self,
        rule: KPIValidationRule,
        source_data: pd.DataFrame,
        period: date,
    ) -> tuple[str, Any, Any, Any, str]:
        period_rows = source_data[source_data["PERIOD"].eq(period.isoformat())]
        kpi_rows = self._filter_kpi_rows(rule, period_rows)

        if rule.rule_type == "RECORD_EXISTS":
            status = "PASSED" if len(kpi_rows) else "FAILED"
            return status, len(kpi_rows), None, None, "Record exists" if len(kpi_rows) else "No record found"

        if kpi_rows.empty:
            return "FAILED", None, None, None, "No record found"
        value = self._aggregate_value(kpi_rows, rule.value_column)

        if rule.rule_type == "VALUE_NOT_NULL":
            passed = pd.notna(value)
            return ("PASSED" if passed else "FAILED"), value, None, None, "Value is not null" if passed else "Value is null"
        if rule.rule_type == "VALUE_GREATER_THAN_ZERO":
            passed = pd.notna(value) and float(value) > 0
            return ("PASSED" if passed else "FAILED"), value, None, None, "Value is greater than zero" if passed else "Value is not greater than zero"
        if rule.rule_type == "CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT":
            previous_period = pd.Timestamp(period.replace(day=1) - timedelta(days=1)) + pd.offsets.MonthEnd(0)
            previous_rows = self._filter_kpi_rows(
                rule,
                source_data[source_data["PERIOD"].eq(previous_period.date().isoformat())],
            )
            previous_value = self._aggregate_value(previous_rows, rule.value_column)
            if previous_rows.empty or pd.isna(value) or pd.isna(previous_value):
                return "PREVIOUS_PERIOD_MISSING", value, None, None, "Previous period data does not exist or value is unavailable"
            previous_value = float(previous_value)
            if previous_value == 0:
                return "FAILED", value, previous_value, None, "Previous period value is zero"
            change_percent = (float(value) - previous_value) / abs(previous_value) * 100
            passed = abs(change_percent) <= float(rule.threshold_percent)
            return ("PASSED" if passed else "FAILED"), change_percent, previous_value, None, f"Absolute change is {change_percent:.2f}%"
        if rule.rule_type == "DEVIATION_FROM_STANDARD_WITHIN_PERCENT":
            standard_value = self._find_standard_value(rule, period)
            if standard_value is None:
                return "STANDARD_VALUE_MISSING", value, None, None, "Standard value is not configured"
            if pd.isna(value):
                return "FAILED", value, None, standard_value, "Current value is null"
            if standard_value == 0:
                return "FAILED", value, None, standard_value, "Standard value is zero"
            deviation_percent = (float(value) - standard_value) / abs(standard_value) * 100
            passed = abs(deviation_percent) <= float(rule.threshold_percent)
            return ("PASSED" if passed else "FAILED"), deviation_percent, None, standard_value, f"Absolute deviation is {deviation_percent:.2f}%"
        raise ValueError(f"Unsupported validation rule: {rule.rule_type}")

    @staticmethod
    def _filter_kpi_rows(rule: KPIValidationRule, data: pd.DataFrame) -> pd.DataFrame:
        filtered = data[data["ACCOUNT_ID"].astype(str).eq(str(rule.kpi_id))]
        if "BU_CODE" in filtered.columns:
            filtered = filtered[filtered["BU_CODE"].astype(str).eq(rule.market)]
        if "MODE" in filtered.columns:
            mode_prefix = "M" if rule.frequency == "Monthly" else "D"
            filtered = filtered[filtered["MODE"].astype(str).str.upper().str.startswith(mode_prefix)]
        return filtered

    @staticmethod
    def _aggregate_value(rows: pd.DataFrame, value_column: str | None) -> float | None:
        column = value_column if value_column in rows.columns else "VALUE"
        if rows.empty or column not in rows.columns:
            return None
        values = pd.to_numeric(rows[column], errors="coerce")
        total = values.sum(min_count=1)
        return None if pd.isna(total) else float(total)

    @staticmethod
    def sub_channel_breakdown(
        rule: KPIValidationRule,
        source_data: pd.DataFrame,
        period: date,
    ) -> pd.DataFrame:
        period_rows = source_data[source_data["PERIOD"].eq(period.isoformat())]
        rows = KPIValidationService._filter_kpi_rows(rule, period_rows)
        if rows.empty or "DISTRIBUTION_CHANNEL" not in rows.columns:
            return pd.DataFrame()
        return (
            rows.assign(VALUE=pd.to_numeric(rows["VALUE"], errors="coerce"))
            .groupby(["DISTRIBUTION_CHANNEL", "CHANNEL_CODE"], dropna=False, as_index=False)
            .agg(record_count=("ACCOUNT_ID", "count"), total_value=("VALUE", "sum"))
            .rename(columns={"DISTRIBUTION_CHANNEL": "sub_channel", "CHANNEL_CODE": "channel_code"})
        )

    def _find_standard_value(self, rule: KPIValidationRule, period: date) -> float | None:
        if self.standard_values.empty:
            return None
        matches = self.standard_values[
            self.standard_values["market"].eq(rule.market)
            & self.standard_values["kpi_id"].eq(rule.kpi_id)
            & self.standard_values["frequency"].eq(rule.frequency)
            & self.standard_values["period"].eq(period.isoformat())
        ]
        if matches.empty or pd.isna(matches["standard_value"].iloc[0]):
            return None
        return float(matches["standard_value"].iloc[0])
