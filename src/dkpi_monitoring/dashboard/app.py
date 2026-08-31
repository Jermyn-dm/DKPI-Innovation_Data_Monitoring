from __future__ import annotations

from datetime import date, timedelta
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
DEFAULT_SOURCE_FILE = Path("data/source/Agency_data_checking_UC.csv")
DEFAULT_STANDARD_FILE = Path("data/reference/kpi_standard_values.xlsx")
VALIDATION_RULE_FILE = CONFIG_DIR / "kpi_validation_rule_config.xlsx"
SOURCE_MAPPING_FILE = CONFIG_DIR / "source_table_mapping.xlsx"
BASELINE_RULES = [
    ("RULE_RECORD_EXISTS", "RECORD_EXISTS", 1, None, "KPI source record must exist"),
    ("RULE_VALUE_NOT_NULL", "VALUE_NOT_NULL", 2, "VALUE", "KPI value must not be null"),
    ("RULE_VALUE_GREATER_THAN_ZERO", "VALUE_GREATER_THAN_ZERO", 3, "VALUE", "KPI value must be greater than zero"),
]
CHANNEL_FREQUENCIES = {
    "Agency": ["Monthly", "Daily"],
    "Banca": ["Monthly", "Daily"],
    "Risk": ["Monthly"],
}
ACTIVE_WORKSPACE_KEY = "active_validation_workspace"


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
        </style>
        """,
        unsafe_allow_html=True,
    )


def _previous_month_end(today: date | None = None) -> date:
    value = pd.Timestamp(today or date.today())
    return (value.replace(day=1).date() - timedelta(days=1))


def _read_uploaded_table(uploaded_file: object | None, default_path: Path) -> pd.DataFrame:
    if uploaded_file is None:
        if default_path.suffix.lower() == ".csv":
            return pd.read_csv(default_path)
        return pd.read_excel(default_path)

    name = getattr(uploaded_file, "name", "")
    if name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def _standard_values_path(uploaded_file: object | None) -> Path | None:
    if uploaded_file is None:
        return DEFAULT_STANDARD_FILE
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        return Path(temp_file.name)


def _business_calendar_service() -> BusinessCalendarService:
    calendar_data = pd.read_excel(CONFIG_DIR / "calendar_config.xlsx")
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


def _configured_kpis(channel: str, frequency: str) -> tuple[list, list]:
    data_source = ExcelConfigurationDataSource(CONFIG_DIR)
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


def _eligible_edl_monthly_kpis() -> pd.DataFrame:
    kpi_data = pd.read_excel(CONFIG_DIR / "kpi_config.xlsx")
    return kpi_data[
        kpi_data["kpi_id"].notna()
        & kpi_data["monthly"].astype(str).str.strip().str.upper().eq("Y")
        & kpi_data["derivation logic"].astype(str).str.strip().str.upper().eq("EDL")
    ].copy()


def _baseline_validation_rows(kpis: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for kpi in kpis.to_dict("records"):
        for rule_id, rule_type, rule_order, value_column, remark in BASELINE_RULES:
            rows.append(
                {
                    "channel": kpi["channel"],
                    "market": kpi["country_cd"],
                    "kpi_id": kpi["kpi_id"],
                    "kpi_name": kpi["kpi_name"],
                    "frequency": "Monthly",
                    "source_table": kpi["source_table"],
                    "rule_id": rule_id,
                    "rule_type": rule_type,
                    "rule_order": rule_order,
                    "value_column": value_column,
                    "threshold_percent": None,
                    "standard_value": None,
                    "enabled": "Y",
                    "effective_from": kpi.get("effective_from"),
                    "effective_to": kpi.get("effective_to"),
                    "remark": remark,
                }
            )
    return pd.DataFrame(rows)


def _upsert_baseline_validation_rules(kpis: pd.DataFrame) -> int:
    existing = pd.read_excel(VALIDATION_RULE_FILE)
    baseline = _baseline_validation_rows(kpis)
    baseline_rule_ids = {rule[0] for rule in BASELINE_RULES}
    baseline_keys = set(
        zip(
            baseline["market"].astype(str),
            baseline["kpi_id"].astype(str),
            baseline["frequency"].astype(str),
            baseline["rule_id"].astype(str),
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
        keep.append(row.get("rule_id") not in baseline_rule_ids or key not in baseline_keys)
    updated = pd.concat([existing.loc[keep], baseline], ignore_index=True)
    updated.to_excel(VALIDATION_RULE_FILE, index=False)
    return len(baseline)


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


def _run_validation(
    source_data: pd.DataFrame,
    standard_values_path: Path | None,
    period: date,
    channel: str,
    frequency: str,
) -> pd.DataFrame:
    kpis, rules = _configured_kpis(channel, frequency)
    if "BU_CODE" in source_data.columns:
        source_markets = {
            str(value).strip()
            for value in source_data["BU_CODE"].dropna().unique()
            if str(value).strip()
        }
        if source_markets:
            kpis = [kpi for kpi in kpis if kpi.country_cd in source_markets]
            rules = [rule for rule in rules if rule.market in source_markets]
    service = KPIValidationService(standard_values_path)
    calendar_service = _business_calendar_service()
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
                target_availability=kpi.target_availability,
                calendar_service=calendar_service,
            )
        )
    return pd.DataFrame(all_results)


def _expected_kpis(channel: str, frequency: str, source_data: pd.DataFrame) -> pd.DataFrame:
    kpis, _ = _configured_kpis(channel, frequency)
    if "BU_CODE" in source_data.columns:
        source_markets = set(source_data["BU_CODE"].dropna().astype(str).str.strip())
        kpis = [kpi for kpi in kpis if kpi.country_cd in source_markets]
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
    summary = results[results["record_type"].eq("KPI_SUMMARY")][
        key_columns + ["status", "ready_status"]
    ].drop_duplicates(key_columns)
    exists_rule = results[
        results["record_type"].eq("RULE") & results["rule_id"].eq("RULE_RECORD_EXISTS")
    ][key_columns + ["status"]].drop_duplicates(key_columns).rename(columns={"status": "record_exists_status"})
    metrics = expected.merge(summary, on=key_columns, how="left").merge(exists_rule, on=key_columns, how="left")
    record_exists = metrics["record_exists_status"].eq("PASSED")
    return {
        "All KPIs": metrics,
        "Expected KPI": metrics,
        "Ready KPI": metrics[record_exists],
        "Missing KPI": metrics[metrics["ready_status"].eq("DELAYED") & ~record_exists],
        "Not Due KPI": metrics[metrics["ready_status"].eq("NOT_DUE")],
        "Delayed KPI": metrics[metrics["ready_status"].eq("READY_DELAYED") & record_exists],
        "Validation Passed": metrics[metrics["status"].eq("PASSED")],
        "Validation Failed": metrics[
            metrics["status"].notna() & ~metrics["status"].isin(["PASSED", "NOT_DUE"])
        ],
    }


def _metric_counts(expected: pd.DataFrame, results: pd.DataFrame) -> dict[str, int]:
    metric_sets = _metric_kpi_sets(expected, results)
    return {label: len(rows) for label, rows in metric_sets.items() if label != "All KPIs"}


def _market_kpi_overview(expected: pd.DataFrame, results: pd.DataFrame, period: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for market, market_expected in expected.groupby("market", sort=True):
        key_columns = ["channel", "market", "kpi_id", "frequency"]
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
    return pd.DataFrame(rows)


def _metric_filter_key(channel: str, frequency: str) -> str:
    return f"metric_filter_{channel}_{frequency}"


def _scroll_target_key(channel: str, frequency: str) -> str:
    return f"scroll_target_{channel}_{frequency}"


def _select_metric(channel: str, frequency: str, label: str) -> None:
    st.session_state[_metric_filter_key(channel, frequency)] = label
    st.session_state.pop(f"summary_selection_{channel}_{frequency}", None)
    st.session_state[_scroll_target_key(channel, frequency)] = "kpi-summary"


def _select_overview_market(channel: str, frequency: str, market: str) -> None:
    st.session_state[f"filter_{channel}_{frequency}_market"] = market
    st.session_state.pop(_metric_filter_key(channel, frequency), None)
    st.session_state.pop(f"summary_selection_{channel}_{frequency}", None)
    st.session_state[_scroll_target_key(channel, frequency)] = "kpi-summary"


def _overview_previous_market_key(channel: str, frequency: str) -> str:
    return f"overview_previous_market_{channel}_{frequency}"


def _clear_overview_drilldown(channel: str, frequency: str) -> None:
    st.session_state.pop(_overview_previous_market_key(channel, frequency), None)
    st.session_state.pop(f"market_overview_selection_{channel}_{frequency}", None)


def _overview_data_key(channel: str, frequency: str) -> str:
    return f"market_overview_data_{channel}_{frequency}"


def _apply_overview_selection() -> None:
    workspace = st.session_state.get(ACTIVE_WORKSPACE_KEY)
    if not workspace:
        return
    channel, frequency = workspace
    selection = st.session_state.get(f"market_overview_selection_{channel}_{frequency}", {})
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
        st.session_state[f"filter_{channel}_{frequency}_market"] = previous_market
        st.session_state.pop(_metric_filter_key(channel, frequency), None)
        st.session_state.pop(f"summary_selection_{channel}_{frequency}", None)


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
    prefix = f"filter_{channel}_{frequency}_"
    for suffix in ("market", "mvp", "kpi"):
        st.session_state.pop(f"{prefix}{suffix}", None)
    st.session_state.pop(_metric_filter_key(channel, frequency), None)
    st.session_state.pop(f"summary_selection_{channel}_{frequency}", None)
    st.session_state.pop(_overview_previous_market_key(channel, frequency), None)
    st.session_state.pop(f"market_overview_selection_{channel}_{frequency}", None)


def _scroll_to(anchor: str) -> None:
    st.html(
        f"<script>window.parent.location.hash = '{anchor}';</script>",
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

    with st.sidebar:
        st.header(f"{channel} {frequency} inputs")
        source_file = st.file_uploader("Source file", type=["csv", "xlsx"])
        standard_file = st.file_uploader("Standard value file", type=["xlsx"])
        period = st.date_input(
            "Monthly period" if frequency == "Monthly" else "Daily period",
            value=_previous_month_end() if frequency == "Monthly" else date.today(),
            key=f"period_{channel}_{frequency}",
        )
        st.caption("Defaults use local files in data/source and data/reference.")
        run_clicked = st.button(
            f"Run {frequency} validation",
            type="primary",
            icon=":material/play_arrow:",
        )
        with st.expander("Configuration maintenance", icon=":material/settings:"):
            if st.button("Generate EDL monthly baseline rules", icon=":material/rule:"):
                try:
                    kpi_count, rule_count, mapping_count = _configure_edl_monthly_baseline_rules()
                    st.success(
                        f"Configured {rule_count} rules for {kpi_count} KPIs; added {mapping_count} source mappings.",
                        icon=":material/check_circle:",
                    )
                except Exception as exc:
                    st.error(f"Configuration generation failed: {exc}", icon=":material/error:")

    workspace_key = _workspace_state_key(channel, frequency)
    if run_clicked:
        try:
            with st.status("Running validation", expanded=False) as status:
                source_data = _read_uploaded_table(source_file, DEFAULT_SOURCE_FILE)
                result_data = _run_validation(
                    source_data,
                    _standard_values_path(standard_file),
                    period,
                    channel,
                    frequency,
                )
                st.session_state[workspace_key] = {
                    "source_data": source_data,
                    "result_data": result_data,
                }
                status.update(label="Validation complete", state="complete")
        except Exception as exc:
            st.error(f"Validation failed: {exc}", icon=":material/error:")
            return

    workspace_data = st.session_state.get(workspace_key)
    if workspace_data is None:
        st.info(
            f"Upload files or use defaults, select a {frequency.lower()} period, then run validation.",
            icon=":material/info:",
        )
        return

    source_data = workspace_data["source_data"]
    result_data = workspace_data["result_data"]

    latest_results = _latest_execution_results(result_data)
    expected = _expected_kpis(channel, frequency, source_data)
    if expected.empty:
        st.warning(
            f"No rule-configured EDL KPIs are available for {channel} {frequency}.",
            icon=":material/warning:",
        )
        return

    st.subheader("Results")
    filter_market, filter_period, filter_mvp, filter_kpi, filter_reset = st.columns([1, 1, 1, 2, 0.6])
    market = filter_market.selectbox(
        "Market",
        ["All markets", *sorted(expected["market"].unique())],
        key=f"filter_{channel}_{frequency}_market",
        on_change=_clear_overview_drilldown,
        args=(channel, frequency),
    )
    periods = sorted(latest_results["period"].dropna().astype(str).unique())
    selected_period = filter_period.selectbox(
        "Period",
        periods,
        index=periods.index(period.isoformat()) if period.isoformat() in periods else 0,
    )
    mvp_phase = filter_mvp.selectbox(
        "MVP1/MVP2",
        ["All phases", *sorted(expected["mvp_phase"].unique())],
        key=f"filter_{channel}_{frequency}_mvp",
    )
    kpi_names = filter_kpi.multiselect(
        "KPI name",
        sorted(expected["kpi_name"].unique()),
        placeholder="All KPIs - search and select",
        key=f"filter_{channel}_{frequency}_kpi",
    )
    filter_reset.button(
        "Reset filters",
        icon=":material/restart_alt:",
        on_click=_clear_filter_state,
        args=(channel, frequency),
        key=f"filter_{channel}_{frequency}_reset",
    )
    filtered_expected = _filter_expected_kpis(expected, market, mvp_phase, kpi_names)
    key_columns = ["channel", "market", "kpi_id", "frequency"]
    result_keys = filtered_expected[key_columns].drop_duplicates()
    filtered_results = latest_results[latest_results["period"].eq(selected_period)].merge(
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
    summary["data_ready_time"] = summary["data_ready_time"].map(_date_only)

    _summary_metrics(_metric_counts(filtered_expected, filtered_results), channel, frequency)

    market_overview = _market_kpi_overview(filtered_expected, filtered_results, selected_period)
    st.session_state[_overview_data_key(channel, frequency)] = market_overview
    st.session_state[ACTIVE_WORKSPACE_KEY] = (channel, frequency)
    st.subheader("Market KPI overview")
    st.dataframe(
        market_overview.style.map(
            _highlight_market_risk,
            subset=["Missing KPI", "Delayed KPI", "Validation Failed"],
        ),
        hide_index=True,
        key=f"market_overview_selection_{channel}_{frequency}",
        on_select=_apply_overview_selection,
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

    st.markdown('<div id="kpi-summary"></div>', unsafe_allow_html=True)
    st.subheader("KPI summary")
    summary_event = st.dataframe(
        summary.reset_index(drop=True).style.map(_highlight_status, subset=["status"]),
        hide_index=True,
        key=f"summary_selection_{channel}_{frequency}",
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
            "execution_date": None,
            "execution_timestamp": None,
        },
    )

    if summary.empty:
        st.warning("No KPI summary results were generated.", icon=":material/warning:")
        return

    selected_rows = summary_event.selection.rows
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

    scroll_target = st.session_state.pop(_scroll_target_key(channel, frequency), None)
    if scroll_target:
        _scroll_to(scroll_target)
    elif selected_rows:
        _scroll_to("validation-rule-details")


if __name__ == "__main__":
    run_dashboard(DashboardDataProvider(None))
