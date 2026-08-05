from __future__ import annotations

from pathlib import Path

from dkpi_monitoring.providers.base import DataProvider
from dkpi_monitoring.providers.excel import ExcelProvider
from dkpi_monitoring.providers.databricks import DatabricksProvider


class ProviderFactory:
    @staticmethod
    def create(provider_type: str, config: dict) -> DataProvider:
        if provider_type == "excel":
            base_path = Path(config["base_path"])
            return ExcelProvider(base_path=base_path)
        if provider_type == "databricks":
            return DatabricksProvider(connection_string=config["connection_string"])
        raise ValueError(f"Unknown provider type: {provider_type}")
