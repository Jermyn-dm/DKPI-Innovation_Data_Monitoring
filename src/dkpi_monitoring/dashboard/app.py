from __future__ import annotations

import calendar as month_calendar
from datetime import date, timedelta
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st

from dkpi_monitoring.dashboard.data import DashboardDataProvider
from dkpi_monitoring.calendar.service import BusinessCalendarService
from dkpi_monitoring.models import BusinessCalendarConfig
from repositories.base_config_repository import ExcelConfigurationDataSource
from repositories.kpi_config_repository import KPIConfigRepository
from repositories.kpi_validation_rule_repository import KPIValidationRuleRepository
from services.kpi_validation_service import KPIValidationService


CONFIG_DIR = Path("configs")
MONTHLY_CONFIG_DIR = CONFIG_DIR / "monthly"
DAILY_CONFIG_DIR = CONFIG_DIR / "daily"
SHARED_CONFIG_DIR = CONFIG_DIR / "shared"
DEFAULT_SOURCE_FILE = Path("data/source/edl_data.xlsx")
DEFAULT_ANAPLAN_FILE = Path("data/source/anaplan_data.xlsx")
DEFAULT_PBI_FILE = Path("data/source/pbi_data.xlsx")
DEFAULT_OVERRIDE_TRACKER_FILE = Path("data/source/Agency_KPI_Override_Tracker.xlsx")
DEFAULT_STANDARD_FILE = Path("data/reference/kpi_standard_values.xlsx")
DAILY_STANDARD_FILE = Path("data/reference/daily/kpi_standard_values.xlsx")
VALIDATION_RULE_FILE = CONFIG_DIR / "kpi_validation_rule_config.xlsx"
DAILY_VALIDATION_RULE_FILE = DAILY_CONFIG_DIR / "kpi_validation_rule_config.xlsx"
SOURCE_MAPPING_FILE = CONFIG_DIR / "source_table_mapping.xlsx"
DAILY_RESULT_FILE = Path("data/results/daily/kpi_validation_results.csv")
DAILY_BUSINESS_DAY_MARKETS = {"HK", "SG"}
BASELINE_RULES = [
    ("RULE_RECORD_EXISTS", "RECORD_EXISTS", 1, None, None, "KPI source record must exist"),
    ("RULE_VALUE_NOT_NULL", "VALUE_NOT_NULL", 2, "VALUE", None, "KPI value must not be null"),
    ("RULE_VALUE_GREATER_THAN_ZERO", "VALUE_GREATER_THAN_ZERO", 3, "VALUE", None, "KPI value must be greater than zero"),
    ("RULE_EDL_VS_ANAPLAN", "EDL_MATCH_ANAPLAN", 101, "VALUE", "ANAPLAN", "EDL value must match Anaplan or a user-uploaded override tracker value matched by Anaplan and PBI"),
    ("RULE_EDL_VS_PBI", "EDL_MATCH_PBI", 102, "VALUE", "PBI", "EDL value must match PBI or a user-uploaded override tracker value matched by Anaplan and PBI"),
]
DAILY_RULES = [
    ("RULE_RECORD_EXISTS", "RECORD_EXISTS", 1, None, None, "Daily KPI source record must exist"),
    ("RULE_VALUE_NOT_NULL", "VALUE_NOT_NULL", 2, "VALUE", None, "Daily KPI value must not be null"),
    ("RULE_VALUE_GREATER_THAN_ZERO", "VALUE_GREATER_THAN_ZERO", 3, "VALUE", None, "Daily KPI value must be greater than zero"),
    ("RULE_EDL_VS_ANAPLAN", "EDL_MATCH_ANAPLAN", 101, "VALUE", "ANAPLAN", "Daily EDL value must match Anaplan"),
    ("RULE_EDL_VS_PBI", "EDL_MATCH_PBI", 102, "VALUE", "PBI", "Daily EDL value must match PBI"),
]
CHANNEL_FREQUENCIES = {
    "Agency": ["Monthly", "Daily"],
    "Banca": ["Monthly", "Daily"],
    "Risk": ["Monthly"],
}
ACTIVE_WORKSPACE_KEY = "active_validation_workspace"


class FrequencyConfigurationDataSource:
    def __init__(self, primary_path: Path, shared_path: Path, legacy_path: Path) -> None:
        self.primary_path = primary_path
        self.shared_path = shared_path
        self.legacy_path = legacy_path

    def read_table(self, table_name: str) -> pd.DataFrame:
        filename = f"{table_name}.xlsx"
        for path in (self.primary_path, self.shared_path, self.legacy_path):
            candidate = path / filename
            if candidate.exists():
                return pd.read_excel(candidate)
        return pd.read_excel(self.primary_path / filename)


def _apply_brand_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ml-green: #00a758;
            --ml-deep-green: #00563f;
            --ml-ink: #1f2a33;
            --ml-muted: #5e6a72;
            --ml-surface: #ffffff;
            --ml-page: #f4f7f5;
            --ml-border: #d8e2dc;
        }
        .stApp {
            background: var(--ml-page);
            color: var(--ml-ink);
        }
        [data-testid="stSidebar"] {
            background: var(--ml-surface);
            border-right: 1px solid var(--ml-border);
        }
        .brand-shell {
            background: var(--ml-deep-green);
            color: white;
            padding: 0.8rem 1.25rem;
            border-radius: 8px;
            margin-bottom: 0.75rem;
        }
        .brand-shell h1 {
            margin: 0;
            font-size: 1.4rem;
            font-weight: 700;
        }
        .brand-shell p {
            margin: 0.2rem 0 0;
            color: #dceee6;
            font-size: 0.95rem;
        }
        div[data-testid="stMetric"] {
            background: var(--ml-surface);
            border: 1px solid var(--ml-border);
            border-left: 4px solid var(--ml-green);
            border-radius: 8px;
            padding: 0.85rem 1rem;
        }
        [class*="st-key-metric_"] button {
            background: var(--ml-surface);
            border: 1px solid var(--ml-border);
            border-left: 4px solid var(--ml-green);
            border-radius: 8px;
            color: var(--ml-ink);
            font-size: 1rem;
            font-weight: 700;
            min-height: 5.4rem;
            white-space: pre-line;
        }
        [class*="st-key-metric_"] button:hover {
            border-color: var(--ml-deep-green);
            background: #eef8f2;
        }
        [class*="st-key-metric_"] button[kind="primary"] {
            background: #dff4e7;
            border-color: var(--ml-deep-green);
        }
        .daily-calendar {
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
            border: 1px solid var(--ml-border);
            border-radius: 8px;
            overflow: hidden;
        }
        .daily-calendar__weekday {
            background: #eaf1ed;
            color: var(--ml-muted);
            font-size: 0.8rem;
            font-weight: 700;
            padding: 0.45rem 0.65rem;
        }
        .daily-calendar__cell {
            border-right: 1px solid var(--ml-border);
            border-top: 1px solid var(--ml-border);
            min-height: 5rem;
            padding: 0.45rem 0.65rem;
        }
        .daily-calendar__cell:nth-child(7n) { border-right: 0; }
        .daily-calendar__cell--empty { background: #fafbfa; }
        .daily-calendar__cell--not-run { background: #f1f3f5; }
        .daily-calendar__cell--not-due { background: #e9ecef; }
        .daily-calendar__cell--passed { background: #dff4e7; }
        .daily-calendar__cell--failed { background: #fff3cd; }
        .daily-calendar__cell--missing { background: #f8d7da; }
        .daily-calendar__date {
            color: #1f2a33;
            display: block;
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.2;
        }
        .daily-calendar__summary {
            color: #5e6a72;
            display: block;
            font-size: 0.76rem;
            font-weight: 600;
            line-height: 1.25;
            margin-top: 0.55rem;
        }
        .daily-calendar__cell--missing .daily-calendar__summary { color: #842029; }
        .daily-calendar__cell--failed .daily-calendar__summary { color: #664d03; }
        .daily-calendar__cell--passed .daily-calendar__summary { color: #00563f; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _previous_month_end(today: date | None = None) -> date:
    value = pd.Timestamp(today or date.today())
    return (value.replace(day=1).date() - timedelta(days=1))


def _daily_validation_dates(start_date: date, end_date: date | None) -> list[date]:
    if end_date is not None and end_date < start_date:
        raise ValueError("Daily end date must be on or after the Daily start date")
    final_date = end_date or start_date
    return [item.date() for item in pd.date_range(start_date, final_date, freq="D")]


def _months_in_range(start_date: date, end_date: date) -> list[date]:
    months = pd.date_range(start_date.replace(day=1), end_date.replace(day=1), freq="MS")
    return [item.date() for item in months]


def _filter_period_range(results: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    periods = pd.to_datetime(results["period"], errors="coerce")
    return results.loc[periods.between(pd.Timestamp(start_date), pd.Timestamp(end_date))]


def _read_uploaded_table(
    uploaded_file: object | None,
    default_path: Path,
    header: int | None = 0,
    sheet_name: str | int = 0,
) -> pd.DataFrame:
    if uploaded_file is None:
        if default_path.suffix.lower() == ".csv":
            return pd.read_csv(default_path)
        return pd.read_excel(default_path, header=header, sheet_name=sheet_name)

    name = getattr(uploaded_file, "name", "")
    if name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file, header=header, sheet_name=sheet_name)


def _standard_values_path(uploaded_file: object | None) -> Path | None:
    if uploaded_file is None:
        return DEFAULT_STANDARD_FILE
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        return Path(temp_file.name)


def _business_calendar_service() -> BusinessCalendarService:
    calendar_path = SHARED_CONFIG_DIR / "calendar_config.xlsx"
    if not calendar_path.exists():
        calendar_path = CONFIG_DIR / "calendar_config.xlsx"
    calendar_data = pd.read_excel(calendar_path)
    entries: list[BusinessCalendarConfig] = []
    for row in calendar_data.to_dict("records"):
        market = str(row.get("market", "")).strip()
        calendar_date = pd.to_datetime(row.get("calendar_date"), errors="coerce")
        if not market or pd.isna(calendar_date):
            continue
        is_business_day = str(row.get("is_business_day", "N")).strip().upper() in {"Y", "YES", "TRUE", "1"}
        entries.append(
            BusinessCalendarConfig(
                market=market,
                calendar_date=calendar_date.date(),
                is_business_day=is_business_day,
            )
        )
    return BusinessCalendarService(entries)


def _configuration_data_source(frequency: str) -> ExcelConfigurationDataSource | FrequencyConfigurationDataSource:
    if frequency == "Daily":
        return FrequencyConfigurationDataSource(DAILY_CONFIG_DIR, SHARED_CONFIG_DIR, CONFIG_DIR)
    if frequency == "Monthly":
        return FrequencyConfigurationDataSource(MONTHLY_CONFIG_DIR, SHARED_CONFIG_DIR, CONFIG_DIR)
    return ExcelConfigurationDataSource(CONFIG_DIR)


def _configured_kpis(channel: str, frequency: str) -> tuple[list, list]:
    data_source = _configuration_data_source(frequency)
    kpi_repo = KPIConfigRepository(data_source)
    rule_repo = KPIValidationRuleRepository(data_source)
    rules = [
        rule
        for rule in rule_repo.load_validation_rules()
        if rule.channel == channel and rule.frequency == frequency
    ]
    configured_keys = {
        (rule.channel, rule.market, rule.kpi_id, rule.frequency)
        for rule in rules
    }
    kpis = [
        kpi
        for kpi in kpi_repo.load_kpi_configs()
        if kpi.active
        and kpi.channel == channel
        and ((frequency == "Monthly" and kpi.monthly) or (frequency == "Daily" and kpi.daily))
        and (kpi.channel, kpi.country_cd, kpi.kpi_id, frequency) in configured_keys
    ]
    return kpis, rules


def _daily_market_expects_data(
    frequency: str,
    market: str,
    period: date,
    calendar_service: BusinessCalendarService | None,
) -> bool:
    if frequency != "Daily" or market not in DAILY_BUSINESS_DAY_MARKETS:
        return True
    if calendar_service is None or market not in calendar_service._configured_markets:
        return True
    return calendar_service.is_business_day(market, period)


def _target_availability_for_run(frequency: str, market: str, target_availability: str) -> str:
    if frequency == "Daily" and market in DAILY_BUSINESS_DAY_MARKETS:
        return target_availability.upper().replace("CD", "BD")
    return target_availability


def _result_file_for_frequency(frequency: str) -> Path | None:
    if frequency == "Daily":
        return DAILY_RESULT_FILE
    return None


def _eligible_edl_monthly_kpis() -> pd.DataFrame:
    kpi_data = pd.read_excel(CONFIG_DIR / "kpi_config.xlsx")
    return kpi_data[
        kpi_data["kpi_id"].notna()
        & kpi_data["monthly"].astype(str).str.strip().str.upper().eq("Y")
        & kpi_data["derivation logic"].astype(str).str.strip().str.upper().eq("EDL")
    ].copy()


def _eligible_edl_daily_kpis() -> pd.DataFrame:
    kpi_data = pd.read_excel(DAILY_CONFIG_DIR / "kpi_config.xlsx")
    return kpi_data[
        kpi_data["kpi_id"].notna()
        & kpi_data["daily"].astype(str).str.strip().str.upper().eq("Y")
        & kpi_data["derivation logic"].astype(str).str.strip().str.upper().eq("EDL")
    ].copy()


def _upload_key(channel: str, frequency: str, file_name: str) -> str:
    return f"upload_{channel}_{frequency}_{file_name}"


def _monthly_data_files(channel: str, frequency: str) -> dict[str, object | None]:
    file_edl, file_anaplan = st.columns(2)
    file_pbi, file_standard = st.columns(2)
    return {
        "source_file": file_edl.file_uploader(
            "EDL source file",
            type=["csv", "xlsx"],
            key=_upload_key(channel, frequency, "edl"),
        ),
        "anaplan_file": file_anaplan.file_uploader(
            "Anaplan source file",
            type=["xlsx"],
            key=_upload_key(channel, frequency, "anaplan"),
        ),
        "pbi_file": file_pbi.file_uploader(
            "PBI source file",
            type=["xlsx"],
            key=_upload_key(channel, frequency, "pbi"),
        ),
        "standard_file": file_standard.file_uploader(
            "Standard value file",
            type=["xlsx"],
            key=_upload_key(channel, frequency, "standard"),
        ),
        "override_file": st.file_uploader(
            "Agency KPI Override tracker",
            type=["xlsx"],
            key=_upload_key(channel, frequency, "override"),
        ),
    }


def _daily_data_files(channel: str, frequency: str) -> dict[str, object | None]:
    st.caption("Daily validation uses separate Daily files. Monthly uploads and defaults are not reused.")
    file_edl, file_anaplan = st.columns(2)
    file_pbi, file_standard = st.columns(2)
    return {
        "source_file": file_edl.file_uploader(
            "Daily EDL source file",
            type=["csv", "xlsx"],
            key=_upload_key(channel, frequency, "edl"),
        ),
        "anaplan_file": file_anaplan.file_uploader(
            "Daily Anaplan source file",
            type=["xlsx"],
            key=_upload_key(channel, frequency, "anaplan"),
        ),
        "pbi_file": file_pbi.file_uploader(
            "Daily PBI source file",
            type=["xlsx"],
            key=_upload_key(channel, frequency, "pbi"),
        ),
        "standard_file": file_standard.file_uploader(
            "Daily standard value file",
            type=["xlsx"],
            key=_upload_key(channel, frequency, "standard"),
        ),
        "override_file": st.file_uploader(
            "Daily Agency KPI Override tracker",
            type=["xlsx"],
            key=_upload_key(channel, frequency, "override"),
        ),
    }


def _data_files(channel: str, frequency: str) -> dict[str, object | None]:
    if frequency == "Daily":
        return _daily_data_files(channel, frequency)
    return _monthly_data_files(channel, frequency)


def _baseline_validation_rows(kpis: pd.DataFrame) -> pd.DataFrame:
    return _validation_rule_rows(kpis, "Monthly", BASELINE_RULES)


def _daily_validation_rows(kpis: pd.DataFrame) -> pd.DataFrame:
    return _validation_rule_rows(kpis, "Daily", DAILY_RULES)


def _validation_rule_rows(
    kpis: pd.DataFrame,
    frequency: str,
    rule_definitions: list[tuple[str, str, int, str | None, str | None, str]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for kpi in kpis.to_dict("records"):
        for rule_id, rule_type, rule_order, value_column, comparison_source, remark in rule_definitions:
            rows.append(
                {
                    "channel": kpi["channel"],
                    "market": kpi["country_cd"],
                    "kpi_id": kpi["kpi_id"],
                    "kpi_name": kpi["kpi_name"],
                    "frequency": frequency,
                    "source_table": kpi["source_table"],
                    "rule_id": rule_id,
                    "rule_type": rule_type,
                    "rule_order": rule_order,
                    "value_column": value_column,
                    "threshold_percent": None,
                    "standard_value": None,
                    "comparison_source": comparison_source,
                    "enabled": "Y",
                    "effective_from": kpi.get("effective_from"),
                    "effective_to": kpi.get("effective_to"),
                    "remark": remark,
                }
            )
    return pd.DataFrame(rows)


def _upsert_baseline_validation_rules(kpis: pd.DataFrame) -> int:
    baseline = _baseline_validation_rows(kpis)
    return _upsert_validation_rules(VALIDATION_RULE_FILE, baseline, {rule[0] for rule in BASELINE_RULES})


def _upsert_daily_validation_rules(kpis: pd.DataFrame) -> int:
    daily_rules = _daily_validation_rows(kpis)
    return _upsert_validation_rules(DAILY_VALIDATION_RULE_FILE, daily_rules, {rule[0] for rule in DAILY_RULES})


def _upsert_validation_rules(path: Path, generated_rules: pd.DataFrame, generated_rule_ids: set[str]) -> int:
    existing = pd.read_excel(path) if path.exists() else pd.DataFrame(columns=generated_rules.columns)
    baseline_keys = set(
        zip(
            generated_rules["market"].astype(str),
            generated_rules["kpi_id"].astype(str),
            generated_rules["frequency"].astype(str),
            generated_rules["rule_id"].astype(str),
        )
    )
    keep = []
    for row in existing.to_dict("records"):
        key = (
            str(row.get("market")),
            str(row.get("kpi_id")),
            str(row.get("frequency")),
            str(row.get("rule_id")),
        )
        keep.append(row.get("rule_id") not in generated_rule_ids or key not in baseline_keys)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = [frame.dropna(axis=1, how="all") for frame in (existing.loc[keep], generated_rules) if not frame.empty]
    updated = pd.concat(frames, ignore_index=True).reindex(columns=generated_rules.columns)
    updated.to_excel(path, index=False)
    return len(generated_rules)


def _default_physical_object_name(source_table: str) -> str:
    if source_table == "agency_fact":
        return "Agency_data_checking_UC.csv"
    return f"{source_table}.csv"


def _ensure_source_table_mappings(kpis: pd.DataFrame) -> int:
    existing = pd.read_excel(SOURCE_MAPPING_FILE)
    existing_keys = set(zip(existing["source_table"].astype(str), existing["market"].astype(str)))
    additions: list[dict[str, str]] = []
    for row in kpis[["source_table", "country_cd"]].drop_duplicates().to_dict("records"):
        source_table = str(row["source_table"])
        market = str(row["country_cd"])
        if (source_table, market) not in existing_keys:
            additions.append(
                {
                    "source_table": source_table,
                    "market": market,
                    "provider_type": "Excel",
                    "physical_object_name": _default_physical_object_name(source_table),
                }
            )
    if additions:
        updated = pd.concat([existing, pd.DataFrame(additions)], ignore_index=True)
        updated.to_excel(SOURCE_MAPPING_FILE, index=False)
    return len(additions)


def _configure_edl_monthly_baseline_rules() -> tuple[int, int, int]:
    kpis = _eligible_edl_monthly_kpis()
    rule_count = _upsert_baseline_validation_rules(kpis)
    mapping_count = _ensure_source_table_mappings(kpis)
    return len(kpis), rule_count, mapping_count


def _configure_edl_daily_validation_rules() -> tuple[int, int]:
    kpis = _eligible_edl_daily_kpis()
    rule_count = _upsert_daily_validation_rules(kpis)
    return len(kpis), rule_count


def _run_validation(
    source_data: pd.DataFrame,
    standard_values_path: Path | None,
    period: date,
    channel: str,
    frequency: str,
    comparison_data: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    kpis, rules = _configured_kpis(channel, frequency)
    calendar_service = _business_calendar_service()
    kpis = [
        kpi
        for kpi in kpis
        if _daily_market_expects_data(frequency, kpi.country_cd, period, calendar_service)
    ]
    expected_markets = {kpi.country_cd for kpi in kpis}
    rules = [rule for rule in rules if rule.market in expected_markets]
    service = KPIValidationService(standard_values_path, comparison_data)
    all_results: list[dict] = []
    for kpi in kpis:
        if not kpi.target_availability:
            raise ValueError(
                f"Missing target availability for {kpi.country_cd}/{kpi.kpi_id}/{kpi.channel}"
            )
        kpi_rules = [
            rule
            for rule in rules
            if (rule.channel, rule.market, rule.kpi_id, rule.frequency)
            == (kpi.channel, kpi.country_cd, kpi.kpi_id, frequency)
        ]
        all_results.extend(
            service.validate_and_save(
                kpi_rules,
                source_data,
                period,
                output_path=_result_file_for_frequency(frequency),
                target_availability=_target_availability_for_run(frequency, kpi.country_cd, kpi.target_availability),
                calendar_service=calendar_service,
            )
        )
    return pd.DataFrame(all_results)


def _expected_kpis(
    channel: str,
    frequency: str,
    source_data: pd.DataFrame,
    period: date | None = None,
    period_end: date | None = None,
    calendar_service: BusinessCalendarService | None = None,
) -> pd.DataFrame:
    kpis, _ = _configured_kpis(channel, frequency)
    if period is not None and frequency != "Daily":
        kpis = [
            kpi
            for kpi in kpis
            if _daily_market_expects_data(frequency, kpi.country_cd, period, calendar_service)
        ]
    if frequency == "Daily" and period is not None:
        expected = [
            {
                "channel": kpi.channel,
                "market": kpi.country_cd,
                "kpi_id": str(kpi.kpi_id),
                "kpi_name": kpi.kpi_name,
                "frequency": frequency,
                "period": validation_date.isoformat(),
                "mvp_phase": kpi.mvp1_mvp2 or "Unspecified",
            }
            for validation_date in _daily_validation_dates(period, period_end)
            for kpi in kpis
            if kpi.kpi_id
            and str(kpi.derivation_logic or "").strip().upper() == "EDL"
            and _daily_market_expects_data(
                frequency,
                kpi.country_cd,
                validation_date,
                calendar_service,
            )
        ]
        return pd.DataFrame(expected)
    expected = [
        {
            "channel": kpi.channel,
            "market": kpi.country_cd,
            "kpi_id": str(kpi.kpi_id),
            "kpi_name": kpi.kpi_name,
            "frequency": frequency,
            "mvp_phase": kpi.mvp1_mvp2 or "Unspecified",
        }
        for kpi in kpis
        if kpi.kpi_id and str(kpi.derivation_logic or "").strip().upper() == "EDL"
    ]
    return pd.DataFrame(expected)


def _filter_expected_kpis(
    expected: pd.DataFrame,
    market: str,
    mvp_phase: str,
    kpi_names: list[str],
) -> pd.DataFrame:
    if expected.empty:
        return expected
    filtered = expected.copy()
    if market != "All markets":
        filtered = filtered[filtered["market"].eq(market)]
    if mvp_phase != "All phases":
        filtered = filtered[filtered["mvp_phase"].eq(mvp_phase)]
    if kpi_names:
        filtered = filtered[filtered["kpi_name"].isin(kpi_names)]
    return filtered


def _metric_kpi_sets(expected: pd.DataFrame, results: pd.DataFrame) -> dict[str, pd.DataFrame]:
    key_columns = ["channel", "market", "kpi_id", "frequency"]
    if "period" in expected.columns:
        key_columns.append("period")
    summary = results[results["record_type"].eq("KPI_SUMMARY")][
        key_columns + ["status", "ready_status"]
    ].drop_duplicates(key_columns)
    if "rule_id" in results.columns:
        exists_rule = results[
            results["record_type"].eq("RULE") & results["rule_id"].eq("RULE_RECORD_EXISTS")
        ][key_columns + ["status"]].drop_duplicates(key_columns).rename(columns={"status": "record_exists_status"})
    else:
        exists_rule = pd.DataFrame(columns=key_columns + ["record_exists_status"])
    metrics = expected.merge(summary, on=key_columns, how="left").merge(exists_rule, on=key_columns, how="left")
    record_exists = metrics["record_exists_status"].eq("PASSED")
    validation_executed = metrics["ready_status"].notna() & (~metrics["ready_status"].eq("NOT_DUE") | record_exists)
    return {
        "All KPIs": metrics,
        "Expected KPI": metrics,
        "Ready KPI": metrics[record_exists],
        "Missing KPI": metrics[metrics["ready_status"].eq("MISSING") & ~record_exists],
        "Not Due KPI": metrics[metrics["ready_status"].eq("NOT_DUE") & ~record_exists],
        "Delayed KPI": metrics[metrics["ready_status"].eq("READY_DELAYED") & record_exists],
        "Validation Passed": metrics[validation_executed & metrics["status"].eq("PASSED")],
        "Validation Failed": metrics[
            validation_executed & metrics["status"].notna() & ~metrics["status"].eq("PASSED")
        ],
    }


def _metric_counts(expected: pd.DataFrame, results: pd.DataFrame) -> dict[str, int]:
    metric_sets = _metric_kpi_sets(expected, results)
    return {label: len(rows) for label, rows in metric_sets.items() if label != "All KPIs"}


def _sort_kpi_summary(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty or "status" not in summary.columns:
        return summary
    return (
        summary.assign(_status_priority=summary["status"].eq("FAILED").map({True: 0, False: 1}))
        .sort_values("_status_priority", kind="stable")
        .drop(columns="_status_priority")
    )


def _market_kpi_overview(expected: pd.DataFrame, results: pd.DataFrame, period: str) -> pd.DataFrame:
    columns = [
        "Market",
        "Channel",
        "Frequency",
        "Period",
        "Expected KPI",
        "Ready KPI",
        "Missing KPI",
        "Not Due KPI",
        "Delayed KPI",
        "Validation Passed",
        "Validation Failed",
    ]
    rows: list[dict[str, object]] = []
    for market, market_expected in expected.groupby("market", sort=True):
        key_columns = ["channel", "market", "kpi_id", "frequency"]
        if "period" in market_expected.columns:
            key_columns.append("period")
        market_keys = market_expected[key_columns].drop_duplicates()
        market_results = results.merge(market_keys, on=key_columns, how="inner")
        metrics = _metric_counts(market_expected, market_results)
        rows.append(
            {
                "Market": market,
                "Channel": market_expected["channel"].iloc[0],
                "Frequency": market_expected["frequency"].iloc[0],
                "Period": period,
                **metrics,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _metric_filter_key(channel: str, frequency: str) -> str:
    return f"metric_filter_{channel}_{frequency}"


def _scroll_target_key(channel: str, frequency: str) -> str:
    return f"scroll_target_{channel}_{frequency}"


def _scroll_request_key(channel: str, frequency: str) -> str:
    return f"scroll_request_{channel}_{frequency}"


def _last_view_anchor_key(channel: str, frequency: str) -> str:
    return f"last_view_anchor_{channel}_{frequency}"


def _remember_view_anchor(channel: str, frequency: str, anchor: str) -> None:
    st.session_state[_last_view_anchor_key(channel, frequency)] = anchor


def _request_scroll(channel: str, frequency: str, anchor: str) -> None:
    _remember_view_anchor(channel, frequency, anchor)
    sequence = int(st.session_state.get(_scroll_request_key(channel, frequency), 0)) + 1
    st.session_state[_scroll_request_key(channel, frequency)] = sequence
    st.session_state[_scroll_target_key(channel, frequency)] = (anchor, sequence)


def _selection_revision_key(channel: str, frequency: str, selection_name: str) -> str:
    return f"{selection_name}_selection_revision_{channel}_{frequency}"


def _selection_revision(channel: str, frequency: str, selection_name: str) -> int:
    return int(st.session_state.get(_selection_revision_key(channel, frequency, selection_name), 0))


def _bump_selection_revision(channel: str, frequency: str, selection_name: str) -> None:
    st.session_state[_selection_revision_key(channel, frequency, selection_name)] = _selection_revision(
        channel,
        frequency,
        selection_name,
    ) + 1


def _overview_selection_key(channel: str, frequency: str) -> str:
    return f"market_overview_selection_{channel}_{frequency}_{_selection_revision(channel, frequency, 'overview')}"


def _summary_selection_key(channel: str, frequency: str) -> str:
    return f"summary_selection_{channel}_{frequency}_{_selection_revision(channel, frequency, 'summary')}"


def _filter_key(channel: str, frequency: str, suffix: str) -> str:
    return f"filter_{channel}_{frequency}_{suffix}"


def _filter_default_period_key(channel: str, frequency: str) -> str:
    return f"filter_default_period_{channel}_{frequency}"


def _suppress_market_change_key(channel: str, frequency: str) -> str:
    return f"suppress_market_change_{channel}_{frequency}"


def _reset_filters_requested_key(channel: str, frequency: str) -> str:
    return f"reset_filters_requested_{channel}_{frequency}"


def _select_metric(channel: str, frequency: str, label: str) -> None:
    st.session_state[_metric_filter_key(channel, frequency)] = label
    _bump_selection_revision(channel, frequency, "summary")
    _request_scroll(channel, frequency, "kpi-summary")


def _select_overview_market(channel: str, frequency: str, market: str) -> None:
    st.session_state[_suppress_market_change_key(channel, frequency)] = True
    st.session_state[_filter_key(channel, frequency, "market")] = market
    st.session_state.pop(_metric_filter_key(channel, frequency), None)
    _bump_selection_revision(channel, frequency, "summary")
    _request_scroll(channel, frequency, "kpi-summary")


def _overview_previous_market_key(channel: str, frequency: str) -> str:
    return f"overview_previous_market_{channel}_{frequency}"


def _pending_overview_market_key(channel: str, frequency: str) -> str:
    return f"pending_overview_market_{channel}_{frequency}"


def _apply_pending_overview_market(channel: str, frequency: str) -> None:
    market = st.session_state.pop(_pending_overview_market_key(channel, frequency), None)
    if market is not None:
        _select_overview_market(channel, frequency, str(market))


def _clear_overview_drilldown(channel: str, frequency: str) -> None:
    if st.session_state.pop(_suppress_market_change_key(channel, frequency), False):
        return
    st.session_state.pop(_overview_previous_market_key(channel, frequency), None)
    _bump_selection_revision(channel, frequency, "overview")
    _bump_selection_revision(channel, frequency, "summary")


def _overview_data_key(channel: str, frequency: str) -> str:
    return f"market_overview_data_{channel}_{frequency}"


def _apply_overview_selection() -> None:
    workspace = st.session_state.get(ACTIVE_WORKSPACE_KEY)
    if not workspace:
        return
    channel, frequency = workspace
    selection = st.session_state.get(_overview_selection_key(channel, frequency), {})
    selected_rows = selection.get("selection", {}).get("rows", [])
    overview = st.session_state.get(_overview_data_key(channel, frequency))
    if selected_rows and isinstance(overview, pd.DataFrame):
        market = str(overview.iloc[selected_rows[0]]["Market"])
        previous_market_key = _overview_previous_market_key(channel, frequency)
        if previous_market_key not in st.session_state:
            st.session_state[previous_market_key] = st.session_state.get(
                f"filter_{channel}_{frequency}_market",
                "All markets",
            )
        _select_overview_market(channel, frequency, market)
    else:
        previous_market = st.session_state.pop(
            _overview_previous_market_key(channel, frequency),
            "All markets",
        )
        st.session_state[_suppress_market_change_key(channel, frequency)] = True
        st.session_state[_filter_key(channel, frequency, "market")] = previous_market
        st.session_state.pop(_metric_filter_key(channel, frequency), None)
        _bump_selection_revision(channel, frequency, "summary")


def _metric_button_key(channel: str, frequency: str, label: str) -> str:
    return f"metric_{channel}_{frequency}_{label.lower().replace(' ', '_')}"


def _summary_metrics(metrics: dict[str, int], channel: str, frequency: str) -> None:
    selected_metric = st.session_state.get(_metric_filter_key(channel, frequency), "All KPIs")
    first_row = st.columns(5)
    for column, label in zip(first_row, ["Expected KPI", "Ready KPI", "Missing KPI", "Not Due KPI", "Delayed KPI"]):
        column.button(
            f"{label}\n{metrics[label]:,}",
            key=_metric_button_key(channel, frequency, label),
            width="stretch",
            type="primary" if label == selected_metric else "secondary",
            on_click=_select_metric,
            args=(channel, frequency, label),
        )
    second_row = st.columns([1, 1, 3])
    for column, label in zip(second_row[:2], ["Validation Passed", "Validation Failed"]):
        column.button(
            f"{label}\n{metrics[label]:,}",
            key=_metric_button_key(channel, frequency, label),
            width="stretch",
            type="primary" if label == selected_metric else "secondary",
            on_click=_select_metric,
            args=(channel, frequency, label),
        )


def _workspace_state_key(channel: str, frequency: str) -> str:
    return f"validation_result_{channel}_{frequency}"


def _clear_filter_state(channel: str, frequency: str) -> None:
    st.session_state[_reset_filters_requested_key(channel, frequency)] = True
    st.session_state.pop(_metric_filter_key(channel, frequency), None)
    st.session_state.pop(_overview_previous_market_key(channel, frequency), None)
    st.session_state.pop(_suppress_market_change_key(channel, frequency), None)
    _remember_view_anchor(channel, frequency, "results")
    _bump_selection_revision(channel, frequency, "overview")
    _bump_selection_revision(channel, frequency, "summary")


def _default_filter_period(periods: list[str], preferred_period: str) -> str:
    return preferred_period if preferred_period in periods else periods[0]


def _as_date(value: str) -> date:
    return pd.Timestamp(value).date()


def _workspace_period_changed(workspace_data: dict[str, object], period: date, period_end: date | None) -> bool:
    workspace_start = _as_date(workspace_data.get("period_start", period))
    workspace_end = _as_date(workspace_data.get("period_end") or workspace_start)
    return workspace_start != period or workspace_end != (period_end or period)


def _workspace_period_defaults(
    frequency: str,
    workspace_data: dict[str, object] | None,
) -> tuple[date, date | None]:
    if workspace_data is not None:
        workspace_start = _as_date(workspace_data.get("period_start"))
        workspace_end = _as_date(workspace_data.get("period_end") or workspace_start)
        if frequency == "Daily":
            return workspace_start, workspace_end
        return workspace_start, None
    if frequency == "Daily":
        return date.today(), None
    return _previous_month_end(), None


def _apply_filter_defaults(
    channel: str,
    frequency: str,
    periods: list[str],
    preferred_period: str,
    preferred_end_period: str | None = None,
) -> None:
    period_key = _filter_key(channel, frequency, "period")
    default_period_key = _filter_default_period_key(channel, frequency)
    default_period = _default_filter_period(periods, preferred_period)
    default_end_period = preferred_end_period or default_period
    default_period_state = f"{default_period}|{default_end_period}"
    previous_default_period_state = st.session_state.get(default_period_key)
    if not st.session_state.pop(_reset_filters_requested_key(channel, frequency), False):
        if st.session_state.get(period_key) not in periods:
            st.session_state[period_key] = default_period
        if frequency == "Daily" and previous_default_period_state != default_period_state:
            st.session_state[_filter_key(channel, frequency, "period_start")] = _as_date(default_period)
            st.session_state[_filter_key(channel, frequency, "period_end")] = _as_date(default_end_period)
        st.session_state[default_period_key] = default_period_state
        return
    st.session_state[_filter_key(channel, frequency, "market")] = "All markets"
    st.session_state[period_key] = default_period
    if frequency == "Daily":
        st.session_state[_filter_key(channel, frequency, "period_start")] = _as_date(default_period)
        st.session_state[_filter_key(channel, frequency, "period_end")] = _as_date(
            default_end_period
        )
    st.session_state[default_period_key] = default_period_state
    st.session_state[_filter_key(channel, frequency, "mvp")] = "All phases"
    st.session_state[_filter_key(channel, frequency, "kpi")] = []


def _scroll_to(anchor: str, sequence: int = 0) -> None:
    st.html(
        f"""
        <script data-scroll-request="{sequence}">
        window.parent.requestAnimationFrame(() => {{
            const target = window.parent.document.getElementById('{anchor}');
            if (target) {{
                target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                window.parent.location.hash = '{anchor}';
            }}
        }});
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def _latest_execution_results(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return results
    key_columns = ["channel", "market", "kpi_id", "frequency", "period"]
    display = results.copy()
    display["_execution_timestamp"] = pd.to_datetime(
        display["execution_timestamp"], errors="coerce", utc=True
    )
    latest_timestamp = display.groupby(key_columns, dropna=False)["_execution_timestamp"].transform("max")
    return display.loc[display["_execution_timestamp"].eq(latest_timestamp)].drop(
        columns="_execution_timestamp"
    )


def _daily_calendar_status(results: pd.DataFrame, day: date) -> tuple[str, str]:
    summaries = results[
        results["record_type"].eq("KPI_SUMMARY")
        & results["period"].eq(day.isoformat())
    ]
    if summaries.empty:
        return "NOT_RUN", str(day.day)
    if summaries["ready_status"].eq("MISSING").any():
        return "MISSING", f"{day.day}\n{summaries['ready_status'].eq('MISSING').sum()} missing"
    executed = summaries[~summaries["ready_status"].eq("NOT_DUE")]
    if executed.empty:
        return "NOT_DUE", f"{day.day}\nNot due"
    if executed["status"].eq("FAILED").any():
        return "FAILED", f"{day.day}\n{executed['status'].eq('FAILED').sum()} failed"
    return "PASSED", f"{day.day}\nAll passed"


def _daily_validation_calendar(results: pd.DataFrame, month: date) -> tuple[pd.DataFrame, pd.DataFrame]:
    weeks = month_calendar.monthcalendar(month.year, month.month)
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cell_rows: list[dict[str, str]] = []
    status_rows: list[dict[str, str]] = []
    for week in weeks:
        cell_row: dict[str, str] = {}
        status_row: dict[str, str] = {}
        for label, day_number in zip(labels, week):
            if day_number == 0:
                cell_row[label] = ""
                status_row[label] = "EMPTY"
                continue
            status, label_value = _daily_calendar_status(
                results,
                date(month.year, month.month, day_number),
            )
            cell_row[label] = label_value
            status_row[label] = status
        cell_rows.append(cell_row)
        status_rows.append(status_row)
    return pd.DataFrame(cell_rows, columns=labels), pd.DataFrame(status_rows, columns=labels)


def _daily_calendar_html(calendar_values: pd.DataFrame, calendar_statuses: pd.DataFrame) -> str:
    weekdays = "".join(
        f'<div class="daily-calendar__weekday">{escape(column)}</div>'
        for column in calendar_values.columns
    )
    cells: list[str] = []
    for row_index in calendar_values.index:
        for column in calendar_values.columns:
            status = str(calendar_statuses.loc[row_index, column]).lower().replace("_", "-")
            value = str(calendar_values.loc[row_index, column])
            if not value:
                cells.append('<div class="daily-calendar__cell daily-calendar__cell--empty"></div>')
                continue
            day, *summary = value.split("\n", maxsplit=1)
            summary_html = f'<span class="daily-calendar__summary">{escape(summary[0])}</span>' if summary else ""
            cells.append(
                f'<div class="daily-calendar__cell daily-calendar__cell--{status}">'
                f'<span class="daily-calendar__date">{escape(day)}</span>{summary_html}</div>'
            )
    return f'<div class="daily-calendar">{weekdays}{"".join(cells)}</div>'


def _highlight_daily_calendar(value: object) -> str:
    styles = {
        "PASSED": "background-color: #dff4e7; color: #00563f; font-weight: 700",
        "FAILED": "background-color: #fff3cd; color: #664d03; font-weight: 700",
        "MISSING": "background-color: #f8d7da; color: #842029; font-weight: 700",
        "NOT_DUE": "background-color: #e9ecef; color: #495057",
        "NOT_RUN": "background-color: #f1f3f5; color: #6c757d",
    }
    return styles.get(str(value), "")


def _daily_calendar_results(result_data: pd.DataFrame) -> pd.DataFrame:
    if not DAILY_RESULT_FILE.exists():
        return _latest_execution_results(result_data)
    persisted = pd.read_csv(DAILY_RESULT_FILE)
    combined = pd.concat([persisted, result_data], ignore_index=True).drop_duplicates()
    return _latest_execution_results(combined)


def _date_only(value: object) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else "-"


def _display_rule_details(details: pd.DataFrame) -> pd.DataFrame:
    display = details.copy()
    if "data_ready_time" in display.columns:
        display["data_ready_time"] = display["data_ready_time"].map(_date_only)
    if {"actual_value", "rule_type"}.issubset(display.columns):
        percentage_rules = {
            "CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT",
            "DEVIATION_FROM_STANDARD_WITHIN_PERCENT",
        }
        percentage_mask = display["rule_type"].isin(percentage_rules)
        display["actual_value"] = display["actual_value"].astype(object)
        display.loc[percentage_mask, "actual_value"] = display.loc[
            percentage_mask, "actual_value"
        ].map(lambda value: f"{float(value):.1f}%" if pd.notna(value) else "-")
    return display


def _highlight_status(value: object) -> str:
    if value == "PASSED":
        return "background-color: #dff4e7; color: #00563f; font-weight: 700"
    if value == "FAILED":
        return "background-color: #fff3cd; color: #664d03; font-weight: 700"
    return ""


def _highlight_market_risk(value: object) -> str:
    return "background-color: #fff3cd; color: #664d03; font-weight: 700" if value and float(value) > 0 else ""


def _render_validation_results(
    channel: str,
    frequency: str,
    source_data: pd.DataFrame,
    result_data: pd.DataFrame,
    period: date,
    period_end: date | None = None,
) -> None:
    latest_results = _latest_execution_results(result_data)
    expected = _expected_kpis(
        channel,
        frequency,
        source_data,
        period,
        period_end,
        _business_calendar_service(),
    )
    if expected.empty:
        st.warning(
            f"No rule-configured EDL KPIs are available for {channel} {frequency}.",
            icon=":material/warning:",
        )
        return

    st.markdown('<div id="results"></div>', unsafe_allow_html=True)
    st.subheader("Results")
    filter_market, filter_period, filter_mvp, filter_kpi, filter_reset = st.columns([1, 1, 1, 2, 0.6])
    periods = sorted(latest_results["period"].dropna().astype(str).unique())
    preferred_period = period.isoformat()
    _apply_pending_overview_market(channel, frequency)
    _apply_filter_defaults(
        channel,
        frequency,
        periods,
        preferred_period,
        period_end.isoformat() if period_end is not None else None,
    )
    market = filter_market.selectbox(
        "Market",
        ["All markets", *sorted(expected["market"].unique())],
        key=_filter_key(channel, frequency, "market"),
        on_change=_clear_overview_drilldown,
        args=(channel, frequency),
    )
    if frequency == "Daily":
        filter_start, filter_end = filter_period.columns(2)
        selected_start = filter_start.date_input(
            "Start date",
            value=period,
            key=_filter_key(channel, frequency, "period_start"),
        )
        selected_end = filter_end.date_input(
            "End date",
            value=period_end or period,
            key=_filter_key(channel, frequency, "period_end"),
        )
        if selected_end < selected_start:
            st.error("Filter end date must be on or after the filter start date.", icon=":material/error:")
            return
        selected_results = _filter_period_range(latest_results, selected_start, selected_end)
        selected_period = f"{selected_start.isoformat()} to {selected_end.isoformat()}"
    else:
        selected_period = filter_period.selectbox(
            "Period",
            periods,
            index=periods.index(period.isoformat()) if period.isoformat() in periods else 0,
            key=_filter_key(channel, frequency, "period"),
        )
        selected_results = latest_results[latest_results["period"].eq(selected_period)]
    mvp_phase = filter_mvp.selectbox(
        "MVP1/MVP2",
        ["All phases", *sorted(expected["mvp_phase"].unique())],
        key=_filter_key(channel, frequency, "mvp"),
    )
    kpi_names = filter_kpi.multiselect(
        "KPI name",
        sorted(expected["kpi_name"].unique()),
        placeholder="All KPIs - search and select",
        key=_filter_key(channel, frequency, "kpi"),
    )
    filter_reset.button(
        "Reset filters",
        icon=":material/restart_alt:",
        on_click=_clear_filter_state,
        args=(channel, frequency),
        key=f"filter_{channel}_{frequency}_reset",
    )
    overview_base_market = st.session_state.get(_overview_previous_market_key(channel, frequency), market)
    filtered_expected = _filter_expected_kpis(expected, market, mvp_phase, kpi_names)
    overview_expected = _filter_expected_kpis(expected, overview_base_market, mvp_phase, kpi_names)
    if frequency == "Daily":
        filtered_expected = _filter_period_range(filtered_expected, selected_start, selected_end)
        overview_expected = _filter_period_range(overview_expected, selected_start, selected_end)
    key_columns = ["channel", "market", "kpi_id", "frequency"]
    if frequency == "Daily":
        key_columns.append("period")
    result_keys = filtered_expected[key_columns].drop_duplicates()
    filtered_results = selected_results.merge(
        result_keys,
        on=key_columns,
        how="inner",
    )
    metric_sets = _metric_kpi_sets(filtered_expected, filtered_results)
    metric_label = st.session_state.get(_metric_filter_key(channel, frequency), "All KPIs")
    metric_keys = metric_sets.get(metric_label, metric_sets["All KPIs"])[key_columns].drop_duplicates()
    scoped_results = filtered_results.merge(metric_keys, on=key_columns, how="inner")
    summary = scoped_results[scoped_results["record_type"].eq("KPI_SUMMARY")].copy()
    details = scoped_results[scoped_results["record_type"].eq("RULE")]
    summary = _sort_kpi_summary(summary)
    summary["data_ready_time"] = summary["data_ready_time"].map(_date_only)

    _summary_metrics(_metric_counts(filtered_expected, filtered_results), channel, frequency)

    overview_keys = overview_expected[key_columns].drop_duplicates()
    overview_results = selected_results.merge(
        overview_keys,
        on=key_columns,
        how="inner",
    )
    market_overview = _market_kpi_overview(overview_expected, overview_results, selected_period)
    st.session_state[_overview_data_key(channel, frequency)] = market_overview
    st.session_state[ACTIVE_WORKSPACE_KEY] = (channel, frequency)
    st.subheader("Market KPI overview")
    overview_event = st.dataframe(
        market_overview.style.map(
            _highlight_market_risk,
            subset=["Missing KPI", "Delayed KPI", "Validation Failed"],
        ),
        hide_index=True,
        key=_overview_selection_key(channel, frequency),
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Expected KPI": st.column_config.NumberColumn(format="%d"),
            "Ready KPI": st.column_config.NumberColumn(format="%d"),
            "Missing KPI": st.column_config.NumberColumn(format="%d"),
            "Not Due KPI": st.column_config.NumberColumn(format="%d"),
            "Delayed KPI": st.column_config.NumberColumn(format="%d"),
            "Validation Passed": st.column_config.NumberColumn(format="%d"),
            "Validation Failed": st.column_config.NumberColumn(format="%d"),
        },
    )
    selected_overview_rows = overview_event.selection.rows
    if selected_overview_rows:
        selected_overview_market = str(market_overview.iloc[selected_overview_rows[0]]["Market"])
        if market != selected_overview_market:
            previous_market_key = _overview_previous_market_key(channel, frequency)
            if previous_market_key not in st.session_state:
                st.session_state[previous_market_key] = market
            st.session_state[_pending_overview_market_key(channel, frequency)] = selected_overview_market
            st.rerun()

    st.markdown('<div id="kpi-summary"></div>', unsafe_allow_html=True)
    st.subheader("KPI summary")
    summary_event = st.dataframe(
        summary.reset_index(drop=True).style.map(_highlight_status, subset=["status"]),
        hide_index=True,
        key=_summary_selection_key(channel, frequency),
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "record_type": None,
            "kpi_id": None,
            "source_table": None,
            "aggregation_level": None,
            "aggregation_detail": None,
            "rule_id": None,
            "rule_type": None,
            "rule_order": None,
            "passed": None,
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
            "execution_date": None,
            "execution_timestamp": None,
        },
    )

    if summary.empty:
        st.warning("No KPI summary results were generated.", icon=":material/warning:")
        return

    selected_rows = summary_event.selection.rows
    if selected_rows:
        _remember_view_anchor(channel, frequency, "validation-rule-details")
    if frequency == "Daily" and not selected_rows:
        calendar_results = _filter_period_range(_daily_calendar_results(result_data), selected_start, selected_end)
        calendar_keys = metric_keys[key_columns].drop_duplicates()
        calendar_results = calendar_results.merge(calendar_keys, on=key_columns, how="inner")
        for calendar_month in _months_in_range(selected_start, selected_end):
            calendar_values, calendar_statuses = _daily_validation_calendar(
                calendar_results,
                calendar_month,
            )
            st.subheader(f"Daily validation calendar | {calendar_month.strftime('%B %Y')}")
            st.markdown(_daily_calendar_html(calendar_values, calendar_statuses), unsafe_allow_html=True)

    st.markdown('<div id="validation-rule-details"></div>', unsafe_allow_html=True)
    st.subheader("Validation rule details")
    if not selected_rows:
        st.info("Select a KPI Summary row to view its validation rule details.", icon=":material/info:")
    else:
        selected_summary = summary.iloc[selected_rows[0]]
        selected_details = details[
            (details["channel"].eq(selected_summary["channel"]))
            & (details["market"].eq(selected_summary["market"]))
            & (details["kpi_id"].eq(selected_summary["kpi_id"]))
            & (details["frequency"].eq(selected_summary["frequency"]))
            & (details["period"].eq(selected_summary["period"]))
            & (details["execution_timestamp"].eq(selected_summary["execution_timestamp"]))
        ]
        st.dataframe(
            _display_rule_details(selected_details).style.map(_highlight_status, subset=["status"]),
            hide_index=True,
            column_order=[
                "market",
                "kpi_name",
                "frequency",
                "rule_type",
                "rule_order",
                "period",
                "expected_ready_date",
                "data_ready_time",
                "ready_status",
                "ready_delay_days",
                "status",
                "actual_value",
                "previous_period_value",
                "threshold_percent",
                "standard_value",
                "baseline_source",
                "comparison_source",
                "comparison_level",
                "baseline_value",
                "comparison_value",
                "difference_value",
                "reason",
            ],
            column_config={
                "record_type": None,
                "channel": None,
                "kpi_id": None,
                "source_table": None,
                "aggregation_level": None,
                "aggregation_detail": None,
                "rule_id": None,
                "passed": None,
                "execution_date": None,
                "execution_timestamp": None,
            },
        )

    scroll_request = st.session_state.pop(_scroll_target_key(channel, frequency), None)
    if scroll_request:
        scroll_target, scroll_sequence = scroll_request
        _scroll_to(scroll_target, scroll_sequence)
    elif selected_rows:
        _scroll_to("validation-rule-details")
    else:
        _scroll_to(st.session_state.get(_last_view_anchor_key(channel, frequency), "results"))


def run_dashboard(data_provider: DashboardDataProvider) -> None:
    st.set_page_config(
        page_title="DKPI data readiness",
        page_icon=":material/analytics:",
        layout="wide",
    )
    _apply_brand_style()
    with st.sidebar:
        st.header("Validation workspace")
        channel = st.selectbox("Channel", list(CHANNEL_FREQUENCIES), key="channel")
        frequencies = CHANNEL_FREQUENCIES[channel]
        frequency = frequencies[0]
        if len(frequencies) > 1:
            frequency = st.segmented_control(
                "Frequency",
                frequencies,
                default="Monthly",
                required=True,
                key=f"frequency_{channel}",
                width="stretch",
            )

    st.markdown(
        f"""
        <div class="brand-shell">
          <h1>DKPI data readiness monitoring</h1>
          <p>Distribution KPI Validation Dashboard | {channel} | {frequency}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    workspace_key = _workspace_state_key(channel, frequency)
    workspace_data = st.session_state.get(workspace_key)
    with st.expander("Data files", expanded=workspace_data is None):
        uploaded_files = _data_files(channel, frequency)

    with st.sidebar:
        st.header(f"{channel} {frequency} inputs")
        default_period, default_end_period = _workspace_period_defaults(frequency, workspace_data)
        if frequency == "Daily":
            period = st.date_input(
                "Daily start date",
                value=default_period,
                key=f"period_{channel}_{frequency}",
            )
            end_period = st.date_input(
                "Daily end date (optional)",
                value=default_end_period,
                key=f"period_end_{channel}_{frequency}",
            )
        else:
            period = st.date_input(
                "Monthly period",
                value=default_period,
                key=f"period_{channel}_{frequency}",
            )
            end_period = None
        if frequency == "Daily":
            st.caption("Daily validation requires a Daily EDL source upload; Daily Anaplan and PBI uploads are optional comparison inputs.")
        else:
            st.caption("Defaults use local data files when no upload is provided.")
        run_clicked = st.button(
            f"Run {frequency} validation",
            type="primary",
            icon=":material/play_arrow:",
        )
        with st.expander("Configuration maintenance", icon=":material/settings:"):
            maintenance_label = "Generate EDL daily validation rules" if frequency == "Daily" else "Generate EDL monthly validation rules"
            if st.button(maintenance_label, icon=":material/rule:"):
                try:
                    if frequency == "Daily":
                        kpi_count, rule_count = _configure_edl_daily_validation_rules()
                        st.success(
                            f"Configured {rule_count} Daily rules for {kpi_count} KPIs.",
                            icon=":material/check_circle:",
                        )
                    else:
                        kpi_count, rule_count, mapping_count = _configure_edl_monthly_baseline_rules()
                        st.success(
                            f"Configured {rule_count} rules for {kpi_count} KPIs; added {mapping_count} source mappings.",
                            icon=":material/check_circle:",
                        )
                except Exception as exc:
                    st.error(f"Configuration generation failed: {exc}", icon=":material/error:")

    if run_clicked:
        try:
            with st.status("Running validation", expanded=False) as status:
                source_file = uploaded_files["source_file"]
                if frequency == "Daily" and source_file is None:
                    status.update(label="Daily EDL source file required", state="error")
                    st.error("Upload a Daily EDL source file before running Daily validation.", icon=":material/error:")
                    return
                validation_dates = _daily_validation_dates(period, end_period) if frequency == "Daily" else [period]
                source_data = _read_uploaded_table(source_file, DEFAULT_SOURCE_FILE)
                comparison_data: dict[str, pd.DataFrame] = {}
                standard_values_path = _standard_values_path(uploaded_files["standard_file"]) if frequency == "Monthly" else DAILY_STANDARD_FILE
                if frequency == "Monthly":
                    comparison_data = {
                        "ANAPLAN": _read_uploaded_table(uploaded_files["anaplan_file"], DEFAULT_ANAPLAN_FILE, header=None),
                        "PBI": _read_uploaded_table(uploaded_files["pbi_file"], DEFAULT_PBI_FILE),
                    }
                else:
                    if uploaded_files["anaplan_file"] is not None:
                        comparison_data["ANAPLAN"] = _read_uploaded_table(uploaded_files["anaplan_file"], DEFAULT_ANAPLAN_FILE, header=None)
                    if uploaded_files["pbi_file"] is not None:
                        comparison_data["PBI"] = _read_uploaded_table(uploaded_files["pbi_file"], DEFAULT_PBI_FILE)
                override_file = uploaded_files["override_file"]
                if override_file is not None:
                    comparison_data["OVERRIDE_TRACKER"] = _read_uploaded_table(
                        override_file,
                        DEFAULT_OVERRIDE_TRACKER_FILE,
                        sheet_name="Dataset",
                    )
                result_data = pd.concat(
                    [
                        _run_validation(
                            source_data,
                            standard_values_path,
                            validation_date,
                            channel,
                            frequency,
                            comparison_data,
                        )
                        for validation_date in validation_dates
                    ],
                    ignore_index=True,
                )
                st.session_state[workspace_key] = {
                    "source_data": source_data,
                    "result_data": result_data,
                    "period_start": period,
                    "period_end": end_period or period,
                }
                status.update(label="Validation complete", state="complete")
                st.rerun()
        except Exception as exc:
            st.error(f"Validation failed: {exc}", icon=":material/error:")
            return

    workspace_data = st.session_state.get(workspace_key)
    if workspace_data is not None and frequency == "Daily" and _workspace_period_changed(workspace_data, period, end_period):
        workspace_data = None
        st.session_state.pop(workspace_key, None)
    if workspace_data is None:
        if frequency == "Daily":
            st.info(
                "Upload Daily source files, select a daily period, then run validation.",
                icon=":material/info:",
            )
            return
        st.info(
            f"Upload files or use defaults, select a {frequency.lower()} period, then run validation.",
            icon=":material/info:",
        )
        return

    source_data = workspace_data["source_data"]
    result_data = KPIValidationService._normalize_status(workspace_data["result_data"])
    result_data = KPIValidationService._normalize_ready_status(result_data)
    workspace_data["result_data"] = result_data

    _render_validation_results(
        channel,
        frequency,
        source_data,
        result_data,
        workspace_data.get("period_start", period),
        workspace_data.get("period_end"),
    )


if __name__ == "__main__":
    run_dashboard(DashboardDataProvider(None))
