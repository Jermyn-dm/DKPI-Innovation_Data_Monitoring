from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from models import KPIValidationRule
from dkpi_monitoring.dashboard.app import _metric_counts
from services.kpi_validation_service import KPIValidationService


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
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "SG", "kpi_id": "AG0018", "frequency": "Monthly", "status": "FAILED", "ready_status": "DELAYED"},
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
            {"record_type": "KPI_SUMMARY", "channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "status": "FAILED", "ready_status": "DELAYED"},
            {"record_type": "RULE", "channel": "Agency", "market": "SG", "kpi_id": "AG0016", "frequency": "Monthly", "rule_id": "RULE_RECORD_EXISTS", "status": "FAILED"},
        ]
    )

    overview = _market_kpi_overview(expected, results, "2026-07-31")

    assert overview[["Market", "Expected KPI", "Ready KPI", "Missing KPI"]].to_dict("records") == [
        {"Market": "CN", "Expected KPI": 1, "Ready KPI": 1, "Missing KPI": 0},
        {"Market": "SG", "Expected KPI": 1, "Ready KPI": 0, "Missing KPI": 1},
    ]