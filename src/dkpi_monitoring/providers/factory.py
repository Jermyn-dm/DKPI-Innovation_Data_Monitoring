from __future__ import annotations

from dkpi_monitoring.providers.base import DataProvider


class ProviderFactory:
    @staticmethod
    def create(provider_type: str, config: dict) -> DataProvider:
        raise NotImplementedError
