from datetime import date

from dkpi_monitoring.calendar.service import BusinessCalendarService
from dkpi_monitoring.engine.readiness import KPIReadinessEvaluator, TargetAvailabilityParser
from dkpi_monitoring.models import BusinessCalendarConfig


def test_target_availability_parser_supports_configured_forms() -> None:
    assert TargetAvailabilityParser.parse("T+CD2") == {
        "anchor": "T",
        "offset": 2,
        "unit": "CD",
    }
    assert TargetAvailabilityParser.parse("T+2CD") == {
        "anchor": "T",
        "offset": 2,
        "unit": "CD",
    }


def test_target_availability_uses_calendar_day_fallback() -> None:
    evaluator = KPIReadinessEvaluator(BusinessCalendarService([]))
    assert evaluator._calculate_expected_ready_date(
        "T+CD2", "CN", date(2026, 7, 31)
    ) == date(2026, 8, 2)


def test_target_availability_uses_sg_business_days() -> None:
    calendar = BusinessCalendarService(
        [
            BusinessCalendarConfig("SG", date(2026, 8, 1), False),
            BusinessCalendarConfig("SG", date(2026, 8, 2), False),
            BusinessCalendarConfig("SG", date(2026, 8, 3), True),
            BusinessCalendarConfig("SG", date(2026, 8, 4), True),
            BusinessCalendarConfig("SG", date(2026, 8, 5), True),
        ]
    )
    evaluator = KPIReadinessEvaluator(calendar)

    assert evaluator._calculate_expected_ready_date(
        "M+3BD", "SG", date(2026, 7, 31)
    ) == date(2026, 8, 5)


def test_business_day_calculation_falls_back_when_calendar_coverage_is_missing() -> None:
    calendar = BusinessCalendarService(
        [BusinessCalendarConfig("SG", date(2026, 8, 3), True)]
    )

    assert calendar.add_business_days("SG", date(2026, 8, 3), 1) == date(2026, 8, 4)
