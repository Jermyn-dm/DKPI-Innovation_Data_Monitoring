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
    KPI_MAPPING_FILE = Path("configs/agency_kpi_mapping.xlsx")
    COMPARISON_TOLERANCE = 0.00001
    SUB_CHANNEL_MARKETS = {"ID", "SG"}
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
        "baseline_source",
        "comparison_source",
        "baseline_value",
        "comparison_value",
        "difference_value",
        "comparison_level",
        "reason",
    ]

    def __init__(
        self,
        standard_values_path: Path | None = None,
        comparison_data: dict[str, pd.DataFrame] | None = None,
        kpi_mapping_path: Path | None = None,
    ) -> None:
        path = standard_values_path or self.STANDARD_VALUES_FILE
        self.standard_values = self._load_standard_values(path)
        mapping_path = kpi_mapping_path or self.KPI_MAPPING_FILE
        self.kpi_mapping = self._load_kpi_mapping(mapping_path)
        comparison_data = comparison_data or {}
        self.comparison_data = {
            source: self._normalize_comparison_source(source, data)
            for source, data in comparison_data.items()
        }

    @staticmethod
    def _load_standard_values(path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        values = pd.read_excel(path)
        values.columns = [str(column).strip().lower() for column in values.columns]
        values["frequency"] = values["frequency"].astype(str).str.strip().str.capitalize()
        values["period"] = values["period"].astype(str).str.strip()
        return values

    @staticmethod
    def _load_kpi_mapping(path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame(columns=["kpi_id", "anaplan_kpi", "pbi_kpi"])
        mapping = pd.read_excel(path)
        mapping.columns = [str(column).strip().lower() for column in mapping.columns]
        mapping["kpi_id"] = mapping["kpi_id"].astype(str).str.strip()
        for column in ("anaplan_kpi", "pbi_kpi"):
            mapping[column] = mapping[column].astype(str).str.strip()
        return mapping

    @staticmethod
    def _normalize_text_key(value: Any) -> str:
        return " ".join(str(value).strip().casefold().split())

    @classmethod
    def _normalize_unit(cls, value: Any, market: str | None = None) -> str:
        unit = str(value).strip()
        mappings = {
            "China": "CN",
            "Singapore": "SG",
            "Indonesia": "ID",
            "Hong Kong": "HK",
            "Vietnam": "VN",
            "Cambodia": "KH",
            "Myanmar": "MM",
            "Malaysia": "MY",
            "Philippines": "PH",
            "Japan": "JP",
            "MAG": "SG-MAG",
            "MFA": "SG-MFA",
            "SG-MAG": "SG-MAG",
            "SG-MFA": "SG-MFA",
            "GA": "ID-GA",
            "BRANCH": "ID-BRANCH",
            "ID-GA": "ID-GA",
            "ID-BRANCH": "ID-BRANCH",
        }
        normalized = mappings.get(unit, unit)
        if market == "SG" and normalized == "SG":
            return "SG"
        if market == "ID" and normalized == "ID":
            return "ID"
        return normalized

    @staticmethod
    def _parse_comparison_period(value: Any) -> str:
        text = str(value).strip()
        daily_period = pd.to_datetime(text, format="%d %b %y", errors="coerce")
        if pd.notna(daily_period):
            return daily_period.date().isoformat()
        monthly_period = pd.to_datetime(text, format="%b %y", errors="coerce")
        if pd.notna(monthly_period):
            return monthly_period.to_period("M").to_timestamp("M").date().isoformat()
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return "NaT"
        return parsed.date().isoformat()

    @staticmethod
    def _pbi_periods(data: pd.DataFrame) -> pd.Series:
        parsed = pd.to_datetime(data["timestamp"], errors="coerce")
        is_daily = data.get("Source", pd.Series(index=data.index, dtype=object)).astype(str).str.contains(
            "Daily",
            case=False,
            na=False,
        )
        return parsed.where(is_daily, parsed.dt.to_period("M").dt.to_timestamp("M")).dt.date.astype(str)

    def _normalize_comparison_source(self, source: str, data: pd.DataFrame) -> pd.DataFrame:
        source = source.upper()
        if source == "ANAPLAN":
            normalized = data.iloc[6:, :4].copy()
            second_column = normalized.iloc[:, 1].astype(str).str.strip()
            second_column_is_period = (
                pd.to_datetime(second_column, format="%d %b %y", errors="coerce").notna()
                | pd.to_datetime(second_column, format="%b %y", errors="coerce").notna()
            ).mean() > 0.5
            if second_column_is_period:
                normalized.columns = ["unit", "period_label", "kpi_name", "comparison_value"]
            else:
                normalized.columns = ["unit", "kpi_name", "period_label", "comparison_value"]
            normalized["period"] = normalized["period_label"].map(self._parse_comparison_period)
            normalized["unit"] = normalized["unit"].map(self._normalize_unit)
            mapping_column = "anaplan_kpi"
        elif source == "PBI":
            normalized = data.copy()
            normalized = normalized.rename(
                columns={
                    "KPI": "kpi_name",
                    "Line Items": "kpi_name",
                    "L2 Agency_Channel: Code": "unit",
                    "Value": "comparison_value",
                    "Timestamp": "timestamp",
                }
            )
            required_columns = {"kpi_name", "unit", "comparison_value", "timestamp"}
            if not required_columns.issubset(normalized.columns):
                return pd.DataFrame(columns=["unit", "kpi_id", "period", "comparison_value"])
            normalized["period"] = self._pbi_periods(normalized)
            normalized["unit"] = normalized["unit"].map(self._normalize_unit)
            mapping_column = "pbi_kpi"
        elif source == "OVERRIDE_TRACKER":
            normalized = data.copy()
            normalized.columns = [str(column).strip().lower() for column in normalized.columns]
            required_columns = {"bu", "distribution_channel", "period", "account_id", "cy(override)", "granularity", "status"}
            if not required_columns.issubset(normalized.columns):
                return pd.DataFrame(columns=["unit", "kpi_id", "frequency", "period", "override_value"])
            normalized = normalized.loc[
                normalized["cy(override)"].notna()
                & normalized["status"].astype(str).str.strip().str.casefold().eq("completed")
            ].copy()
            normalized["period"] = (
                pd.to_datetime(normalized["period"], errors="coerce")
                .dt.to_period("M")
                .dt.to_timestamp("M")
                .dt.date.astype(str)
            )
            normalized["market"] = normalized["bu"].astype(str).str.strip().replace(
                {
                    "China": "CN",
                    "Singapore": "SG",
                    "Indonesia": "ID",
                    "Hong Kong": "HK",
                    "Vietnam": "VN",
                    "Cambodia": "KH",
                    "Myanmar": "MM",
                    "Malaysia": "MY",
                    "Philippines": "PH",
                    "Japan": "JP",
                }
            )
            normalized["unit"] = normalized.apply(
                lambda row: self._normalize_unit(row["distribution_channel"], row["market"]),
                axis=1,
            )
            normalized.loc[~normalized["market"].isin(self.SUB_CHANNEL_MARKETS), "unit"] = normalized["market"]
            normalized.loc[
                normalized["market"].eq("SG") & normalized["unit"].eq("Agency"), "unit"
            ] = "SG"
            normalized["kpi_id"] = normalized["account_id"].astype(str).str.strip()
            normalized["frequency"] = normalized["granularity"].astype(str).str.strip().str.capitalize()
            normalized["override_value"] = pd.to_numeric(normalized["cy(override)"], errors="coerce")
            key_columns = ["unit", "kpi_id", "frequency", "period"]
            normalized = normalized.dropna(subset=["override_value", "period"])
            return (
                normalized.groupby(key_columns, as_index=False)["override_value"]
                .agg(lambda values: values.iloc[0] if values.nunique() == 1 else float("nan"))
                .dropna(subset=["override_value"])
            )
        else:
            raise ValueError(f"Unsupported comparison source: {source}")
        normalized["kpi_name"] = normalized["kpi_name"].astype(str).str.strip()
        normalized["comparison_value"] = pd.to_numeric(normalized["comparison_value"], errors="coerce")
        normalized["kpi_name_key"] = normalized["kpi_name"].map(self._normalize_text_key)
        mapping = self.kpi_mapping[["kpi_id", mapping_column]].copy()
        mapping["kpi_name_key"] = mapping[mapping_column].map(self._normalize_text_key)
        normalized = normalized.merge(
            mapping[["kpi_id", "kpi_name_key"]],
            on="kpi_name_key",
            how="inner",
        )
        return normalized.groupby(["unit", "kpi_id", "period"], as_index=False)["comparison_value"].sum(min_count=1)

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
            record_exists_results = self._record_exists_results(
                rules,
                source_data,
                period,
                execution_timestamp,
                ready_result,
            )
            if not any(result["status"] == "PASSED" for result in record_exists_results):
                return [*record_exists_results, self._summary_result(rules[0], period, execution_timestamp, "PASSED", ready_result)]

        results: list[dict[str, Any]] = []
        for rule in sorted(rules, key=lambda item: item.rule_order):
            if not rule.enabled:
                continue
            status, actual_value, previous_value, standard_value, reason, comparison = self._evaluate_rule(rule, source_data, period)
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
                    **comparison,
                    "reason": reason,
                }
            )
        final_status = self._final_status(results)
        if results:
            results.append(self._summary_result(rules[0], period, execution_timestamp, final_status, ready_result))
        for result in results:
            result.setdefault("record_type", "RULE")
        return results

    def _record_exists_results(
        self,
        rules: list[KPIValidationRule],
        source_data: pd.DataFrame,
        period: date,
        execution_timestamp: datetime,
        ready_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for rule in sorted(rules, key=lambda item: item.rule_order):
            if not rule.enabled or rule.rule_type != "RECORD_EXISTS":
                continue
            status, actual_value, previous_value, standard_value, reason, comparison = self._evaluate_rule(rule, source_data, period)
            results.append(
                {
                    "record_type": "RULE",
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
                    **comparison,
                    "reason": reason,
                }
            )
        return results

    @staticmethod
    def _summary_reason(status: str) -> str:
        reasons = {
            "PASSED": "All enabled validation rules passed",
            "FAILED": "One or more validation rules failed",
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
            "baseline_source": None,
            "comparison_source": None,
            "baseline_value": None,
            "comparison_value": None,
            "difference_value": None,
            "comparison_level": None,
            "reason": KPIValidationService._summary_reason(status),
        }

    @staticmethod
    def _final_status(results: list[dict[str, Any]]) -> str:
        statuses = {result["status"] for result in results}
        if statuses == {"PASSED"}:
            return "PASSED"
        return "FAILED"

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
            existing = self._read_existing_results(path)
            existing = existing.reindex(columns=self.RESULT_COLUMNS)
            existing = self._normalize_aggregation_level(existing)
            existing = self._normalize_status(existing)
            existing = self._normalize_ready_status(existing)
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
        new_results = self._normalize_aggregation_level(new_results)
        new_results = self._normalize_status(new_results)
        self._normalize_ready_status(new_results).to_csv(path, index=False)
        return results

    @classmethod
    def _read_existing_results(cls, path: Path) -> pd.DataFrame:
        try:
            return pd.read_csv(path)
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=cls.RESULT_COLUMNS)
        except pd.errors.ParserError:
            return pd.read_csv(path, names=cls.RESULT_COLUMNS, header=0, on_bad_lines="skip")

    @staticmethod
    def _normalize_aggregation_level(results: pd.DataFrame) -> pd.DataFrame:
        if "aggregation_level" not in results.columns:
            return results
        normalized = results.copy()
        level = normalized["aggregation_level"].astype("string").str.strip()
        normalized.loc[level.str.upper().eq("MARKET"), "aggregation_level"] = "Agency"
        return normalized

    @staticmethod
    def _normalize_status(results: pd.DataFrame) -> pd.DataFrame:
        if "status" not in results.columns:
            return results
        normalized = results.copy()
        normalized.loc[~normalized["status"].isin(["PASSED", "FAILED"]), "status"] = "FAILED"
        normalized["passed"] = normalized["status"].eq("PASSED")
        return normalized

    @staticmethod
    def _normalize_ready_status(results: pd.DataFrame) -> pd.DataFrame:
        if "ready_status" not in results.columns:
            return results
        normalized = results.copy()
        normalized.loc[normalized["ready_status"].eq("DELAYED"), "ready_status"] = "MISSING"
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
        period_rows = source_data[source_data["PERIOD"].eq(period.isoformat())]
        kpi_rows = self._filter_kpi_rows(rule, period_rows)
        data_ready_time = self._data_ready_time(kpi_rows, execution_timestamp)
        if execution_date < expected_ready_date:
            if data_ready_time is not None:
                return {
                    "expected_ready_date": expected_ready_date.isoformat(),
                    "data_ready_time": data_ready_time.isoformat(),
                    "ready_status": "READY_EARLY",
                    "ready_delay_days": 0,
                }
            return {
                "expected_ready_date": expected_ready_date.isoformat(),
                "data_ready_time": None,
                "ready_status": "NOT_DUE",
                "ready_delay_days": None,
            }

        if data_ready_time is None:
            delay_days = self._delay_days(expected_ready_date, execution_date, target_availability, rule.market, calendar_service)
            return {
                "expected_ready_date": expected_ready_date.isoformat(),
                "data_ready_time": None,
                "ready_status": "MISSING",
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
    ) -> tuple[str, Any, Any, Any, str, dict[str, Any]]:
        period_rows = source_data[source_data["PERIOD"].eq(period.isoformat())]
        kpi_rows = self._filter_kpi_rows(rule, period_rows)

        if rule.rule_type == "RECORD_EXISTS":
            status = "PASSED" if len(kpi_rows) else "FAILED"
            return status, len(kpi_rows), None, None, "Record exists" if len(kpi_rows) else "No record found", {}

        if kpi_rows.empty:
            return "FAILED", None, None, None, "No record found", {}
        value = self._aggregate_value(kpi_rows, rule.value_column)

        if rule.rule_type == "VALUE_NOT_NULL":
            passed = pd.notna(value)
            return ("PASSED" if passed else "FAILED"), value, None, None, "Value is not null" if passed else "Value is null", {}
        if rule.rule_type == "VALUE_GREATER_THAN_ZERO":
            passed = pd.notna(value) and float(value) > 0
            return ("PASSED" if passed else "FAILED"), value, None, None, "Value is greater than zero" if passed else "Value is not greater than zero", {}
        if rule.rule_type == "CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT":
            previous_period = pd.Timestamp(period.replace(day=1) - timedelta(days=1)) + pd.offsets.MonthEnd(0)
            previous_rows = self._filter_kpi_rows(
                rule,
                source_data[source_data["PERIOD"].eq(previous_period.date().isoformat())],
            )
            previous_value = self._aggregate_value(previous_rows, rule.value_column)
            if previous_rows.empty or pd.isna(value) or pd.isna(previous_value):
                return "FAILED", value, None, None, "Previous period data does not exist or value is unavailable", {}
            previous_value = float(previous_value)
            if previous_value == 0:
                return "FAILED", value, previous_value, None, "Previous period value is zero", {}
            change_percent = (float(value) - previous_value) / abs(previous_value) * 100
            passed = abs(change_percent) <= float(rule.threshold_percent)
            return ("PASSED" if passed else "FAILED"), change_percent, previous_value, None, f"Absolute change is {change_percent:.2f}%", {}
        if rule.rule_type == "DEVIATION_FROM_STANDARD_WITHIN_PERCENT":
            standard_value = self._find_standard_value(rule, period)
            if standard_value is None:
                return "FAILED", value, None, None, "Standard value is not configured", {}
            if pd.isna(value):
                return "FAILED", value, None, standard_value, "Current value is null", {}
            if standard_value == 0:
                return "FAILED", value, None, standard_value, "Standard value is zero", {}
            deviation_percent = (float(value) - standard_value) / abs(standard_value) * 100
            passed = abs(deviation_percent) <= float(rule.threshold_percent)
            return ("PASSED" if passed else "FAILED"), deviation_percent, None, standard_value, f"Absolute deviation is {deviation_percent:.2f}%", {}
        if rule.rule_type in {"EDL_MATCH_ANAPLAN", "EDL_MATCH_PBI"}:
            return self._evaluate_source_comparison(rule, kpi_rows, period)
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

    def _evaluate_source_comparison(
        self,
        rule: KPIValidationRule,
        edl_rows: pd.DataFrame,
        period: date,
    ) -> tuple[str, Any, Any, Any, str, dict[str, Any]]:
        source = "ANAPLAN" if rule.rule_type == "EDL_MATCH_ANAPLAN" else "PBI"
        comparison_data = self.comparison_data.get(source)
        base_metadata = {
            "baseline_source": "EDL",
            "comparison_source": source,
            "baseline_value": None,
            "comparison_value": None,
            "difference_value": None,
            "comparison_level": "SUB_CHANNEL" if rule.market in self.SUB_CHANNEL_MARKETS else "AGENCY",
        }
        if comparison_data is None or comparison_data.empty:
            return "FAILED", None, None, None, f"{source} comparison data is unavailable", base_metadata

        edl_rows = edl_rows.copy()
        if rule.market in self.SUB_CHANNEL_MARKETS and "CHANNEL_CODE" in edl_rows.columns:
            edl_rows["unit"] = edl_rows["CHANNEL_CODE"].map(lambda value: self._normalize_unit(value, rule.market))
        else:
            edl_rows["unit"] = rule.market
        edl_rows["VALUE"] = pd.to_numeric(edl_rows[rule.value_column or "VALUE"], errors="coerce")
        edl_values = edl_rows.groupby("unit", as_index=False)["VALUE"].sum(min_count=1)
        comparison_values = comparison_data[
            comparison_data["kpi_id"].astype(str).eq(str(rule.kpi_id))
            & comparison_data["period"].eq(period.isoformat())
            & comparison_data["unit"].isin(edl_values["unit"])
        ]
        joined = edl_values.merge(comparison_values, on="unit", how="left")
        if joined.empty or joined["VALUE"].isna().any() or joined["comparison_value"].isna().any():
            missing_units = joined.loc[joined["comparison_value"].isna(), "unit"].dropna().astype(str).tolist()
            missing_description = ", ".join(missing_units) or "required comparison unit"
            metadata = {
                **base_metadata,
                "baseline_value": float(joined["VALUE"].sum(min_count=1)) if not joined.empty else None,
                "comparison_value": float(joined["comparison_value"].sum(min_count=1)) if not joined.empty else None,
            }
            return "FAILED", metadata["baseline_value"], None, metadata["comparison_value"], f"{source} value is missing for {missing_description}", metadata

        joined["difference"] = joined["VALUE"] - joined["comparison_value"]
        baseline_value = float(joined["VALUE"].sum())
        comparison_value = float(joined["comparison_value"].sum())
        difference_value = float(joined["difference"].sum())
        metadata = {
            **base_metadata,
            "baseline_value": baseline_value,
            "comparison_value": comparison_value,
            "difference_value": difference_value,
        }
        failed_units = joined.loc[joined["difference"].abs() > self.COMPARISON_TOLERANCE, "unit"].tolist()
        if failed_units:
            source_label = "Anaplan" if source == "ANAPLAN" else "PBI"
            override_data = self.comparison_data.get("OVERRIDE_TRACKER")
            pbi_data = self.comparison_data.get("PBI")
            if override_data is not None and pbi_data is not None and not override_data.empty and not pbi_data.empty:
                override_values = override_data[
                    override_data["kpi_id"].astype(str).eq(str(rule.kpi_id))
                    & override_data["frequency"].eq(rule.frequency)
                    & override_data["period"].eq(period.isoformat())
                    & override_data["unit"].isin(failed_units)
                ]
                pbi_values = pbi_data[
                    pbi_data["kpi_id"].astype(str).eq(str(rule.kpi_id))
                    & pbi_data["period"].eq(period.isoformat())
                    & pbi_data["unit"].isin(failed_units)
                ]
                override_match = (
                    pd.DataFrame({"unit": failed_units})
                    .merge(override_values, on="unit", how="left")
                    .merge(pbi_values[["unit", "comparison_value"]], on="unit", how="left")
                )
                if (
                    not override_match.empty
                    and override_match["override_value"].notna().all()
                    and override_match["comparison_value"].notna().all()
                    and (override_match["override_value"] - override_match["comparison_value"]).abs().le(self.COMPARISON_TOLERANCE).all()
                    and (joined.loc[joined["unit"].isin(failed_units), "comparison_value"].reset_index(drop=True) - override_match["override_value"].reset_index(drop=True)).abs().le(self.COMPARISON_TOLERANCE).all()
                ):
                    return (
                        "PASSED",
                        baseline_value,
                        None,
                        comparison_value,
                        f"EDL mismatch {source_label}, but {source_label} value matches Override tracker and PBI for {', '.join(failed_units)}",
                        metadata,
                    )
            return "FAILED", baseline_value, None, comparison_value, f"EDL and {source} differ for {', '.join(failed_units)}", metadata
        return "PASSED", baseline_value, None, comparison_value, f"EDL and {source} values match", metadata

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
