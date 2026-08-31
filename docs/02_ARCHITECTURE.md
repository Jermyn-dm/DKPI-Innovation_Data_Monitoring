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
- KPI Validation Rule Engine
- Monitoring Engine
- Dashboard Layer

## Data Source Layer
- Provides an abstraction over data source implementations.
- Supports MVP Excel provider and future Databricks provider.
- Ensures business logic remains unchanged when provider changes.

## Configuration Layer
- Loads KPI configurations, target-availability rules, business calendars, source table mappings, and KPI validation rules.
- Uses configuration metadata to drive monitoring logic.
- Supports Excel files in MVP and future Databricks-backed configuration tables.

The Configuration Repository owns configuration concerns. It loads and normalizes configuration data, validates it, resolves active KPI definitions, target availability, business calendars, source mappings, and validation rules, and returns typed domain objects to the monitoring engine. Providers own only physical source access and provider-level normalization; they do not resolve business configuration or apply readiness logic.

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
- Persists fields: channel, market, KPI ID, KPI name, frequency, expected ready date, actual ready date, status, missing reason, record count, evaluation details, execution timestamp.
- Supports recent result retrieval and historical trend queries.
- Enables MVP1 traceability through execution metadata; full result version history is deferred to V2.
- Allows persistence in MVP storage (file or in-memory) and future Databricks-backed tables.

## Configuration Repository Design
- Defines a configuration repository abstraction for metadata sources.
- Supports Excel files in MVP and Databricks config tables in future.
- Maintains KPI configuration, target-availability rules, business calendar data, source table mappings, and KPI validation rules.
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
- For `BD` rules, uses the configured market calendar when available and falls back to calendar-day calculation when the market has no configured calendar.
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

For a `BD` calculation, the calendar service shall first look up the requested market and required date range in the business calendar repository. If matching calendar entries exist for that market, `is_business_day` and business-day offsets shall use those entries. If the market has no configured calendar entries, the `BD` offset shall use calendar-day arithmetic as the defined fallback. `CD` calculations always use calendar-day arithmetic.

The Excel configuration boundary shall normalize calendar rows before constructing the calendar service. It shall accept `Y/N`, `YES/NO`, boolean, and `1/0` representations of `is_business_day`, parse `calendar_date` as a date, ignore incomplete rows, and retain the market key. The dashboard validation path shall load this calendar service and pass it to the KPI validation service so target availability uses the configured market calendar rather than silently defaulting to calendar days.

When normalized source data contains `BU_CODE`, the dashboard orchestration layer shall derive the uploaded market set and restrict KPI and rule selection to those markets before execution. This keeps multi-market configuration errors isolated from the selected source market.

## Dashboard Layer
- Streamlit-based visualization.
- Displays overview, channel, market, KPI, and trend views.
- Consumes persisted monitoring results.
- MVP1 dashboard accepts uploaded source and standard-value reference files, or uses default local files from `data/source/` and `data/reference/`.
- Dashboard navigation provides channel workspaces: Agency and Banca expose Monthly and Daily frequency controls; Risk exposes Monthly only.
- The selected channel and frequency are passed to configuration selection and validation execution. KPI inventory and rule bindings are filtered by the selected pair before market filtering.
- The Monthly period selector defaults to the previous month end; the Daily period selector defaults to the current date.
- A channel-frequency workspace without matching configured KPIs displays an empty state and does not fall back to another channel or frequency.
- The compact title band identifies the selected channel and frequency without displacing the operational filter and KPI metric area.
- After validation, `Market`, `Period`, `MVP1/MVP2`, and `KPI Name` filters are derived from the rule-configured Expected KPI set and apply to metrics, summary, and rule detail data. Market and MVP are single selectors with explicit `All` defaults; KPI Name is a searchable native multi-select dropdown. An empty KPI selection represents all KPIs and selected KPI names are applied as an exact multi-value filter.
- Completed validation result data and source data are held in Streamlit session state per `channel + frequency` workspace. Filter reruns reuse this data and do not invoke validation again; Reset filters clears only the current workspace's filter state.
- The metric panel uses two rows: Expected/Ready/Missing/Not Due/Delayed KPI counts, followed by content-width Validation Passed/Validation Failed counts without empty metric-card placeholders.
- Each metric count is a clickable drill-down action. Cards emphasize the numeric count and use an active state for the selected metric. The action stores selected metric state per channel-frequency workspace, filters KPI Summary using the corresponding complete KPI-key set, and navigates to the KPI Summary anchor.
- Market KPI Overview is rendered after the KPI metric rows and before KPI Summary. It groups the filtered Expected KPI set by market, applies the same metric calculation for each group, and displays Market, Channel, Frequency, Period, and all seven KPI counts. Non-zero Missing, Delayed, and Validation Failed counts use risk highlighting. The selectable overview row is handled by a callback that applies a drill-down Market filter and navigates to KPI Summary. The callback retains the prior user-selected Market value and restores it when the overview selection is cleared; a manual Market filter change exits the overview drill-down.
- Market KPI Overview is a dashboard-derived view held in session state only. It is not written to `data/results/kpi_validation_results.csv`.
- KPI summary display reads `record_type = KPI_SUMMARY`; drill-down details read matching `record_type = RULE` rows.
- KPI Summary is a single-row selectable dataframe. Its selection filters Validation Rule Details by `channel + market + kpi_id + frequency + period + execution_timestamp` and navigates to the rule-details anchor. Clearing the selection clears the details view and renders a selection prompt. Validation Rule Details is read-only.
- The dashboard subtitle is `Distribution KPI Validation Dashboard`.
- KPI Summary hides internal identifiers and execution metadata: `kpi_id`, `aggregation_level`, `aggregation_detail`, `execution_date`, and `execution_timestamp`. Validation Rule Details orders `market` first and hides `kpi_id` and `rule_id` at the display layer only; both fields remain part of persisted result records and execution-key joins.
- Dashboard display formats `data_ready_time` as `YYYY-MM-DD`. For percentage-based comparison rules, the detail-table `actual_value` is formatted to one decimal place with a `%` suffix.
- KPI Summary and Validation Rule Details apply the same `status` styling: `PASSED` is light green with bold dark-green text; `FAILED` is light yellow with bold dark text. Status text is always retained for accessibility.
- The dashboard does not render a separate selected-KPI status panel because the selected summary row and matching rule-detail table provide the same information.
- Sub-channel fields such as `DISTRIBUTION_CHANNEL` and `CHANNEL_CODE` remain source-level diagnostic information but are not rendered in the MVP dashboard. They do not change the KPI summary grain.
- Visual presentation uses a Manulife-inspired enterprise style with green accents, white grouped panels, concise KPI metric cards, and status-specific color treatment for operational readability.
- The dashboard provides a configuration maintenance action that generates baseline validation-rule bindings from `kpi_config.xlsx` for KPI rows where `kpi_id` is populated, `monthly = Y`, and `derivation logic = EDL`.

## KPI Data Validation Rule Schema
The KPI validation rule engine shall evaluate source data using structured rules stored in `kpi_validation_rule_config.xlsx`. Expected ready dates are defined by `target_availability` in `kpi_config.xlsx` and are not data validation rules.

The dashboard orchestration layer builds the execution set by joining KPI inventory and validation-rule configuration on the exact composite key `channel + market + kpi_id + frequency`. It must not join by `kpi_id` alone. An inventory KPI without a matching validation-rule binding is excluded from execution, and a same-ID KPI in another market or channel remains isolated.

The dashboard constructs its Expected KPI set from this execution set by retaining only active KPI configuration with populated `kpi_id` and `derivation_logic = EDL`. Dashboard filters operate on this set. The metric calculation joins Expected KPIs to the latest `KPI_SUMMARY` and `RULE_RECORD_EXISTS` records using `channel + market + kpi_id + frequency`: Ready uses a passed record-exists rule, Missing uses `ready_status = DELAYED` and a non-passed record-exists rule, Not Due uses `ready_status = NOT_DUE`, and Delayed uses `ready_status = READY_DELAYED` plus a passed record-exists rule. Validation Passed uses summary status `PASSED`; Validation Failed includes executed summary statuses other than `PASSED` and `NOT_DUE`.

### Purpose
- Keeps KPI data validation configuration-driven.
- Prevents KPI-specific logic from being hardcoded in provider or engine code.
- Allows the same rule engine to evaluate different KPI readiness methods.

### Canonical Definition
Each validation rule record shall define:

| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `rule_type` | string | Yes | `RECORD_EXISTS`, `VALUE_NOT_NULL`, `VALUE_GREATER_THAN_ZERO`, `CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT`, or `DEVIATION_FROM_STANDARD_WITHIN_PERCENT` |
| `kpi_id` | string | Yes | Stable KPI identifier |
| `kpi_name` | string | Yes | Human-readable KPI name |
| `rule_id` | string | Yes | Reusable generic rule identifier; must not contain `kpi_id` |
| `rule_order` | integer | Yes | Evaluation order within the KPI rule set |
| `value_column` | string | Conditional | KPI value column for value-based checks |
| `threshold_percent` | number | Conditional | Maximum allowed percentage change or deviation |
| `standard_value` | number | No | Not stored in the rule binding; loaded from the standard-value reference file |
| `enabled` | boolean | Yes | Whether the rule is active |
| `failure_reason` | string | No | Diagnostic reason when the rule fails |

### Evaluation Rules
- `RECORD_EXISTS` passes when at least one normalized source row is returned.
- `VALUE_NOT_NULL` passes when the configured value is not null. Omitting this rule explicitly allows null for that KPI.
- `VALUE_GREATER_THAN_ZERO` passes when the configured value is greater than zero.
- `CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT` passes when the absolute percentage change from the immediately preceding period does not exceed `threshold_percent`.
- `DEVIATION_FROM_STANDARD_WITHIN_PERCENT` passes when the absolute percentage deviation from `standard_value` does not exceed `threshold_percent`.
- Enabled rules for a KPI are evaluated in ascending `rule_order`; all enabled rules must pass.

### Example Structure
```json
{
  "rule_id": "premium-exists",
  "rule_type": "RECORD_EXISTS",
  "rule_order": 1,
  "enabled": true
}
```

The `kpi_validation_rule_config.xlsx` file uses one row per rule binding with these fields: `channel`, `market`, `kpi_id`, `kpi_name`, `frequency`, `source_table`, `rule_id`, `rule_type`, `rule_order`, `value_column`, `threshold_percent`, `enabled`, `effective_from`, `effective_to`, and `remark`. Generic `rule_id` values may be reused across KPIs and markets. Rules are selected by KPI and effective period, then evaluated by ascending `rule_order`. An enabled KPI validation rule set passes only when all configured rules pass. Missing optional parameters are invalid when required by the selected `rule_type`.

The validation binding key is `market + kpi_id + frequency + rule_id + rule_order + effective_from`. `threshold_percent` belongs to the binding, allowing comparison thresholds to vary by market and KPI. Standard values are maintained separately in `data/reference/kpi_standard_values.xlsx`.

The baseline generation action upserts three reusable rule bindings for each eligible KPI: `RULE_RECORD_EXISTS`, `RULE_VALUE_NOT_NULL`, and `RULE_VALUE_GREATER_THAN_ZERO`. It also ensures `source_table_mapping.xlsx` contains one mapping row for each required `source_table + market`. The action shall not remove or overwrite manually configured comparison rules.

For `CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT`, the previous-period value is obtained from the same KPI and source configuration for the immediately preceding monitoring period. For `DEVIATION_FROM_STANDARD_WITHIN_PERCENT`, `standard_value` is the configured reference value. Division-by-zero and unavailable comparison values shall produce a validation failure with a diagnostic reason rather than an unhandled calculation error.

## KPI Configuration Schema
The KPI configuration schema defines the canonical metadata consumed by the monitoring engine.

### Required Fields
| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `country_cd` | string | Yes | Market/country identifier from the KPI inventory |
| `channel` | string | Yes | Business channel identifier |
| `kpi_id` | string | Yes | Stable KPI identifier |
| `kpi_name` | string | Yes | KPI name |
| `monthly` | boolean | Yes | Whether the KPI is monitored monthly |
| `daily` | boolean | Yes | Whether the KPI is monitored daily |
| `run_batch` | string or integer | No | Configured processing batch |
| `mvp1/mvp2` | string | No | Delivery phase classification |
| `derivation logic` | string | No | KPI derivation metadata |
| `integration` | boolean | Yes | Whether the KPI is integrated |
| `target_availability` | string | Yes | Target availability rule or date |
| `remark` | string | No | KPI metadata remark |
| `source_table` | string | Yes | Logical source identifier resolved through source mapping |
| `active` | boolean | Yes | Whether the KPI participates in monitoring |
| `effective_from` | date | No | Optional KPI activation start date |
| `effective_to` | date | No | Optional KPI activation end date |

### Constraints
- The composite key is `channel + country_cd + kpi_id + effective_from`.
- `source_table` is a logical identifier and shall not embed Excel filenames or Databricks physical table names.
- Validation rules for the KPI shall be maintained in `kpi_validation_rule_config.xlsx`.

### Example Structure
```json
{
  "country_cd": "CN",
  "channel": "Agency",
  "kpi_id": "AG0001",
  "kpi_name": "Premium",
  "monthly": true,
  "daily": false,
  "source_table": "premium_fact",
  "active": true,
  "effective_from": "2026-01-01",
  "effective_to": null
}
```

The KPI validation rule set is referenced by `channel + market + kpi_id + frequency` and effective dates; it is not embedded in the KPI inventory row. Every KPI configuration, ready-date rule, validation rule, and monitoring result must contain both `kpi_id` and `kpi_name`.

## Target Availability Rule
The `target_availability` field in the KPI configuration defines how expected ready dates are calculated. It is the single source of truth; no separate ready-rule configuration is required.

### Required Fields
| Field | Type | Required | Description |
|----------|----------|----------|----------|
| `channel` | string | Yes | Business channel identifier |
| `country_cd` | string | Yes | Market identifier from KPI configuration |
| `kpi_id` | string | Yes | Stable KPI identifier |
| `kpi_name` | string | Yes | Human-readable KPI name |
| `target_availability` | string | Yes | Rule expression such as `M+3BD`, `M+5CD`, or `T+CD2` |

### Rule Grammar
- Supported anchors include month-end, monitoring date, and data-period end.
- `BD` uses the configured market calendar when available; otherwise it falls back to calendar days.
- `CD` always uses calendar days.
- `T` means the data period end date; `T+CD2` means two calendar days after that date. The equivalent normalized form `T+2CD` is also accepted.

### Resolution Rules
- For monthly KPIs, `M` anchors to the month end of the monitoring period.
- For daily KPIs, `D` anchors to the monitoring date.
- The target availability value is read directly from the active KPI configuration.

The dashboard validation path requires a non-empty target availability for every KPI in the execution set. Missing values fail fast with an actionable `market/kpi/channel` configuration error rather than producing an ambiguous readiness result.

### Example Structure
```json
{
  "channel": "Agency",
  "country_cd": "CN",
  "kpi_id": "AG0001",
  "kpi_name": "Premium",
  "target_availability": "M+3BD"
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

Calendar coverage is required only for markets that are configured for business-day calculation. A market with no calendar records is treated as not configured, and its `BD` rules use the calendar-day fallback rather than failing calendar lookup.

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
| `kpi_id` | string | Yes | Stable KPI identifier |
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
- The MVP1 overwrite key is `monitoring_date + channel + market + kpi_id + frequency`.
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
  "kpi_id": "AG0001",
  "kpi_name": "Premium",
  "frequency": "Monthly",
  "source_table": "premium_fact",
  "expected_ready_date": "2026-08-05",
  "actual_ready_date": "2026-08-04",
  "status": "READY",
  "missing_reason": null,
  "record_count": 124,
  "evaluation_details": {
    "target_availability": "M+3BD",
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
- Resolve target availability from active KPI configurations.
- Load business calendar entries by calendar code and date range.
- Validate configuration completeness and uniqueness.

The repository is the sole owner of these responsibilities at the application boundary. The monitoring engine consumes repository results and does not read provider files, provider tables, or raw configuration rows directly.

### Required Methods
- `load_kpi_configs() -> list[KPIConfiguration]`
- `load_validation_rules() -> list[KPIValidationRule]`
- `load_business_calendar(calendar_code, date_from, date_to) -> list[BusinessCalendarEntry]`
- `load_source_table_mappings() -> list[SourceTableMapping]`
- `get_active_kpis(channel, market, frequency, monitoring_date) -> list[KPIConfiguration]`
- `get_target_availability(channel, market, kpi_id, frequency, monitoring_date) -> str`
- `get_source_mapping(source_table, market) -> SourceTableMapping`
- `validate() -> list[ConfigurationValidationIssue]`

### Validation Rules
- Every active KPI shall have a valid target availability value.
- Every active KPI shall reference a valid source mapping.
- Target availability rules using business days shall use the configured market calendar when available.

### Example Contract Shape
```python
class ConfigurationRepository(ABC):
    def load_kpi_configs(self) -> list[KPIConfiguration]: ...

    def load_validation_rules(self) -> list[KPIValidationRule]: ...

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

    def get_target_availability(
        self,
        channel: str,
        market: str,
        kpi_id: str,
        frequency: str,
        monitoring_date: date,
    ) -> str: ...

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
- `get_result_history(channel, market, kpi_id, frequency, date_from=None, date_to=None) -> list[MonitoringResult]`
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
        kpi_id: str,
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
| `physical_object_name` | string | Yes | Excel workbook name under `data/source/`, or Databricks table/view name |

The `source_table` value in KPI configuration is a logical source identifier. The Configuration Repository shall resolve each active KPI's `source_table` and `market` as a composite lookup key in the source mapping configuration. The matching mapping provides `provider_type` and `physical_object_name`, which identify the provider and physical Excel file or Databricks table/view to read. An active KPI without exactly one matching mapping is invalid configuration.

For MVP1 Excel execution, physical KPI source files shall be located under `data/source/`. The `physical_object_name` is resolved relative to that directory; configuration files remain under `configs/`.

Validation reference data shall be stored under `data/reference/`. The standard-value file is `data/reference/kpi_standard_values.xlsx`; it is not a KPI source file or rule configuration file. The `DEVIATION_FROM_STANDARD_WITHIN_PERCENT` rule resolves a standard value using `market + kpi_id + frequency + period`, with effective-date filtering when applicable.

For the supplied Agency source data, providers shall normalize `ACCOUNT_ID` to `kpi_id`, `ACCOUNT` to `kpi_name`, `PERIOD` to the monitoring period, and `VALUE` to the KPI value. The validation engine shall select AG0016 monthly rows by `ACCOUNT_ID = AG0016` and the requested `PERIOD`.

For market files with sub-channel rows, providers shall retain `BU_CODE`, `DISTRIBUTION_CHANNEL`, `CHANNEL_CODE`, and `MODE` when available. The validation engine filters by configured market, KPI, selected period, and monthly mode, then sums `VALUE` across all matching sub-channel rows. This supports Singapore and Indonesia source files where standards and validation rules are maintained at total market level while sub-channel rows are used for issue analysis.

The validation result is a rule-level record containing the KPI identifiers, rule ID/type/order, period, pass/fail value, actual value, comparison value where applicable, configured threshold, and diagnostic reason. For previous-period comparison, the percentage is calculated as `(current_value - previous_value) / abs(previous_value) * 100`; the rule passes when its absolute value is within `threshold_percent`.

Only the configured market/KPI/frequency rule set is evaluated. For source data with `BU_CODE`, the dashboard first restricts the execution set to markets present in the source, then applies the exact rule-binding key. This prevents unrelated incomplete market configuration from affecting a run.

Validation output is written to the fixed file `data/results/kpi_validation_results.csv`. Each rule-level record has `record_type = RULE` and includes `execution_date`, `execution_timestamp`, and `status`. Each KPI has one separate `record_type = KPI_SUMMARY` row with `rule_id = KPI_RESULT`; its `status` is the final result for that KPI and period. `status` supports `PASSED`, `FAILED`, `PREVIOUS_PERIOD_MISSING`, and `STANDARD_VALUE_MISSING`. The `record_type` determines whether `status` represents an individual rule result or the KPI-level summary result. The persistence layer retains execution history across dates. On each write, it removes only the earlier complete batch matching `execution_date + channel + market + kpi_id + frequency + period`, then appends the new rule and summary batch.

Validation output includes `aggregation_level` and `aggregation_detail`. MVP1 distribution validation persists `aggregation_level = Agency` and `aggregation_detail = ALL`. `Agency` is the canonical output value; during every result write, legacy persisted `aggregation_level` values matching `MARKET`, case-insensitively and with surrounding whitespace ignored, are normalized to `Agency` before the file is saved. Sub-channel fields contribute to source aggregation but are not rendered in the dashboard or persisted as separate KPI validation results.

Validation output shall also include `expected_ready_date`, `data_ready_time`, `ready_status`, and `ready_delay_days`. The data ready time is derived from source `CREATE_DATE` and `UPDATE_DATE`: use `CREATE_DATE` when only it is populated, use `UPDATE_DATE` when both are populated and `UPDATE_DATE > CREATE_DATE`, and use the validation execution timestamp when both are empty. If the execution date is before expected ready date, the service writes only a `KPI_SUMMARY` row with `ready_status = NOT_DUE` and skips validation rules.

Ready timing statuses are `READY_ON_TIME`, `READY_DELAYED`, `DELAYED`, and `NOT_DUE`. `READY_DELAYED` is used when source data arrives after expected ready date. `DELAYED` is used when expected ready date has passed but no source record is available. Delay days use the same unit as the target availability rule: business-day delay for `BD` and calendar-day delay for `CD`.

The KPI summary status is `PASSED` only when every enabled rule passes. A failed rule produces `FAILED`; an unavailable previous-period input produces `PREVIOUS_PERIOD_MISSING`; an unavailable standard value produces `STANDARD_VALUE_MISSING`; other unresolved prerequisites produce `VALIDATION_INCOMPLETE`. The summary row is the only row used as the KPI-level final result.

Before rendering, the dashboard applies latest-execution selection to the result set. It groups by `channel + market + kpi_id + frequency + period`, retains records with the maximum `execution_timestamp` for display, and filters rule details to the selected summary's exact business key and execution timestamp. This display selection does not delete results from prior execution dates. The selector label includes channel and market so KPIs with the same ID remain distinguishable.

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
4. For each active KPI, the repository reads `target_availability` and resolves `source_table + market` to one physical source mapping.
5. The engine determines the calendar range required for all rule calculations in the run.
6. The configuration repository loads the required business calendar entries and constructs the business calendar service.
7. The selected provider retrieves normalized source data from the physical object resolved by the source mapping for each logical source and monitoring date range.
8. The KPI rule engine calculates the expected ready date using `target_availability` and the calendar service; the calendar service uses the market calendar when configured and calendar-day fallback otherwise.
9. The KPI readiness evaluator applies the structured readiness condition schema against the normalized source data.
10. The KPI validation rule engine applies the effective validation rules for the KPI in rule order.
11. The engine derives `actual_ready_date`, `record_count`, `status`, and `evaluation_details`.
12. The engine assembles one monitoring result record per KPI using the Monitoring Result Schema.
13. The result repository persists the full result set with execution metadata, overwriting the prior MVP1 result set for the same monitoring slice and date.
14. The dashboard layer displays KPI summary results and rule-level drill-down details from `data/results/kpi_validation_results.csv` for MVP1 local execution.

### Sequence Guarantees
- Business logic shall not read raw Excel files or Databricks tables directly.
- The rule engine shall evaluate only normalized configuration and normalized source data.
- Provider switching shall not require changes to rule evaluation, orchestration, or dashboard code.
