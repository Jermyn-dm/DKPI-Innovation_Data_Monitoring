# Architecture Design

## Source of Truth
This document is aligned with `docs/01_PRD.md` and serves as the architecture blueprint for the DKPI Data Readiness Monitoring platform.

## Core Architecture
The architecture is built around a configuration-driven monitoring engine with abstracted data providers, a reusable business calendar service, and a Streamlit dashboard for visualization.

### Logical Layers
- Data Source Layer
- Configuration Layer
- Business Calendar Layer
- KPI Rule Engine
- Monitoring Engine
- Dashboard Layer

## Data Source Layer
- Provides an abstraction over data source implementations.
- Supports MVP Excel provider and future Databricks provider.
- Ensures business logic remains unchanged when provider changes.

## Configuration Layer
- Loads KPI configurations, ready rules, business calendars, and source table mappings.
- Uses configuration metadata to drive monitoring logic.
- Supports Excel files in MVP and future Databricks-backed configuration tables.

The Configuration Repository owns configuration concerns. It loads and normalizes configuration data, validates it, resolves active KPI definitions, effective-dated ready rules, business calendars, and source mappings, and returns typed domain objects to the monitoring engine. Providers own only physical source access and provider-level normalization; they do not resolve business configuration or apply readiness logic.

## Business Calendar Layer
- Encapsulates market-specific business day rules.
- Supports public holidays and weekends.
- Provides business-day and calendar-day calculation functions.

## KPI Rule Engine
- Parses readiness rules such as `M+3BD`, `M+5CD`, `D+1BD`.
- Calculates expected ready dates.
- Determines KPI status based on configurable readiness conditions.

## Monitoring Engine
- Orchestrates end-to-end monitoring execution.
- Reads config, retrieves source data, evaluates readiness, and persists results.
- Supports daily and monthly KPI monitoring.
- Emits monitoring result records for dashboard and historical trend calculation.

## Monitoring Result Storage Design
- Stores KPI monitoring results in a dedicated result repository.
- Persists fields: channel, market, KPI name, frequency, expected ready date, actual ready date, status, missing reason, record count, evaluation details, execution timestamp.
- Supports recent result retrieval and historical trend queries.
- Enables MVP1 traceability through execution metadata; full result version history is deferred to V2.
- Allows persistence in MVP storage (file or in-memory) and future Databricks-backed tables.

## Configuration Repository Design
- Defines a configuration repository abstraction for metadata sources.
- Supports Excel files in MVP and Databricks config tables in future.
- Maintains KPI configuration, ready-rule configuration, business calendar data, and source table mappings.
- Provides dynamic source selection so the active configuration source can change without application logic changes.
- Validates configuration completeness, active KPI filters, effective-dated rules, and market-specific mappings.
- Ensures business logic consumes normalized config objects rather than raw files or SQL rows.

## Provider Interface Contract
- Uses a provider contract that abstracts physical data source access.
- Core methods:
  - `get_table_data(source_table, date_from, date_to, filters)`
  - `get_config_table(config_name, filters)`
  - `get_calendar_data(market, date_from, date_to)`
- Requires providers to normalize data shapes so the engine receives consistent data regardless of Excel or Databricks backend.
- Supports provider selection via configuration and handles provider-specific errors, retries, and connection issues.
- Keeps provider implementations pluggable and independent of KPI readiness logic.

## KPI Rule Engine Scope
- Parses readiness rule expressions such as `M+3BD`, `M+5CD`, `D+1BD`, and similar variants.
- Calculates expected ready dates using business-date and calendar-date rules.
- Evaluates KPI readiness according to configurable conditions, including record existence, record count, and required KPI value presence.
- Supports KPI-specific readiness criteria sourced from metadata rather than hardcoded in logic.
- Produces structured readiness results with status (`NOT_DUE`, `READY`, `LATE`, `MISSING`) and diagnostic reasons.
- Enables future extension to more complex rule forms without changing the core engine.

## Business Calendar Model
- Represents market-specific business calendars with date-level records and business-day flags.
- Handles weekends, public holidays, and market-specific non-business days.
- Supports lookup functions for `is_business_day`, `add_business_days`, `add_calendar_days`, and next/previous business day calculations.
- Uses calendar metadata from the configuration repository so calendars can be updated without code changes.
- Provides calendar ranges to support both daily and monthly readiness calculations.

## Dashboard Layer
- Streamlit-based visualization.
- Displays overview, channel, market, KPI, and trend views.
- Consumes persisted monitoring results.

## KPI Readiness Condition Schema
The KPI rule engine shall evaluate readiness using a structured readiness condition definition attached to each KPI configuration or referenced by it.

### Purpose
- Keeps readiness logic configuration-driven.
- Prevents KPI-specific logic from being hardcoded in provider or engine code.
- Allows the same rule engine to evaluate different KPI readiness methods.

### Canonical Definition
Each readiness condition record shall define:

| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `condition_type` | string | Yes | Supported values: `record_exists`, `record_count_greater_than`, `required_column_not_null`, `all_of`, `any_of` |
| `target_column` | string | Conditional | Column to inspect for column-based conditions |
| `operator` | string | Conditional | Supported comparison operators for numeric conditions, initially `>` only |
| `expected_value` | integer or string | Conditional | Threshold or comparison value |
| `child_conditions` | list | Conditional | Nested conditions for `all_of` or `any_of` |
| `failure_reason` | string | Yes | Standard diagnostic reason when the condition fails |

### Evaluation Rules
- `record_exists` passes when at least one normalized source row is returned.
- `record_count_greater_than` passes when normalized row count satisfies the configured threshold.
- `required_column_not_null` passes when at least one row contains a non-null value for the target column.
- `all_of` passes only when all child conditions pass.
- `any_of` passes when at least one child condition passes.
- The evaluator shall return the first failed child reason for `all_of` and an aggregated reason for `any_of` when all children fail.

### Example Structure
```json
{
  "condition_type": "all_of",
  "failure_reason": "KPI readiness conditions not met",
  "child_conditions": [
    {
      "condition_type": "record_exists",
      "failure_reason": "No records found"
    },
    {
      "condition_type": "record_count_greater_than",
      "operator": ">",
      "expected_value": 0,
      "failure_reason": "Record count must be greater than zero"
    },
    {
      "condition_type": "required_column_not_null",
      "target_column": "kpi_value",
      "failure_reason": "Required KPI value is missing"
    }
  ]
}
```

## KPI Configuration Schema
The KPI configuration schema defines the canonical metadata consumed by the monitoring engine.

### Required Fields
| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `channel` | string | Yes | Business channel identifier |
| `market` | string | Yes | Market identifier |
| `kpi_name` | string | Yes | Unique KPI name within channel and market |
| `frequency` | string | Yes | Supported values: `Daily`, `Monthly` |
| `source_table` | string | Yes | Logical source identifier resolved through source mapping |
| `date_column` | string | Yes | Normalized date column used for actual ready date derivation and source filtering |
| `value_column` | string | Yes | Normalized KPI value column used by readiness conditions |
| `market_column` | string | Yes | Normalized market column used to scope source rows to the configured market |
| `readiness_condition` | object | Yes | Structured readiness condition definition |
| `active` | boolean | Yes | Whether the KPI participates in monitoring |
| `effective_from` | date | No | Optional KPI activation start date |
| `effective_to` | date | No | Optional KPI activation end date |

### Constraints
- The composite key is `channel + market + kpi_name + frequency + effective_from`.
- `source_table` is a logical identifier and shall not embed Excel filenames or Databricks physical table names.
- `date_column`, `value_column`, and `market_column` shall reference normalized output column names.
- `readiness_condition` shall be valid against the KPI Readiness Condition Schema.

### Example Structure
```json
{
  "channel": "Agency",
  "market": "CN",
  "kpi_name": "Premium",
  "frequency": "Monthly",
  "source_table": "premium_fact",
  "date_column": "data_date",
  "value_column": "premium_amount",
  "readiness_condition": {
    "condition_type": "all_of",
    "failure_reason": "Monthly Premium is not ready",
    "child_conditions": [
      {
        "condition_type": "record_exists",
        "failure_reason": "No records found"
      },
      {
        "condition_type": "required_column_not_null",
        "target_column": "premium_amount",
        "failure_reason": "Premium amount is null"
      }
    ]
  },
  "active": true,
  "effective_from": "2026-01-01",
  "effective_to": null
}
```

## Ready Rule Schema
The ready rule schema defines how expected ready dates are calculated.

### Required Fields
| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `channel` | string | Yes | Business channel identifier |
| `market` | string | Yes | Market identifier |
| `kpi_name` | string | Yes | KPI identifier |
| `frequency` | string | Yes | `Daily` or `Monthly` |
| `ready_rule` | string | Yes | Rule expression such as `M+3BD` or `D+1CD` |
| `business_calendar` | string | Yes | Calendar code used for business-day calculations |
| `effective_from` | date | Yes | Inclusive start date for rule applicability |
| `effective_to` | date | No | Inclusive end date for rule applicability |

### Rule Grammar
- Base tokens: `M` for month-end anchor, `D` for monitoring-date anchor.
- Offset token: non-negative integer.
- Unit tokens: `BD` for business days, `CD` for calendar days.
- Initial supported grammar: `^(M|D)\+(\d+)(BD|CD)$`

### Resolution Rules
- For monthly KPIs, `M` anchors to the month end of the monitoring period.
- For daily KPIs, `D` anchors to the monitoring date.
- If multiple rules match the same KPI and monitoring date, the rule with the latest `effective_from` shall be selected.
- Overlapping effective periods for the same `channel + market + kpi_name + frequency` are invalid configuration.

### Example Structure
```json
{
  "channel": "Agency",
  "market": "CN",
  "kpi_name": "Premium",
  "frequency": "Monthly",
  "ready_rule": "M+3BD",
  "business_calendar": "CN",
  "effective_from": "2026-01-01",
  "effective_to": null
}
```

## Business Calendar Schema
The business calendar schema defines the canonical market calendar used by the calendar service.

### Required Fields
| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `calendar_code` | string | Yes | Calendar identifier referenced by ready rules |
| `market` | string | Yes | Market identifier |
| `calendar_date` | date | Yes | Calendar date |
| `is_business_day` | boolean | Yes | Business-day flag |
| `holiday_name` | string | No | Human-readable holiday or closure description |
| `day_type` | string | Yes | Supported values: `business_day`, `weekend`, `public_holiday`, `market_holiday` |

### Constraints
- Each `calendar_code + calendar_date` pair shall be unique.
- Calendars shall provide complete date coverage for all supported monitoring periods.
- Missing dates are invalid because business-day calculations must be deterministic.
- `is_business_day` shall be false for weekends and holidays.

### Example Structure
```json
{
  "calendar_code": "CN",
  "market": "CN",
  "calendar_date": "2026-10-01",
  "is_business_day": false,
  "holiday_name": "National Day",
  "day_type": "public_holiday"
}
```

## Monitoring Result Schema
The monitoring result schema defines the persisted output of one KPI evaluation for one monitoring execution.

### Required Fields
| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `execution_id` | string | Yes | Unique identifier for a monitoring run |
| `result_version` | integer | Yes | Version number for reruns or corrected outputs |
| `execution_timestamp` | datetime | Yes | Timestamp when the evaluation was produced |
| `monitoring_date` | date | Yes | Logical monitoring date for the run |
| `channel` | string | Yes | Business channel identifier |
| `market` | string | Yes | Market identifier |
| `kpi_name` | string | Yes | KPI identifier |
| `frequency` | string | Yes | `Daily` or `Monthly` |
| `source_table` | string | Yes | Logical source identifier evaluated for the KPI |
| `expected_ready_date` | date | Yes | Calculated expected ready date |
| `actual_ready_date` | date | No | Derived latest available source date |
| `status` | string | Yes | Supported values: `NOT_DUE`, `READY`, `LATE`, `MISSING` |
| `missing_reason` | string | No | Required when status is `MISSING` |
| `record_count` | integer | Yes | Count of normalized rows evaluated |
| `evaluation_details` | object | Yes | Structured diagnostic metadata |

### Status Semantics
- `NOT_DUE` means the expected ready date has not been reached.
- `READY` means data satisfies readiness conditions and `actual_ready_date` is on or before `expected_ready_date`.
- `LATE` means data satisfies readiness conditions but `actual_ready_date` is after `expected_ready_date`.
- `MISSING` means the expected ready date has been reached or passed and readiness conditions are not satisfied, or required dates cannot be derived.

### Versioning Rules
- The MVP1 overwrite key is `monitoring_date + channel + market + kpi_name + frequency`.
- In MVP1, `result_version` is `1`; a rerun for the same overwrite key shall replace the previously persisted result. Full idempotency and preservation of all rerun versions are deferred to V2.
- Result retrieval APIs shall support the MVP1 latest-result behavior; all-version retrieval is a V2 concern.

### Example Structure
```json
{
  "execution_id": "20260807T090000Z-agency-cn-monthly",
  "result_version": 1,
  "execution_timestamp": "2026-08-07T09:00:00Z",
  "monitoring_date": "2026-08-07",
  "channel": "Agency",
  "market": "CN",
  "kpi_name": "Premium",
  "frequency": "Monthly",
  "source_table": "premium_fact",
  "expected_ready_date": "2026-08-05",
  "actual_ready_date": "2026-08-04",
  "status": "READY",
  "missing_reason": null,
  "record_count": 124,
  "evaluation_details": {
    "ready_rule": "M+3BD",
    "calendar_code": "CN",
    "readiness_condition_type": "all_of",
    "evaluated_columns": ["data_date", "premium_amount"]
  }
}
```

## Data Provider Interface Contract
The data provider contract abstracts physical source access while requiring normalized output semantics.

### Interface Methods
- `get_table_data(source_table, date_from, date_to, filters=None) -> DataFrame`
- `get_config_table(config_name, filters=None) -> DataFrame`
- `get_calendar_data(calendar_code, date_from, date_to) -> DataFrame`

### Method Semantics
- `source_table` is a logical source identifier resolved outside the provider into a physical source target.
- `date_from` and `date_to` are inclusive bounds.
- `filters` is an optional structured dictionary of equality predicates on normalized column names.
- Returned data shall already be normalized to the shared Normalized Data Contract.

### Provider Responsibilities
- Resolve physical data access for Excel or Databricks without leaking provider-specific details to the engine.
- Apply inclusive date filtering when date bounds are provided.
- Convert provider-native types into normalized Python and pandas types.
- Raise provider-specific exceptions that conform to the error categories below.

### Standard Error Categories
- `ProviderConnectionError`: connection or authentication failure.
- `ProviderTransientError`: retryable execution failure.
- `ProviderConfigurationError`: missing file, missing table, or invalid provider configuration.
- `ProviderSchemaError`: source data does not satisfy the expected normalized contract.

### Migration Requirement
- Excel and Databricks providers shall return identical normalized column names, data types, and null handling for the same logical source.
- Migration between providers shall require configuration changes only.

### Example Contract Shape
```python
class DataProvider(ABC):
    def get_table_data(
        self,
        source_table: str,
        date_from: date,
        date_to: date,
        filters: dict[str, object] | None = None,
    ) -> pd.DataFrame: ...

    def get_config_table(
        self,
        config_name: str,
        filters: dict[str, object] | None = None,
    ) -> pd.DataFrame: ...

    def get_calendar_data(
        self,
        calendar_code: str,
        date_from: date,
        date_to: date,
    ) -> pd.DataFrame: ...
```

## Configuration Repository Contract
The configuration repository contract defines how monitoring metadata is loaded and validated independent of the physical source.

### Responsibilities
- Load normalized configuration records.
- Resolve active KPI definitions for a monitoring slice.
- Resolve effective-dated ready rules.
- Load business calendar entries by calendar code and date range.
- Validate configuration completeness and uniqueness.

The repository is the sole owner of these responsibilities at the application boundary. The monitoring engine consumes repository results and does not read provider files, provider tables, or raw configuration rows directly.

### Required Methods
- `load_kpi_configs() -> list[KPIConfiguration]`
- `load_ready_rule_configs() -> list[ReadyRuleConfiguration]`
- `load_business_calendar(calendar_code, date_from, date_to) -> list[BusinessCalendarEntry]`
- `load_source_table_mappings() -> list[SourceTableMapping]`
- `get_active_kpis(channel, market, frequency, monitoring_date) -> list[KPIConfiguration]`
- `get_ready_rule(channel, market, kpi_name, frequency, monitoring_date) -> ReadyRuleConfiguration`
- `get_source_mapping(source_table, market) -> SourceTableMapping`
- `validate() -> list[ConfigurationValidationIssue]`

### Validation Rules
- Every active KPI shall have exactly one matching ready rule for the monitoring date.
- Every active KPI shall reference a valid source mapping.
- Every ready rule using business days shall reference a valid calendar code.
- Effective-dated ready rules shall not overlap for the same KPI and frequency.

### Example Contract Shape
```python
class ConfigurationRepository(ABC):
    def load_kpi_configs(self) -> list[KPIConfiguration]: ...

    def load_ready_rule_configs(self) -> list[ReadyRuleConfiguration]: ...

    def load_business_calendar(
        self,
        calendar_code: str,
        date_from: date,
        date_to: date,
    ) -> list[BusinessCalendarEntry]: ...

    def load_source_table_mappings(self) -> list[SourceTableMapping]: ...

    def get_active_kpis(
        self,
        channel: str,
        market: str,
        frequency: str,
        monitoring_date: date,
    ) -> list[KPIConfiguration]: ...

    def get_ready_rule(
        self,
        channel: str,
        market: str,
        kpi_name: str,
        frequency: str,
        monitoring_date: date,
    ) -> ReadyRuleConfiguration: ...

    def get_source_mapping(self, source_table: str, market: str) -> SourceTableMapping: ...

    def validate(self) -> list[ConfigurationValidationIssue]: ...
```

## Result Repository Contract
The result repository contract defines persistence and retrieval behavior for monitoring results.

### Responsibilities
- Persist monitoring results for each execution.
- Support latest-result retrieval for dashboard views.
- Support historical queries for trend analysis and auditability.
- Preserve execution metadata; MVP1 retains only the overwritten latest result set.

### Required Methods
- `save_results(results) -> None`
- `get_latest_results(channel=None, market=None, frequency=None, status=None, monitoring_date=None) -> list[MonitoringResult]`
- `get_result_history(channel, market, kpi_name, frequency, date_from=None, date_to=None) -> list[MonitoringResult]`
- `get_results_by_execution(execution_id) -> list[MonitoringResult]`

### Query Semantics
- Latest-result queries shall return the stored MVP1 result set for the requested slice.
- Full multi-version historical retrieval is deferred to V2.
- Results shall be ordered by `monitoring_date` descending, then `execution_timestamp` descending unless another order is requested.

### Example Contract Shape
```python
class ResultRepository(ABC):
    def save_results(self, results: list[MonitoringResult]) -> None: ...

    def get_latest_results(
        self,
        channel: str | None = None,
        market: str | None = None,
        frequency: str | None = None,
        status: str | None = None,
        monitoring_date: date | None = None,
    ) -> list[MonitoringResult]: ...

    def get_result_history(
        self,
        channel: str,
        market: str,
        kpi_name: str,
        frequency: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[MonitoringResult]: ...

    def get_results_by_execution(self, execution_id: str) -> list[MonitoringResult]: ...
```

## Normalized Data Contract
The normalized data contract defines the shape that the provider layer must return to the engine regardless of backend.

### Source Data Requirements
- Returned data shall use normalized column names agreed by configuration.
- The configured `date_column` shall exist in the returned DataFrame.
- Date columns shall be convertible to dates without provider-specific parsing logic in the engine.
- Required KPI value columns shall use consistent null semantics across providers.
- Additional source-specific columns may be present but shall not be required by the monitoring engine unless named in configuration.

### Configuration Data Requirements
- Configuration tables returned by providers shall already align to the architecture schemas defined above.
- Excel column names and Databricks column names shall be normalized before repository logic consumes them.

### Source Mapping Requirements
Source table mappings shall define:

| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `source_table` | string | Yes | Logical source identifier used by KPI config |
| `market` | string | Yes | Market identifier |
| `provider_type` | string | Yes | `excel` or `databricks` |
| `physical_object_name` | string | Yes | Excel workbook base name or Databricks table/view name |

KPI source configurations shall also define these normalized source fields:

| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `source_table` | string | Yes | Logical source table identifier |
| `date_column` | string | Yes | Source column used for date filtering and actual ready date derivation |
| `value_column` | string | Yes | Source column used for KPI value readiness checks |
| `market_column` | string | Yes | Source column used to filter the configured market |

### Example Structure
```json
{
  "source_table": "premium_fact",
  "market": "CN",
  "provider_type": "excel",
  "physical_object_name": "Table_A"
}
```

## Reference Execution Flow
The following flow is the canonical execution sequence for one monitoring run.

1. The monitoring engine receives `channel`, `market`, `frequency`, and `monitoring_date`.
2. The configuration repository validates required metadata or loads previously validated metadata.
3. The configuration repository resolves active KPI configurations for the requested monitoring slice.
4. For each active KPI, the repository resolves the effective-dated ready rule and the source table mapping.
5. The engine determines the calendar range required for all rule calculations in the run.
6. The configuration repository loads the required business calendar entries and constructs the business calendar service.
7. The provider retrieves normalized source data for each logical source and monitoring date range.
8. The KPI rule engine calculates the expected ready date using the ready rule and calendar service.
9. The KPI readiness evaluator applies the structured readiness condition schema against the normalized source data.
10. The engine derives `actual_ready_date`, `record_count`, `status`, and `evaluation_details`.
11. The engine assembles one monitoring result record per KPI using the Monitoring Result Schema.
12. The result repository persists the full result set with execution metadata, overwriting the prior MVP1 result set for the same monitoring slice and date.
13. The dashboard layer reads latest or historical results only through the result repository contract.

### Sequence Guarantees
- Business logic shall not read raw Excel files or Databricks tables directly.
- The rule engine shall evaluate only normalized configuration and normalized source data.
- Provider switching shall not require changes to rule evaluation, orchestration, or dashboard code.
