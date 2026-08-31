from __future__ import annotations

from collections import Counter
from models import BusinessCalendarEntry, KPIConfig, KPIValidationRule, SourceTableMapping


class ConfigurationValidationService:
    """Validates configuration metadata without executing monitoring logic."""

    def validate_configuration(
        self,
        kpi_configs: list[KPIConfig],
        validation_rules: list[KPIValidationRule],
        calendar_entries: list[BusinessCalendarEntry],
        source_mappings: list[SourceTableMapping] | None = None,
    ) -> list[str]:
        issues: list[str] = []
        issues.extend(self._duplicate_kpi_issues(kpi_configs))
        issues.extend(self._target_availability_issues(kpi_configs))
        issues.extend(self._validation_rule_issues(validation_rules, kpi_configs))
        issues.extend(self._calendar_reference_issues(kpi_configs, calendar_entries))
        issues.extend(self._source_mapping_issues(kpi_configs, source_mappings or []))
        return issues

    @staticmethod
    def _duplicate_kpi_issues(configs: list[KPIConfig]) -> list[str]:
        keys = [
            (item.channel, item.country_cd, item.kpi_id, item.kpi_name, item.effective_from)
            for item in configs
        ]
        return [f"Duplicate KPI configuration: {key}" for key, count in Counter(keys).items() if count > 1]

    @staticmethod
    def _target_availability_issues(configs: list[KPIConfig]) -> list[str]:
        return [
            f"Missing target availability: {item.channel}/{item.country_cd}/{item.kpi_id}"
            for item in configs
            if item.active and not item.target_availability
        ]

    @staticmethod
    def _validation_rule_issues(
        rules: list[KPIValidationRule],
        configs: list[KPIConfig],
    ) -> list[str]:
        config_keys = {(item.channel, item.country_cd, item.kpi_id, item.kpi_name) for item in configs}
        rule_ids: list[tuple[str, str, str, str, str, int, object]] = []
        issues: list[str] = []
        for rule in rules:
            key = (rule.channel, rule.market, rule.kpi_id, rule.kpi_name)
            if key not in config_keys:
                issues.append(f"Invalid validation rule KPI reference: {key}")
            rule_ids.append((*key, rule.rule_id, rule.rule_order, rule.effective_from))
        return issues + [f"Duplicate validation rule: {key}" for key, count in Counter(rule_ids).items() if count > 1]

    @staticmethod
    def _calendar_reference_issues(
        configs: list[KPIConfig],
        calendar_entries: list[BusinessCalendarEntry],
    ) -> list[str]:
        configured_markets = {entry.market for entry in calendar_entries}
        issues: list[str] = []
        for item in configs:
            if item.target_availability and "BD" in item.target_availability.upper() and item.country_cd not in configured_markets:
                issues.append(f"Missing calendar reference: {item.country_cd}")
        return issues

    @staticmethod
    def _source_mapping_issues(
        configs: list[KPIConfig],
        mappings: list[SourceTableMapping],
    ) -> list[str]:
        mapping_keys = {(mapping.source_table, mapping.market) for mapping in mappings}
        if not mappings:
            return [f"Invalid source mapping for {item.source_table}/{item.country_cd}" for item in configs if not item.source_table]
        return [
            f"Invalid source mapping for {item.source_table}/{item.country_cd}"
            for item in configs
            if (item.source_table, item.country_cd) not in mapping_keys
        ]
