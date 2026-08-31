from __future__ import annotations

from typing import Any

from models import BusinessCalendarEntry
from repositories.base_config_repository import BaseConfigurationRepository, ConfigurationDataSource


class BusinessCalendarRepository(BaseConfigurationRepository):
    """Repository for market calendar records; it performs no date calculations."""

    def __init__(self, data_source: ConfigurationDataSource) -> None:
        self.data_source = data_source

    def load_kpi_configs(self) -> list[Any]:
        raise NotImplementedError

    def load_validation_rules(self) -> list[Any]:
        raise NotImplementedError

    def load_business_calendar(
        self,
        calendar_code: str | None = None,
        market: str | None = None,
    ) -> list[BusinessCalendarEntry]:
        records = self.data_source.read_table("calendar_config").to_dict("records")
        entries = [BusinessCalendarEntry.model_validate(row) for row in records]
        return [
            entry
            for entry in entries
            if (calendar_code is None or entry.calendar_code == calendar_code)
            and (market is None or entry.market == market)
        ]

    def validate_configuration(self) -> list[str]:
        return []
