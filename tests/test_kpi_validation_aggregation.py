from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from models import KPIValidationRule
from dkpi_monitoring.dashboard.app import _baseline_validation_rows, _daily_validation_rows, _metric_counts, _metric_kpi_sets, _sort_kpi_summary
from dkpi_monitoring.dashboard import app as dashboard_app
from dkpi_monitoring.calendar.service import BusinessCalendarService
from dkpi_monitoring.models import BusinessCalendarConfig
from services.kpi_validation_service import KPIValidationService


def test_kpi_summary_places_failed_rows_first_and_preserves_other_order() -> None:
    summary = pd.DataFrame(
        [
            {"kpi_id": "AG0001", "status": "PASSED"},
            {"kpi_id": "AG0002", "status": "FAILED"},
            {"kpi_id": "AG0003", "status": "PASSED"},
            {"kpi_id": "AG0004", "status": "FAILED"},
        ]
    )

    ordered = _sort_kpi_summary(summary)

    assert ordered["kpi_id"].tolist() == ["AG0002", "AG0004", "AG0001", "AG0003"]


def test_market_level_validation_aggregates_sub_channels() -> None:
    rule = KPIValidationRule(
        channel="Agency",
        market="SG",
        kpi_id="AG0016",
        kpi_name="Active agents",
        frequency="Monthly",
        source_table="agency_fact",
        rule_id="RULE_VALUE_GREATER_THAN_ZERO",
        rule_type="VALUE_GREATER_THAN_ZERO",
        rule_order=1,
        value_column="VALUE",
    )
    source_data = pd.DataFrame(
        [
            {
                "BU_CODE": "SG",
                "DISTRIBUTION_CHANNEL": "MAG",
                "CHANNEL_CODE": "MAG",
                "MODE": "M",
                "PERIOD": "2024-07-31",
                "ACCOUNT_ID": "AG0016",
                "VALUE": 100,
            },
            {
                "BU_CODE": "SG",
                "DISTRIBUTION_CHANNEL": "MFA",
                "CHANNEL_CODE": "MFA",
                "MODE": "M",
                "PERIOD": "2024-07-31",
                "ACCOUNT_ID": "AG0016",
                "VALUE": 200,
            },
            {
                "BU_CODE": "ID",
                "DISTRIBUTION_CHANNEL": "Agency",
                "CHANNEL_CODE": "Agency",
                "MODE": "M",
                "PERIOD": "2024-07-31",
                "ACCOUNT_ID": "AG0016",
                "VALUE": 999,
            },
        ]
    )

    results = KPIValidationService().validate(
        [rule],
        source_data,
        date(2024, 7, 31),
        execution_timestamp=datetime(2024, 8, 5, 9, 0, 0),
    )

    rule_result = results[0]
    assert rule_result["status"] == "PASSED"
    assert rule_result["actual_value"] == 300.0
    assert rule_result["aggregation_level"] == "Agency"
    assert rule_result["aggregation_detail"] == "ALL"


def test_sub_channel_breakdown_uses_matching_market_rows() -> None:
    rule = KPIValidationRule(
        channel="Agency",
        market="SG",
        kpi_id="AG0016",
        kpi_name="Active agents",
        frequency="Monthly",
        source_table="agency_fact",
        rule_id="RULE_RECORD_EXISTS",
        rule_type="RECORD_EXISTS",
        rule_order=1,
    )
    source_data = pd.DataFrame(
        [
            {"BU_CODE": "SG", "DISTRIBUTION_CHANNEL": "MAG", "CHANNEL_CODE": "MAG", "MODE": "M", "PERIOD": "2024-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 100},
            {"BU_CODE": "SG", "DISTRIBUTION_CHANNEL": "MFA", "CHANNEL_CODE": "MFA", "MODE": "M", "PERIOD": "2024-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 200},
            {"BU_CODE": "ID", "DISTRIBUTION_CHANNEL": "Agency", "CHANNEL_CODE": "Agency", "MODE": "M", "PERIOD": "2024-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 999},
        ]
    )

    breakdown = KPIValidationService.sub_channel_breakdown(rule, source_data, date(2024, 7, 31))

    assert sorted(breakdown["sub_channel"].tolist()) == ["MAG", "MFA"]
    assert breakdown["total_value"].sum() == 300


def test_result_persistence_overwrites_same_day_and_keeps_other_days(tmp_path: Path) -> None:
    rule = KPIValidationRule(
        channel="Agency",
        market="SG",
        kpi_id="AG0016",
        kpi_name="Active agents",
        frequency="Monthly",
        source_table="agency_fact",
        rule_id="RULE_RECORD_EXISTS",
        rule_type="RECORD_EXISTS",
    )
    source_data = pd.DataFrame(
        [{"BU_CODE": "SG", "MODE": "M", "PERIOD": "2024-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 1}]
    )
    output_path = tmp_path / "results.csv"
    service = KPIValidationService()
    period = date(2024, 7, 31)

    service.validate_and_save([rule], source_data, period, output_path=output_path, execution_timestamp=datetime(2026, 8, 28, 9, 0, 0))
    service.validate_and_save([rule], source_data, period, output_path=output_path, execution_timestamp=datetime(2026, 8, 28, 10, 0, 0))
    service.validate_and_save([rule], source_data, period, output_path=output_path, execution_timestamp=datetime(2026, 8, 31, 9, 0, 0))

    persisted = pd.read_csv(output_path)
    assert set(persisted["execution_date"]) == {"2026-08-28", "2026-08-31"}
    assert not persisted["execution_timestamp"].eq("2026-08-28T09:00:00").any()
    assert persisted["execution_timestamp"].eq("2026-08-28T10:00:00").sum() == 2
    assert persisted["execution_timestamp"].eq("2026-08-31T09:00:00").sum() == 2


def test_result_persistence_normalizes_legacy_market_aggregation_level(tmp_path: Path) -> None:
    output_path = tmp_path / "results.csv"
    pd.DataFrame(
        [{"aggregation_level": " market ", "channel": "Agency", "market": "SG"}]
    ).to_csv(output_path, index=False)

    normalized = KPIValidationService._normalize_aggregation_level(pd.read_csv(output_path))

    assert normalized.loc[0, "aggregation_level"] == "Agency"


def test_result_persistence_skips_malformed_historical_rows(tmp_path: Path) -> None:
    output_path = tmp_path / "results.csv"
    output_path.write_text(
        ",".join(KPIValidationService.RESULT_COLUMNS)
        + "\n"
        + "RULE,Agency,SG,AG0016,Active agents,Monthly,agency_fact,Agency,ALL,RULE_RECORD_EXISTS,RECORD_EXISTS,1,2026-08-31,2026-09-02,2026-09-02T00:00:00,2026-09-10,,NOT_DUE,,PASSED,True,1,,,,,,,,,,Record exists\n"
        + "bad,row,with,too,many,columns,that,should,be,skipped,because,it,has,more,than,thirty,two,fields,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17\n",
        encoding="utf-8",
    )
    rule = KPIValidationRule(
        channel="Agency",
        market="SG",
        kpi_id="AG0016",
        kpi_name="Active agents",
        frequency="Monthly",
        source_table="agency_fact",
        rule_id="RULE_RECORD_EXISTS",
        rule_type="RECORD_EXISTS",
        rule_order=1,
    )
    source_data = pd.DataFrame(
        [{"BU_CODE": "SG", "MODE": "M", "PERIOD": "2026-08-31", "ACCOUNT_ID": "AG0016", "VALUE": 1}]
    )

    KPIValidationService().validate_and_save(
        [rule],
        source_data,
        date(2026, 8, 31),
        output_path=output_path,
        target_availability="M+1CD",
        execution_timestamp=datetime(2026, 9, 2),
    )

    persisted = pd.read_csv(output_path)
    assert len(persisted.columns) == len(KPIValidationService.RESULT_COLUMNS)
    assert not persisted["record_type"].eq("bad").any()


def test_result_persistence_handles_empty_historical_file(tmp_path: Path) -> None:
    output_path = tmp_path / "results.csv"
    output_path.write_text("", encoding="utf-8")
    rule = KPIValidationRule(
        channel="Agency",
        market="SG",
        kpi_id="AG0016",
        kpi_name="Active agents",
        frequency="Monthly",
        source_table="agency_fact",
        rule_id="RULE_RECORD_EXISTS",
        rule_type="RECORD_EXISTS",
        rule_order=1,
    )
    source_data = pd.DataFrame(
        [{"BU_CODE": "SG", "MODE": "M", "PERIOD": "2026-08-31", "ACCOUNT_ID": "AG0016", "VALUE": 1}]
    )

    KPIValidationService().validate_and_save(
        [rule],
        source_data,
        date(2026, 8, 31),
        output_path=output_path,
        target_availability="M+1CD",
        execution_timestamp=datetime(2026, 9, 2),
    )

    persisted = pd.read_csv(output_path)
    assert persisted["record_type"].tolist() == ["RULE", "KPI_SUMMARY"]


def test_no_record_after_due_uses_missing_ready_status() -> None:
    rule = KPIValidationRule(
        channel="Agency",
        market="JP",
        kpi_id="AG0016",
        kpi_name="Active agents",
        frequency="Monthly",
        source_table="agency_fact",
        rule_id="RULE_RECORD_EXISTS",
        rule_type="RECORD_EXISTS",
    )
    source_data = pd.DataFrame(
        [{"BU_CODE": "CN", "MODE": "M", "PERIOD": "2026-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 1}]
    )

    result = KPIValidationService().validate(
        [rule],
        source_data,
        date(2026, 7, 31),
        target_availability="M+1CD",
        execution_timestamp=datetime(2026, 9, 1),
    )[0]

    assert result["ready_status"] == "MISSING"
    assert result["status"] == "FAILED"


def test_legacy_delayed_ready_status_normalizes_to_missing() -> None:
    results = pd.DataFrame([{"ready_status": "DELAYED", "status": "FAILED"}])

    normalized = KPIValidationService._normalize_ready_status(results)

    assert normalized.loc[0, "ready_status"] == "MISSING"


def test_metric_counts_follow_expected_kpi_and_rule_statuses() -> None:
    expected = pd.DataFrame(
        [
            {"channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "kpi_name": "Active agents", "mvp_phase": "MVP1"},
            {"channel": "Agency", "market": "SG", "kpi_id": "AG0018", "frequency": "Monthly", "kpi_name": "Three-month active agents", "mvp_phase": "MVP2"},
        ]
    )
    results = pd.DataFrame(
        [
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "status": "PASSED", "ready_status": "READY_DELAYED"},
            {"record_type": "RULE", "channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "rule_id": "RULE_RECORD_EXISTS", "status": "PASSED"},
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "SG", "kpi_id": "AG0018", "frequency": "Monthly", "status": "FAILED", "ready_status": "MISSING"},
            {"record_type": "RULE", "channel": "Agency", "market": "SG", "kpi_id": "AG0018", "frequency": "Monthly", "rule_id": "RULE_RECORD_EXISTS", "status": "FAILED"},
        ]
    )

    metrics = _metric_counts(expected, results)

    assert metrics == {
        "Expected KPI": 2,
        "Ready KPI": 1,
        "Missing KPI": 1,
        "Not Due KPI": 0,
        "Delayed KPI": 1,
        "Validation Passed": 1,
        "Validation Failed": 1,
    }


def test_not_due_kpis_are_not_counted_as_validation_passed_or_failed() -> None:
    expected = pd.DataFrame(
        [
            {"channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "kpi_name": "Active agents", "mvp_phase": "MVP1"},
        ]
    )
    results = pd.DataFrame(
        [
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "status": "PASSED", "ready_status": "NOT_DUE"},
        ]
    )

    metrics = _metric_counts(expected, results)

    assert metrics["Not Due KPI"] == 1
    assert metrics["Validation Passed"] == 0
    assert metrics["Validation Failed"] == 0


def test_not_due_kpis_with_records_count_as_ready_not_not_due() -> None:
    expected = pd.DataFrame(
        [
            {"channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "kpi_name": "Active agents", "mvp_phase": "MVP1"},
        ]
    )
    results = pd.DataFrame(
        [
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "status": "PASSED", "ready_status": "READY_EARLY"},
            {"record_type": "RULE", "channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "rule_id": "RULE_RECORD_EXISTS", "status": "PASSED"},
        ]
    )

    metrics = _metric_counts(expected, results)

    assert metrics["Ready KPI"] == 1
    assert metrics["Not Due KPI"] == 0
    assert metrics["Validation Passed"] == 1
    assert metrics["Validation Failed"] == 0


def test_not_due_validation_runs_all_rules_for_early_data() -> None:
    record_exists_rule = KPIValidationRule(
        channel="Agency",
        market="SG",
        kpi_id="AG0016",
        kpi_name="Active agents",
        frequency="Monthly",
        source_table="agency_fact",
        rule_id="RULE_RECORD_EXISTS",
        rule_type="RECORD_EXISTS",
        rule_order=1,
    )
    value_rule = record_exists_rule.model_copy(
        update={
            "rule_id": "RULE_VALUE_GREATER_THAN_ZERO",
            "rule_type": "VALUE_GREATER_THAN_ZERO",
            "rule_order": 2,
            "value_column": "VALUE",
        }
    )
    source_data = pd.DataFrame(
        [{"BU_CODE": "SG", "MODE": "M", "PERIOD": "2026-08-31", "ACCOUNT_ID": "AG0016", "VALUE": 1}]
    )

    results = KPIValidationService().validate(
        [record_exists_rule, value_rule],
        source_data,
        date(2026, 8, 31),
        target_availability="M+10CD",
        execution_timestamp=datetime(2026, 9, 2),
    )

    assert results[0]["rule_id"] == "RULE_RECORD_EXISTS"
    assert results[0]["status"] == "PASSED"
    assert results[0]["ready_status"] == "READY_EARLY"
    assert [result["rule_id"] for result in results] == [
        "RULE_RECORD_EXISTS",
        "RULE_VALUE_GREATER_THAN_ZERO",
        "KPI_RESULT",
    ]
    assert results[1]["status"] == "PASSED"
    assert results[2]["ready_status"] == "READY_EARLY"


def test_expected_kpi_filter_supports_multiple_selected_kpi_names() -> None:
    from dkpi_monitoring.dashboard.app import _filter_expected_kpis

    expected = pd.DataFrame(
        [
            {"market": "SG", "mvp_phase": "MVP1", "kpi_name": "Active agents"},
            {"market": "SG", "mvp_phase": "MVP2", "kpi_name": "New agents"},
            {"market": "CN", "mvp_phase": "MVP1", "kpi_name": "Premium"},
        ]
    )

    filtered = _filter_expected_kpis(
        expected,
        "All markets",
        "All phases",
        ["Active agents", "Premium"],
    )

    assert filtered["kpi_name"].tolist() == ["Active agents", "Premium"]


def test_market_kpi_overview_uses_the_same_metric_definitions() -> None:
    from dkpi_monitoring.dashboard.app import _market_kpi_overview

    expected = pd.DataFrame(
        [
            {"channel": "Agency", "market": "CN", "kpi_id": "AG0016", "frequency": "Monthly"},
            {"channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly"},
        ]
    )
    results = pd.DataFrame(
        [
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "CN", "kpi_id": "AG0016", "frequency": "Monthly", "status": "PASSED", "ready_status": "READY_ON_TIME"},
            {"record_type": "RULE", "channel": "Agency", "market": "CN", "kpi_id": "AG0016", "frequency": "Monthly", "rule_id": "RULE_RECORD_EXISTS", "status": "PASSED"},
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "status": "FAILED", "ready_status": "MISSING"},
            {"record_type": "RULE", "channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "rule_id": "RULE_RECORD_EXISTS", "status": "FAILED"},
        ]
    )

    overview = _market_kpi_overview(expected, results, "2026-07-31")

    assert overview[["Market", "Expected KPI", "Ready KPI", "Missing KPI"]].to_dict("records") == [
        {"Market": "CN", "Expected KPI": 1, "Ready KPI": 1, "Missing KPI": 0},
        {"Market": "SG", "Expected KPI": 1, "Ready KPI": 0, "Missing KPI": 1},
    ]


def test_market_kpi_overview_keeps_metric_columns_when_empty() -> None:
    from dkpi_monitoring.dashboard.app import _market_kpi_overview

    overview = _market_kpi_overview(
        pd.DataFrame(columns=["channel", "market", "kpi_id", "frequency"]),
        pd.DataFrame(columns=["record_type", "channel", "market", "kpi_id", "frequency"]),
        "2026-08-30",
    )

    assert [
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
    ] == overview.columns.tolist()


def test_reset_filters_sets_widget_defaults_and_clears_selection_state(monkeypatch) -> None:
    state = {
        "filter_Agency_Monthly_market": "SG",
        "filter_Agency_Monthly_period": "2026-06-30",
        "filter_Agency_Monthly_mvp": "MVP1",
        "filter_Agency_Monthly_kpi": ["Active agents"],
        "metric_filter_Agency_Monthly": "Missing KPI",
        "overview_previous_market_Agency_Monthly": "CN",
    }
    monkeypatch.setattr(dashboard_app, "st", SimpleNamespace(session_state=state))

    dashboard_app._clear_filter_state("Agency", "Monthly")
    dashboard_app._apply_filter_defaults("Agency", "Monthly", ["2026-06-30", "2026-07-31"], "2026-07-31")

    assert state["filter_Agency_Monthly_market"] == "All markets"
    assert state["filter_Agency_Monthly_period"] == "2026-07-31"
    assert state["filter_Agency_Monthly_mvp"] == "All phases"
    assert state["filter_Agency_Monthly_kpi"] == []
    assert "metric_filter_Agency_Monthly" not in state
    assert "overview_previous_market_Agency_Monthly" not in state
    assert state["overview_selection_revision_Agency_Monthly"] == 1
    assert state["summary_selection_revision_Agency_Monthly"] == 1


def test_period_filter_defaults_to_current_validation_period(monkeypatch) -> None:
    state = {}
    monkeypatch.setattr(dashboard_app, "st", SimpleNamespace(session_state=state))

    dashboard_app._apply_filter_defaults("Agency", "Monthly", ["2026-06-30", "2026-07-31"], "2026-07-31")

    assert state["filter_Agency_Monthly_period"] == "2026-07-31"


def test_daily_filter_reset_uses_date_values_for_date_inputs(monkeypatch) -> None:
    state = {}
    monkeypatch.setattr(dashboard_app, "st", SimpleNamespace(session_state=state))

    dashboard_app._clear_filter_state("Agency", "Daily")
    dashboard_app._apply_filter_defaults(
        "Agency",
        "Daily",
        ["2026-08-27", "2026-08-28"],
        "2026-08-27",
        "2026-08-28",
    )

    assert state["filter_Agency_Daily_period_start"] == date(2026, 8, 27)
    assert state["filter_Agency_Daily_period_end"] == date(2026, 8, 28)


def test_daily_filter_defaults_follow_changed_sidebar_dates(monkeypatch) -> None:
    state = {
        "filter_Agency_Daily_period_start": date(2026, 9, 29),
        "filter_Agency_Daily_period_end": date(2026, 9, 29),
    }
    monkeypatch.setattr(dashboard_app, "st", SimpleNamespace(session_state=state))

    dashboard_app._apply_filter_defaults(
        "Agency",
        "Daily",
        ["2026-08-30", "2026-09-29"],
        "2026-08-30",
        "2026-08-30",
    )

    assert state["filter_Agency_Daily_period_start"] == date(2026, 8, 30)
    assert state["filter_Agency_Daily_period_end"] == date(2026, 8, 30)


def test_daily_workspace_period_change_marks_results_stale() -> None:
    workspace_data = {
        "period_start": date(2026, 9, 29),
        "period_end": date(2026, 9, 29),
    }

    assert dashboard_app._workspace_period_changed(
        workspace_data,
        date(2026, 8, 30),
        None,
    )
    assert not dashboard_app._workspace_period_changed(
        workspace_data,
        date(2026, 9, 29),
        date(2026, 9, 29),
    )


def test_daily_workspace_period_defaults_restore_saved_dates() -> None:
    workspace_data = {
        "period_start": date(2026, 8, 30),
        "period_end": date(2026, 9, 2),
    }

    period, period_end = dashboard_app._workspace_period_defaults("Daily", workspace_data)

    assert period == date(2026, 8, 30)
    assert period_end == date(2026, 9, 2)
    assert not dashboard_app._workspace_period_changed(workspace_data, period, period_end)


def test_monthly_workspace_period_defaults_restore_saved_date() -> None:
    workspace_data = {
        "period_start": date(2026, 8, 31),
        "period_end": date(2026, 8, 31),
    }

    period, period_end = dashboard_app._workspace_period_defaults("Monthly", workspace_data)

    assert period == date(2026, 8, 31)
    assert period_end is None


def test_programmatic_overview_market_selection_is_not_cleared_as_manual_filter_change(monkeypatch) -> None:
    state = {"filter_Agency_Monthly_market": "All markets"}
    monkeypatch.setattr(dashboard_app, "st", SimpleNamespace(session_state=state))

    dashboard_app._select_overview_market("Agency", "Monthly", "SG")
    dashboard_app._clear_overview_drilldown("Agency", "Monthly")

    assert state["filter_Agency_Monthly_market"] == "SG"
    assert "overview_previous_market_Agency_Monthly" not in state
    assert state["summary_selection_revision_Agency_Monthly"] == 1
    assert "overview_selection_revision_Agency_Monthly" not in state


def test_pending_overview_market_applies_before_market_widget_render(monkeypatch) -> None:
    state = {"pending_overview_market_Agency_Daily": "CN"}
    monkeypatch.setattr(dashboard_app, "st", SimpleNamespace(session_state=state))

    dashboard_app._apply_pending_overview_market("Agency", "Daily")

    assert state["filter_Agency_Daily_market"] == "CN"
    assert state["scroll_target_Agency_Daily"] == ("kpi-summary", 1)
    assert "pending_overview_market_Agency_Daily" not in state


def test_scroll_to_uses_anchor_scroll_into_view(monkeypatch) -> None:
    rendered: dict[str, object] = {}
    monkeypatch.setattr(
        dashboard_app,
        "st",
        SimpleNamespace(html=lambda content, unsafe_allow_javascript: rendered.update({"content": content})),
    )

    dashboard_app._scroll_to("kpi-summary")

    assert "getElementById('kpi-summary')" in str(rendered["content"])
    assert "scrollIntoView" in str(rendered["content"])
    assert "requestAnimationFrame" in str(rendered["content"])


def test_repeated_metric_selection_uses_new_scroll_request(monkeypatch) -> None:
    state: dict[str, object] = {}
    monkeypatch.setattr(dashboard_app, "st", SimpleNamespace(session_state=state))

    dashboard_app._select_metric("Agency", "Daily", "Missing KPI")
    first_request = state["scroll_target_Agency_Daily"]
    dashboard_app._select_metric("Agency", "Daily", "Validation Failed")
    second_request = state["scroll_target_Agency_Daily"]

    assert first_request == ("kpi-summary", 1)
    assert second_request == ("kpi-summary", 2)


def test_last_view_anchor_is_scoped_by_frequency(monkeypatch) -> None:
    state: dict[str, object] = {}
    monkeypatch.setattr(dashboard_app, "st", SimpleNamespace(session_state=state))

    dashboard_app._remember_view_anchor("Agency", "Monthly", "validation-rule-details")
    dashboard_app._remember_view_anchor("Agency", "Daily", "kpi-summary")

    assert state["last_view_anchor_Agency_Monthly"] == "validation-rule-details"
    assert state["last_view_anchor_Agency_Daily"] == "kpi-summary"


def test_scroll_request_remembers_last_view_anchor(monkeypatch) -> None:
    state: dict[str, object] = {}
    monkeypatch.setattr(dashboard_app, "st", SimpleNamespace(session_state=state))

    dashboard_app._request_scroll("Agency", "Monthly", "kpi-summary")

    assert state["last_view_anchor_Agency_Monthly"] == "kpi-summary"
    assert state["scroll_target_Agency_Monthly"] == ("kpi-summary", 1)


def test_source_comparison_fails_when_one_sg_sub_channel_differs() -> None:
    rule = KPIValidationRule(
        channel="Agency",
        market="SG",
        kpi_id="AG0016",
        kpi_name="Active agents",
        frequency="Monthly",
        source_table="agency_fact",
        rule_id="RULE_EDL_VS_ANAPLAN",
        rule_type="EDL_MATCH_ANAPLAN",
        rule_order=101,
        value_column="VALUE",
        comparison_source="ANAPLAN",
    )
    source_data = pd.DataFrame(
        [
            {"BU_CODE": "SG", "CHANNEL_CODE": "SG-MAG", "MODE": "M1", "PERIOD": "2026-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 314},
            {"BU_CODE": "SG", "CHANNEL_CODE": "SG-MFA", "MODE": "M1", "PERIOD": "2026-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 690},
        ]
    )
    service = KPIValidationService()
    service.comparison_data = {
        "ANAPLAN": pd.DataFrame(
            [
                {"unit": "SG-MAG", "kpi_id": "AG0016", "period": "2026-07-31", "comparison_value": 314},
                {"unit": "SG-MFA", "kpi_id": "AG0016", "period": "2026-07-31", "comparison_value": 691},
            ]
        )
    }

    result = service.validate([rule], source_data, date(2026, 7, 31), execution_timestamp=datetime(2026, 8, 5))[0]

    assert result["status"] == "FAILED"
    assert result["comparison_level"] == "SUB_CHANNEL"
    assert result["baseline_value"] == 1004.0
    assert result["comparison_value"] == 1005.0
    assert result["difference_value"] == -1.0
    assert "SG-MFA" in result["reason"]


def test_source_comparison_uses_id_sub_channel_grain() -> None:
    rule = KPIValidationRule(
        channel="Agency",
        market="ID",
        kpi_id="AG0016",
        kpi_name="Active agents",
        frequency="Monthly",
        source_table="agency_fact",
        rule_id="RULE_EDL_VS_PBI",
        rule_type="EDL_MATCH_PBI",
        rule_order=102,
        value_column="VALUE",
        comparison_source="PBI",
    )
    source_data = pd.DataFrame(
        [
            {"BU_CODE": "ID", "CHANNEL_CODE": "GA", "MODE": "M1", "PERIOD": "2026-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 1817},
            {"BU_CODE": "ID", "CHANNEL_CODE": "BRANCH", "MODE": "M1", "PERIOD": "2026-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 1178},
        ]
    )
    service = KPIValidationService()
    service.comparison_data = {
        "PBI": pd.DataFrame(
            [
                {"unit": "ID-GA", "kpi_id": "AG0016", "period": "2026-07-31", "comparison_value": 1817},
                {"unit": "ID-BRANCH", "kpi_id": "AG0016", "period": "2026-07-31", "comparison_value": 1179},
            ]
        )
    }

    result = service.validate([rule], source_data, date(2026, 7, 31), execution_timestamp=datetime(2026, 8, 5))[0]

    assert result["status"] == "FAILED"
    assert result["comparison_level"] == "SUB_CHANNEL"
    assert result["baseline_value"] == 2995.0
    assert result["comparison_value"] == 2996.0
    assert result["difference_value"] == -1.0
    assert "ID-BRANCH" in result["reason"]


def test_downstream_market_names_normalize_to_configured_market_codes() -> None:
    service = KPIValidationService()
    service.kpi_mapping = pd.DataFrame(
        [
            {"kpi_id": "AG0020", "anaplan_kpi": "Net Case Count - Agency", "pbi_kpi": "Net Case Count - Agency"},
        ]
    )
    anaplan = pd.DataFrame(
        [
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            ["Hong Kong", "Net Case Count - Agency", "Jul 26", 10],
            ["Vietnam", "Net Case Count - Agency", "Jul 26", 20],
            ["Cambodia", "Net Case Count - Agency", "Jul 26", 30],
        ]
    )
    pbi = pd.DataFrame(
        [
            {"KPI": "Net Case Count - Agency", "L2 Agency_Channel: Code": "Hong Kong", "Value": 10, "Timestamp": "7/1/2026"},
            {"KPI": "Net Case Count - Agency", "L2 Agency_Channel: Code": "Vietnam", "Value": 20, "Timestamp": "7/1/2026"},
            {"KPI": "Net Case Count - Agency", "L2 Agency_Channel: Code": "Cambodia", "Value": 30, "Timestamp": "7/1/2026"},
        ]
    )

    normalized_anaplan = service._normalize_comparison_source("ANAPLAN", anaplan)
    normalized_pbi = service._normalize_comparison_source("PBI", pbi)

    assert normalized_anaplan[["unit", "period", "comparison_value"]].to_dict("records") == [
        {"unit": "HK", "period": "2026-07-31", "comparison_value": 10},
        {"unit": "KH", "period": "2026-07-31", "comparison_value": 30},
        {"unit": "VN", "period": "2026-07-31", "comparison_value": 20},
    ]
    assert normalized_pbi[["unit", "period", "comparison_value"]].to_dict("records") == [
        {"unit": "HK", "period": "2026-07-31", "comparison_value": 10},
        {"unit": "KH", "period": "2026-07-31", "comparison_value": 30},
        {"unit": "VN", "period": "2026-07-31", "comparison_value": 20},
    ]


def test_downstream_kpi_name_mapping_is_case_insensitive() -> None:
    service = KPIValidationService()
    service.kpi_mapping = pd.DataFrame(
        [
            {
                "kpi_id": "AG0029_12",
                "anaplan_kpi": "Total agent headcount (end of period) in Top-tier Agents",
                "pbi_kpi": "Total agent headcount (end of period) in Top-tier Agents",
            },
        ]
    )
    anaplan = pd.DataFrame(
        [
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            ["Hong Kong", "Total agent headcount (end of period) in Top-tier agents", "Jul 26", 4005],
        ]
    )
    pbi = pd.DataFrame(
        [
            {
                "KPI": "Total agent headcount (end of period) in Top-tier agents",
                "L2 Agency_Channel: Code": "Hong Kong",
                "Value": 4005,
                "Timestamp": "7/1/2026",
            },
        ]
    )

    normalized_anaplan = service._normalize_comparison_source("ANAPLAN", anaplan)
    normalized_pbi = service._normalize_comparison_source("PBI", pbi)

    assert normalized_anaplan.to_dict("records") == [
        {"unit": "HK", "kpi_id": "AG0029_12", "period": "2026-07-31", "comparison_value": 4005}
    ]
    assert normalized_pbi.to_dict("records") == [
        {"unit": "HK", "kpi_id": "AG0029_12", "period": "2026-07-31", "comparison_value": 4005}
    ]


def test_daily_anaplan_format_uses_daily_period_and_swapped_kpi_columns() -> None:
    service = KPIValidationService()
    service.kpi_mapping = pd.DataFrame(
        [{"kpi_id": "AG0016", "anaplan_kpi": "# of 1-Month Active Agents", "pbi_kpi": "# of 1-Month Active Agents"}]
    )
    anaplan = pd.DataFrame(
        [
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, "CY"],
            ["China", "1 Aug 26", "# of 1-Month Active Agents", 149],
        ]
    )

    normalized = service._normalize_comparison_source("ANAPLAN", anaplan)

    assert normalized.to_dict("records") == [
        {"unit": "CN", "kpi_id": "AG0016", "period": "2026-08-01", "comparison_value": 149}
    ]


def test_monthly_anaplan_format_uses_month_period_and_swapped_kpi_columns() -> None:
    service = KPIValidationService()
    service.kpi_mapping = pd.DataFrame(
        [{"kpi_id": "AG0016", "anaplan_kpi": "# of 1-Month Active Agents", "pbi_kpi": "# of 1-Month Active Agents"}]
    )
    anaplan = pd.DataFrame(
        [
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, "CY"],
            ["Agency", "Aug 26", "# of 1-Month Active Agents", 5146],
        ]
    )

    normalized = service._normalize_comparison_source("ANAPLAN", anaplan)

    assert normalized.to_dict("records") == [
        {"unit": "Agency", "kpi_id": "AG0016", "period": "2026-08-31", "comparison_value": 5146}
    ]


def test_daily_pbi_format_uses_line_items_and_daily_timestamp() -> None:
    service = KPIValidationService()
    service.kpi_mapping = pd.DataFrame(
        [{"kpi_id": "AG0016", "anaplan_kpi": "# of 1-Month Active Agents", "pbi_kpi": "# of 1-Month Active Agents"}]
    )
    pbi = pd.DataFrame(
        [
            {
                "Line Items": "# of 1-Month Active Agents",
                "L2 Agency_Channel: Code": "All",
                "Value": 149,
                "Timestamp": "2026-08-01",
                "Source": "Agency Comparatives - Daily",
            }
        ]
    )

    normalized = service._normalize_comparison_source("PBI", pbi)

    assert normalized.to_dict("records") == [
        {"unit": "All", "kpi_id": "AG0016", "period": "2026-08-01", "comparison_value": 149}
    ]


def test_source_comparison_passes_when_both_downstream_values_match_completed_override() -> None:
    anaplan_rule = KPIValidationRule(
        channel="Agency", market="CN", kpi_id="AG0020", kpi_name="Net case count", frequency="Monthly",
        source_table="agency_fact", rule_id="RULE_EDL_VS_ANAPLAN", rule_type="EDL_MATCH_ANAPLAN",
        rule_order=101, value_column="VALUE", comparison_source="ANAPLAN",
    )
    pbi_rule = anaplan_rule.model_copy(update={"rule_id": "RULE_EDL_VS_PBI", "rule_type": "EDL_MATCH_PBI", "rule_order": 102, "comparison_source": "PBI"})
    source_data = pd.DataFrame([
        {"BU_CODE": "CN", "MODE": "M1", "PERIOD": "2026-07-31", "ACCOUNT_ID": "AG0020", "VALUE": 3500},
    ])
    service = KPIValidationService()
    service.comparison_data = {
        "ANAPLAN": pd.DataFrame([{"unit": "CN", "kpi_id": "AG0020", "period": "2026-07-31", "comparison_value": 3575}]),
        "PBI": pd.DataFrame([{"unit": "CN", "kpi_id": "AG0020", "period": "2026-07-31", "comparison_value": 3575}]),
        "OVERRIDE_TRACKER": pd.DataFrame([{"unit": "CN", "kpi_id": "AG0020", "frequency": "Monthly", "period": "2026-07-31", "override_value": 3575}]),
    }

    results = service.validate([anaplan_rule, pbi_rule], source_data, date(2026, 7, 31), execution_timestamp=datetime(2026, 8, 5))

    assert [result["status"] for result in results[:2]] == ["PASSED", "PASSED"]
    assert all("EDL mismatch" in result["reason"] and "Override tracker and PBI" in result["reason"] for result in results[:2])


def test_override_tracker_uses_completed_values_and_month_end_period() -> None:
    raw_tracker = pd.DataFrame(
        [
            {"BU": "China", "DISTRIBUTION_CHANNEL": "Agency", "PERIOD": "2026-07-01", "ACCOUNT_ID": "AG0020", "CY(Override)": 3575, "Granularity": "monthly", "Status": "Completed"},
            {"BU": "China", "DISTRIBUTION_CHANNEL": "Agency", "PERIOD": "2026-07-01", "ACCOUNT_ID": "AG0021", "CY(Override)": 100, "Granularity": "monthly", "Status": "awaiting anaplan set up"},
        ]
    )

    normalized = KPIValidationService()._normalize_comparison_source("OVERRIDE_TRACKER", raw_tracker)

    assert normalized.to_dict("records") == [
        {"unit": "CN", "kpi_id": "AG0020", "frequency": "Monthly", "period": "2026-07-31", "override_value": 3575}
    ]


def test_generated_edl_monthly_rules_include_downstream_comparison_rules() -> None:
    kpis = pd.DataFrame(
        [
            {
                "channel": "Agency",
                "country_cd": "CN",
                "kpi_id": "AG0020",
                "kpi_name": "Net Case Count - Agency",
                "source_table": "agency_fact",
                "effective_from": None,
                "effective_to": None,
            }
        ]
    )

    generated = _baseline_validation_rows(kpis)

    rule_bindings = generated[["rule_id", "rule_type", "rule_order", "value_column", "comparison_source"]].to_dict("records")
    assert rule_bindings == [
        {"rule_id": "RULE_RECORD_EXISTS", "rule_type": "RECORD_EXISTS", "rule_order": 1, "value_column": None, "comparison_source": None},
        {"rule_id": "RULE_VALUE_NOT_NULL", "rule_type": "VALUE_NOT_NULL", "rule_order": 2, "value_column": "VALUE", "comparison_source": None},
        {"rule_id": "RULE_VALUE_GREATER_THAN_ZERO", "rule_type": "VALUE_GREATER_THAN_ZERO", "rule_order": 3, "value_column": "VALUE", "comparison_source": None},
        {"rule_id": "RULE_EDL_VS_ANAPLAN", "rule_type": "EDL_MATCH_ANAPLAN", "rule_order": 101, "value_column": "VALUE", "comparison_source": "ANAPLAN"},
        {"rule_id": "RULE_EDL_VS_PBI", "rule_type": "EDL_MATCH_PBI", "rule_order": 102, "value_column": "VALUE", "comparison_source": "PBI"},
    ]


def test_generated_edl_daily_rules_use_daily_rule_set() -> None:
    kpis = pd.DataFrame(
        [
            {
                "channel": "Agency",
                "country_cd": "CN",
                "kpi_id": "AG0020",
                "kpi_name": "Net Case Count - Agency",
                "source_table": "agency_fact",
                "effective_from": None,
                "effective_to": None,
            }
        ]
    )

    generated = _daily_validation_rows(kpis)

    assert generated[["frequency", "rule_id", "rule_type", "rule_order", "value_column", "comparison_source"]].to_dict("records") == [
        {"frequency": "Daily", "rule_id": "RULE_RECORD_EXISTS", "rule_type": "RECORD_EXISTS", "rule_order": 1, "value_column": None, "comparison_source": None},
        {"frequency": "Daily", "rule_id": "RULE_VALUE_NOT_NULL", "rule_type": "VALUE_NOT_NULL", "rule_order": 2, "value_column": "VALUE", "comparison_source": None},
        {"frequency": "Daily", "rule_id": "RULE_VALUE_GREATER_THAN_ZERO", "rule_type": "VALUE_GREATER_THAN_ZERO", "rule_order": 3, "value_column": "VALUE", "comparison_source": None},
        {"frequency": "Daily", "rule_id": "RULE_EDL_VS_ANAPLAN", "rule_type": "EDL_MATCH_ANAPLAN", "rule_order": 101, "value_column": "VALUE", "comparison_source": "ANAPLAN"},
        {"frequency": "Daily", "rule_id": "RULE_EDL_VS_PBI", "rule_type": "EDL_MATCH_PBI", "rule_order": 102, "value_column": "VALUE", "comparison_source": "PBI"},
    ]


def test_daily_configuration_loads_from_daily_config_directory() -> None:
    kpis, rules = dashboard_app._configured_kpis("Agency", "Daily")

    assert len(kpis) == 67
    assert {rule.frequency for rule in rules} == {"Daily"}
    assert {rule.rule_type for rule in rules} == {
        "RECORD_EXISTS",
        "VALUE_NOT_NULL",
        "VALUE_GREATER_THAN_ZERO",
        "EDL_MATCH_ANAPLAN",
        "EDL_MATCH_PBI",
    }


def test_monthly_configuration_loads_from_monthly_config_directory() -> None:
    data_source = dashboard_app._configuration_data_source("Monthly")
    kpi_data = data_source.read_table("kpi_config")
    rule_data = data_source.read_table("kpi_validation_rule_config")
    monthly_kpis, monthly_rules = dashboard_app._configured_kpis("Agency", "Monthly")

    expected_kpi_data = pd.read_excel(dashboard_app.MONTHLY_CONFIG_DIR / "kpi_config.xlsx")
    expected_rule_data = pd.read_excel(dashboard_app.MONTHLY_CONFIG_DIR / "kpi_validation_rule_config.xlsx")

    assert kpi_data.equals(expected_kpi_data)
    assert rule_data.equals(expected_rule_data)
    assert len(monthly_kpis) > 0
    assert {rule.frequency for rule in monthly_rules} == {"Monthly"}


def test_daily_sg_hk_expect_data_only_on_business_days() -> None:
    calendar = BusinessCalendarService(
        [
            BusinessCalendarConfig("SG", date(2026, 9, 1), True),
            BusinessCalendarConfig("SG", date(2026, 9, 6), False),
            BusinessCalendarConfig("HK", date(2026, 9, 1), True),
            BusinessCalendarConfig("HK", date(2026, 9, 6), False),
        ]
    )

    assert dashboard_app._daily_market_expects_data("Daily", "SG", date(2026, 9, 1), calendar)
    assert not dashboard_app._daily_market_expects_data("Daily", "SG", date(2026, 9, 6), calendar)
    assert dashboard_app._daily_market_expects_data("Daily", "HK", date(2026, 9, 1), calendar)
    assert not dashboard_app._daily_market_expects_data("Daily", "HK", date(2026, 9, 6), calendar)
    assert dashboard_app._daily_market_expects_data("Daily", "CN", date(2026, 9, 6), calendar)


def test_daily_sg_hk_target_availability_uses_business_days() -> None:
    assert dashboard_app._target_availability_for_run("Daily", "SG", "T+CD1") == "T+BD1"
    assert dashboard_app._target_availability_for_run("Daily", "HK", "T+1CD") == "T+1BD"
    assert dashboard_app._target_availability_for_run("Daily", "CN", "T+CD1") == "T+CD1"


def test_daily_result_path_is_independent_from_monthly_result_path() -> None:
    assert dashboard_app._result_file_for_frequency("Daily").as_posix() == "data/results/daily/kpi_validation_results.csv"
    assert dashboard_app._result_file_for_frequency("Monthly") is None


def test_daily_date_range_supports_one_date_and_inclusive_range() -> None:
    assert dashboard_app._daily_validation_dates(date(2026, 8, 27), None) == [date(2026, 8, 27)]
    assert dashboard_app._daily_validation_dates(date(2026, 8, 27), date(2026, 8, 29)) == [
        date(2026, 8, 27),
        date(2026, 8, 28),
        date(2026, 8, 29),
    ]


def test_daily_date_range_rejects_end_before_start() -> None:
    with pytest.raises(ValueError, match="on or after"):
        dashboard_app._daily_validation_dates(date(2026, 8, 29), date(2026, 8, 27))


def test_daily_calendar_range_includes_each_month() -> None:
    assert dashboard_app._months_in_range(date(2026, 8, 31), date(2026, 10, 1)) == [
        date(2026, 8, 1),
        date(2026, 9, 1),
        date(2026, 10, 1),
    ]


def test_daily_validation_calendar_prioritizes_missing_then_failed_then_passed() -> None:
    results = pd.DataFrame(
        [
            {"record_type": "KPI_SUMMARY", "period": "2026-08-01", "ready_status": "READY_ON_TIME", "status": "PASSED"},
            {"record_type": "KPI_SUMMARY", "period": "2026-08-02", "ready_status": "MISSING", "status": "FAILED"},
            {"record_type": "KPI_SUMMARY", "period": "2026-08-03", "ready_status": "READY_ON_TIME", "status": "FAILED"},
            {"record_type": "KPI_SUMMARY", "period": "2026-08-04", "ready_status": "NOT_DUE", "status": "PASSED"},
        ]
    )

    values, statuses = dashboard_app._daily_validation_calendar(results, date(2026, 8, 1))

    cells = values.to_numpy().ravel().tolist()
    assert "1\nAll passed" in cells
    assert "2\n1 missing" in cells
    assert "3\n1 failed" in cells
    assert "4\nNot due" in cells
    assert statuses.loc[0, "Sat"] == "PASSED"
    assert statuses.loc[0, "Sun"] == "MISSING"
    assert statuses.loc[1, "Mon"] == "FAILED"
    assert statuses.loc[1, "Tue"] == "NOT_DUE"


def test_daily_expected_kpis_are_not_limited_to_uploaded_edl_markets() -> None:
    source_data = pd.DataFrame(
        [{"BU_CODE": "HK", "MODE": "D", "PERIOD": "2026-08-27", "ACCOUNT_ID": "AG0016", "VALUE": 1}]
    )

    expected = dashboard_app._expected_kpis(
        "Agency",
        "Daily",
        source_data,
        date(2026, 8, 27),
        calendar_service=dashboard_app._business_calendar_service(),
    )

    assert {"CN", "JP"}.issubset(set(expected["market"]))


def test_monthly_expected_kpis_are_not_limited_to_uploaded_edl_markets() -> None:
    source_data = pd.DataFrame(
        [{"BU_CODE": "SG", "MODE": "M", "PERIOD": "2026-07-31", "ACCOUNT_ID": "AG0016", "VALUE": 1}]
    )

    expected = dashboard_app._expected_kpis(
        "Agency",
        "Monthly",
        source_data,
        date(2026, 7, 31),
        calendar_service=dashboard_app._business_calendar_service(),
    )

    assert {"CN", "HK", "ID", "JP", "KH", "MM", "MY", "PH", "SG", "VN"}.issubset(
        set(expected["market"])
    )
    assert len(expected) > len(expected[expected["market"].eq("SG")])


def test_daily_expected_kpis_count_each_date_and_exclude_sg_hk_non_working_days() -> None:
    source_data = pd.DataFrame(
        [{"BU_CODE": "CN", "MODE": "D", "PERIOD": "2026-08-27", "ACCOUNT_ID": "AG0016", "VALUE": 1}]
    )
    calendar = BusinessCalendarService(
        [
            BusinessCalendarConfig("SG", date(2026, 8, 27), True),
            BusinessCalendarConfig("SG", date(2026, 8, 28), False),
            BusinessCalendarConfig("HK", date(2026, 8, 27), True),
            BusinessCalendarConfig("HK", date(2026, 8, 28), False),
        ]
    )

    expected = dashboard_app._expected_kpis(
        "Agency",
        "Daily",
        source_data,
        date(2026, 8, 27),
        date(2026, 8, 28),
        calendar,
    )

    by_market = expected.groupby("market").size().to_dict()
    assert by_market["SG"] == 7
    assert by_market["HK"] == 7
    assert by_market["CN"] == 10
    assert expected["period"].nunique() == 2


def test_daily_metric_sets_keep_each_kpi_day_for_drilldown() -> None:
    expected = pd.DataFrame(
        [
            {"channel": "Agency", "market": "CN", "kpi_id": "AG0016", "frequency": "Daily", "period": "2026-08-27"},
            {"channel": "Agency", "market": "CN", "kpi_id": "AG0016", "frequency": "Daily", "period": "2026-08-28"},
        ]
    )
    results = pd.DataFrame(
        [
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "CN", "kpi_id": "AG0016", "frequency": "Daily", "period": "2026-08-27", "status": "PASSED", "ready_status": "READY_ON_TIME"},
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "CN", "kpi_id": "AG0016", "frequency": "Daily", "period": "2026-08-28", "status": "FAILED", "ready_status": "MISSING"},
            {"record_type": "RULE", "channel": "Agency", "market": "CN", "kpi_id": "AG0016", "frequency": "Daily", "period": "2026-08-27", "rule_id": "RULE_RECORD_EXISTS", "status": "PASSED"},
            {"record_type": "RULE", "channel": "Agency", "market": "CN", "kpi_id": "AG0016", "frequency": "Daily", "period": "2026-08-28", "rule_id": "RULE_RECORD_EXISTS", "status": "FAILED"},
        ]
    )

    metric_sets = _metric_kpi_sets(expected, results)

    assert metric_sets["Validation Passed"]["period"].tolist() == ["2026-08-27"]
    assert metric_sets["Validation Failed"]["period"].tolist() == ["2026-08-28"]