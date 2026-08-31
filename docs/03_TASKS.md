# DKPI Data Readiness Monitoring - Implementation Task Plan

## 1. Scope and Planning Rules

- Source documents: `docs/01_PRD.md`, `docs/02_ARCHITECTURE.md`
- Task granularity: each task is designed to be completed in less than 1 working day.
- Dependency notation:
	- `FS` = Finish-to-Start dependency (default)
	- `SS` = Start-to-Start dependency (can run in parallel once predecessor starts)
- Priority scale:
	- `P0` = critical for MVP1 path
	- `P1` = important for MVP1 quality and completeness
	- `P2` = post-MVP1 extension preparation
- MVP1 scope baseline:
	- Channel: Agency
	- Market: CN
	- Frequency: Monthly
	- KPI: selected representative KPIs
	- Source: Excel

## 2. Task Backlog

| Task ID | Task Name | Est. Effort | Priority | MVP1 | Dependencies | Acceptance Criteria |
|----------|----------|----------|----------|----------|----------|----------|
| T001 | Define Python environment and dependencies | 0.25 day | P0 | Yes | None | Virtual environment setup documented; required packages for pandas, streamlit, pydantic, openpyxl installed; project runs without missing import errors. |
| T002 | Finalize domain model classes | 0.5 day | P0 | Yes | T001 (FS) | Domain models require both `kpi_id` and `kpi_name` for KPI, validation-rule, and monitoring-result records; KPI models include target availability; model validation works for sample payloads. |
| T003 | Implement configuration loader entrypoint | 0.5 day | P0 | Yes | T002 (FS) | Config loader resolves configured source type and returns typed config entities; loader handles invalid source selection with clear error. |
| T004 | Build Excel configuration reader | 0.5 day | P0 | Yes | T003 (FS) | `kpi_config.xlsx`, `kpi_validation_rule_config.xlsx`, `calendar_config.xlsx`, and `source_table_mapping.xlsx` can be read into normalized dataframes; malformed sheet structure returns validation error. `data/reference/kpi_standard_values.xlsx` is available as the standard-value reference template. |
| T005 | Implement source table mapping resolution | 0.5 day | P0 | Yes | T004 (FS) | KPI `source_table + market` resolves to exactly one mapping row; the row supplies `provider_type` and physical Excel object name; missing or duplicate mappings are detected and reported. |
| T006 | Implement configuration validation rules | 0.75 day | P0 | Yes | T004 (FS), T005 (FS), T012A (FS) | Validation catches missing target availability, missing KPI IDs/names, mismatched KPI IDs/names, invalid calendar code references, duplicate active KPI keys, invalid validation-rule parameters, and malformed validation rule types; validation report is machine-readable. |
| T007 | Implement business calendar data loading | 0.5 day | P0 | Yes | T004 (FS) | Configured CN calendar entries load with complete date coverage for the test period; duplicates and missing dates are detected, while absent market calendars are represented as unconfigured. |
| T008 | Implement business calendar service core functions | 0.75 day | P0 | Yes | T007 (FS) | Configured markets use `is_business_day`, `add_business_days`, and holiday/weekend rules; markets without calendar entries use calendar-day fallback for `BD`; `add_calendar_days` is verified. |
| T009 | Implement target-availability parser | 0.5 day | P0 | Yes | T002 (FS), T008 (FS) | Parser supports configured target-availability forms including `M+nBD`, `M+nCD`, `D+nBD`, `D+nCD`, `T+CDn`, and normalized `T+nCD`; invalid formats are rejected with explicit error. |
| T010 | Implement expected ready date calculator | 0.5 day | P0 | Yes | T009 (FS), T008 (FS) | Expected ready date computation uses KPI `target_availability`; configured-market `BD`, unconfigured-market `BD` fallback, `CD`, and `T` data-period-end anchors pass tests. |
| T010B | Connect configured calendars to validation execution | 0.5 day | P0 | Yes | T010 (FS), T013 (FS) | Excel calendar rows normalize `Y/N` and boolean flags, SG `M+NBD` skips weekends/holidays during dashboard validation, and markets without usable calendar rows use documented calendar-day fallback. |
| T010C | Scope validation to uploaded markets | 0.25 day | P0 | Yes | T010B (FS), T013 (FS) | When source data contains `BU_CODE`, dashboard execution selects only matching KPI and validation-rule markets, preventing unrelated incomplete market configuration from changing the selected market result. |
| T010D | Enforce configured KPI validation scope | 0.25 day | P0 | Yes | T012A (FS), T012B (FS) | Dashboard execution joins KPI inventory to validation rules by exact `channel + market + kpi_id + frequency`; KPIs without a matching validation-rule binding are skipped, and same-ID KPIs from another market or channel are not selected. Missing target availability fails with the specific market/KPI/channel. |
| T010A | Implement data ready time derivation | 0.5 day | P0 | Yes | T010 (FS) | Data ready time is derived from `CREATE_DATE` and `UPDATE_DATE`; when both are empty, validation execution timestamp is used. |
| T011 | Define readiness condition evaluator primitives | 0.5 day | P0 | Yes | T002 (FS) | Evaluator supports configured record/value readiness conditions; each condition returns pass/fail plus reason. |
| T012 | Implement composite readiness evaluator (`all_of`, `any_of`) | 0.5 day | P0 | Yes | T011 (FS) | Nested condition evaluation works; `all_of` returns first failed reason; `any_of` returns aggregated failure when all fail. |
| T012A | Define KPI validation rule model and repository | 0.5 day | P0 | Yes | T002 (FS), T004 (FS) | `kpi_validation_rule_config.xlsx` loads typed rule bindings for all five initial rule types; generic `rule_id` values are reusable across KPIs and markets, every binding carries both `kpi_id` and `kpi_name`, and thresholds may vary by binding. |
| T012B | Validate KPI validation rule configuration | 0.5 day | P0 | Yes | T012A (FS), T005 (FS) | Validation rejects missing required parameters, unsupported rule types, duplicate rule bindings, invalid thresholds, invalid KPI/source references, and missing standard-value references; generic rule IDs may repeat across KPI/market bindings, and KPIs without `VALUE_NOT_NULL` remain valid. Standard values are resolved from `data/reference/kpi_standard_values.xlsx` by market, KPI, frequency, and period. |
| T012C | Generate baseline validation rules from KPI inventory | 0.5 day | P0 | Yes | T004 (FS), T005 (FS), T012A (FS) | Dashboard action generates `RULE_RECORD_EXISTS`, `RULE_VALUE_NOT_NULL`, and `RULE_VALUE_GREATER_THAN_ZERO` for all rows with `kpi_id` populated, `monthly = Y`, and `derivation logic = EDL`; generation is idempotent and preserves manually configured comparison rules. |
| T012D | Implement market-level KPI aggregation | 0.5 day | P0 | Yes | T012A (FS), T013 (FS) | Validation filters by market, KPI, period, and monthly mode, then sums `VALUE` across sub-channels; generated output records persist `aggregation_level = Agency` and `aggregation_detail = ALL`; result writes normalize all legacy `MARKET` case/whitespace variants to `Agency`. |
| T013 | Implement Excel data provider table read | 0.5 day | P0 | Yes | T001 (FS), T005 (FS) | Provider reads the physical Excel object under `data/source/` resolved from KPI `source_table + market` mapping and date range; returns normalized dataframe with expected columns and dtypes. |
| T014 | Implement provider error mapping and retry handling | 0.5 day | P1 | Yes | T013 (FS) | Provider raises standardized error categories for config, schema, and transient failures; retry behavior defined for transient errors. |
| T015 | Implement provider factory selection | 0.25 day | P0 | Yes | T013 (FS) | Factory creates provider from configuration; unsupported provider type fails fast with clear message. |
| T016 | Implement result repository write path (MVP memory/file) | 0.5 day | P0 | Yes | T002 (FS) | Monitoring results persist with execution metadata; an MVP1 rerun overwrites the prior result set for the same monitoring slice and date. |
| T017 | Implement latest result retrieval query | 0.5 day | P1 | Yes | T016 (FS) | Latest query returns the stored MVP1 result per KPI slice and monitoring date; filters (channel, market, frequency, status) function correctly. |
| T018 | Implement result history retrieval query | 0.5 day | P1 | Yes | T016 (FS) | History query returns ordered MVP1 results across a date range; rerun versions are not retained in MVP1. |
| T019 | Build monitoring orchestration skeleton | 0.5 day | P0 | Yes | T006 (FS), T015 (FS), T016 (FS) | Orchestrator accepts run parameters (`channel`, `market`, `frequency`, `monitoring_date`) and executes configuration-to-result pipeline steps without KPI-specific branching. |
| T020 | Implement per-KPI execution loop | 0.75 day | P0 | Yes | T019 (FS), T010 (FS), T012 (FS), T013 (FS), T022 (FS) | For each active KPI, system computes expected date, evaluates readiness, derives actual date and status, and creates output record matching monitoring result schema. |
| T021 | Add execution metadata and versioning strategy | 0.5 day | P1 | Yes | T020 (FS), T016 (FS) | Execution ID and execution timestamp are generated and documented; MVP1 reruns overwrite the prior result set for the same monitoring slice and date. |
| T022 | Implement monitoring status derivation rules | 0.5 day | P0 | Yes | T010 (FS), T012 (FS) | `NOT_DUE`, `READY`, `LATE`, and `MISSING` semantics are implemented exactly as architecture definitions and verified via unit tests. |
| T023 | Seed MVP1 sample configuration data | 0.5 day | P0 | Yes | T006 (FS), T007 (FS) | Agency-CN-Monthly KPI inventory with target availability, configured CN calendar, validation rules, `data/reference/kpi_standard_values.xlsx`, and `source_table_mapping.xlsx` rows resolving each active KPI to its physical Excel file are available and pass validation. |
| T024 | Prepare MVP1 sample Excel source data | 0.5 day | P0 | Yes | T013 (SS), T023 (SS) | Sample source files are stored under `data/source/`, include ready, late, and missing cases, and conform to normalized contract expectations. |
| T025 | Build Streamlit dashboard skeleton and navigation | 0.5 day | P1 | Yes | T030B (FS), T012C (FS) | Dashboard loads successfully by local URL and provides Agency and Banca Monthly/Daily workspaces plus a Risk Monthly workspace. Each workspace provides upload controls, frequency-appropriate period selection, KPI summary, rule-detail sections, and baseline-rule generation with Manulife-inspired green enterprise styling. |
| T025A | Scope dashboard execution by channel and frequency | 0.5 day | P1 | Yes | T025 (FS), T012A (FS) | Selected Channel/Frequency filters KPI inventory and validation rules before market filtering. Monthly defaults to the prior month-end, Daily defaults to the current date, and an unconfigured workspace shows an empty state without executing another channel's rules. |
| T026 | Implement dashboard KPI status summary view | 0.5 day | P1 | Yes | T025 (FS), T022 (FS), T030B (FS) | Summary table displays only the latest `KPI_SUMMARY` result per `channel + market + kpi_id + frequency + period`, including ready status, delay days, validation status, and reason; it hides `kpi_id`, aggregation fields, and execution metadata, and displays `data_ready_time` as `YYYY-MM-DD`. A compact title band and user-friendly Market/Period/MVP1-MVP2/KPI Name filters apply to the metric cards and summary data. |
| T026A | Implement expected KPI readiness metrics | 0.5 day | P1 | Yes | T010D (FS), T026 (FS), T030B (FS) | Two metric rows show Expected, Ready, Missing, Not Due, Delayed, Validation Passed, and Validation Failed. Cards emphasize numeric values and show an active selection state. Expected KPI count is limited to active, EDL, non-null KPI IDs with an exact rule binding; all metric categories use the documented summary and `RULE_RECORD_EXISTS` status definitions. The validation row uses content width only. Clicking a metric filters KPI Summary to that metric's KPI set and navigates to the summary section. |
| T026B | Improve dashboard filter ergonomics | 0.25 day | P1 | Yes | T026 (FS), T026A (FS) | Market and MVP use `All` single selectors, KPI Name provides a searchable multi-select dropdown with empty selection meaning all KPIs, Reset filters restores defaults, and Streamlit session state retains completed channel-frequency results while users refine filters. |
| T026C | Add Market KPI Overview | 0.5 day | P1 | Yes | T026A (FS), T026B (FS) | A dashboard-only table between metric cards and KPI Summary groups the filtered Expected KPI set by Market and displays Channel, Frequency, Period, and the seven KPI counts. Non-zero Missing, Delayed, and Validation Failed counts are highlighted. Selecting one market row applies a temporary Market drill-down and navigates to KPI Summary; clearing it restores the user's prior Market filter, and manual Market selection exits the drill-down. No overview records are persisted. |
| T027 | Implement dashboard rule detail view | 0.5 day | P1 | Yes | T025 (FS), T030B (FS) | Selecting one KPI Summary dataframe row displays only matching `RULE` rows from the same `channel + market + kpi_id + frequency + period + execution_timestamp` and navigates to the detail section. Clearing the Summary selection clears details and shows a selection prompt. Details are read-only, lead with market, and include rule type, status, actual value, previous value, standard value, threshold, and reason. `kpi_id` and `rule_id` are hidden only in the UI and remain persisted. Sub-channel contribution is not rendered in the MVP dashboard. `PASSED` and `FAILED` status cells use accessible green/yellow highlighting consistent with KPI Summary. Percentage-based `actual_value` values display one decimal place with a `%` suffix. The redundant selected-KPI status panel is not rendered. |
| T028 | Add unit tests for calendar and rule engine | 0.75 day | P0 | Yes | T010 (FS), T012 (FS) | Test suite covers configured-market business-day calculations, unconfigured-market calendar-day fallback, rule parsing, expected dates, and readiness condition pass/fail variants. |
| T028A | Add unit tests for KPI validation rules | 0.75 day | P0 | Yes | T012B (FS) | Tests cover record existence, nullable KPI exceptions, non-null values, values greater than zero, previous-period percentage thresholds, standard-value percentage thresholds, diagnostic failures, missing comparison inputs, AG0016 monthly row selection by `ACCOUNT_ID` and `PERIOD`, and SG business-day target availability across weekends. |
| T029 | Add unit tests for provider normalization | 0.5 day | P1 | Yes | T013 (FS), T014 (FS) | Tests verify normalized columns, data types, null handling, and error mapping behavior for Excel provider. |
| T030 | Add integration test for end-to-end monthly run | 0.75 day | P0 | Yes | T020 (FS), T023 (FS), T024 (FS), T016 (FS), T028 (FS), T037 (FS) | One run from config load to result persistence succeeds and produces expected statuses for not-due, ready, late, and missing sample KPIs. AG0016 `PERIOD=2026-07-31` validation uses the reference standard value and generates output under `data/results/`. |
| T030A | Implement fixed validation result output | 0.5 day | P0 | Yes | T028A (FS), T010A (FS), T010D (FS) | Results are written to fixed file `data/results/kpi_validation_results.csv`; only rule-configured KPIs are persisted; rule rows include execution date, timestamp, expected ready date, data ready time, ready status, delay days, `aggregation_level`, and `aggregation_detail`; all stored `aggregation_level` values use `Agency`, with legacy `MARKET` values migrated during writes; different execution dates are appended as history. |
| T030B | Implement KPI validation summary result | 0.5 day | P0 | Yes | T030A (FS) | Each execution batch has one `KPI_SUMMARY` row per KPI; `status` represents rule result on `RULE` rows and KPI final result on `KPI_SUMMARY` rows; rule rows do not repeat the final result. Dashboard display selects the latest summary batch. |
| T031 | Add regression test for rerun overwrite behavior | 0.5 day | P1 | Yes | T021 (FS), T030B (FS) | Re-execution overwrites the earlier complete rule and summary batch only when `execution_date + channel + market + kpi_id + frequency + period` matches. Results from different execution dates remain persisted as history, while the dashboard displays the latest execution timestamp. |
| T032 | Add architecture conformance checklist | 0.25 day | P1 | Yes | T030 (FS) | Checklist verifies contracts from architecture doc are represented in code interfaces and model schemas; no unresolved ambiguity items remain. |
| T033 | Add operational logging for orchestration steps | 0.5 day | P1 | Yes | T020 (FS) | Logs include execution ID, KPI key, provider operation, rule evaluation outcome, and persistence status. |
| T034 | Create Databricks provider interface stub | 0.5 day | P2 | No | T015 (FS) | Databricks provider class compiles against provider contract with method stubs and TODO markers; no business logic changes needed. |
| T035 | Create config switch playbook (Excel to Databricks) | 0.25 day | P2 | No | T034 (FS), T032 (FS) | Documentation defines only configuration changes required for provider migration and validates unchanged engine/rule code path. |
| T036 | Confirm MVP scope (MVP1) sign-off | 0.25 day | P0 | Yes | None | Written sign-off confirms MVP1 delivery scope is Agency-CN-Monthly only and daily monitoring is deferred beyond MVP1. |
| T037 | Implement schema drift validation (pre-run) | 0.5 day | P0 | Yes | T006 (FS), T013 (FS) | Before each monitoring run, schema drift checks validate config and source columns/types; violations fail fast with actionable error messages. |
| T038 | Execute business UAT and sign-off | 0.5 day | P0 | Yes | T026 (FS), T027 (FS), T030 (FS) | UAT checklist is executed with business users, defects triaged, and formal MVP1 acceptance decision documented. |
| T039 | Create operational runbook (MVP1) | 0.5 day | P1 | Yes | T033 (FS), T038 (FS) | Runbook documents setup, execution command, monitoring flow, common failures, and recovery actions; walkthrough completed with handover audience. |

## 3. MVP1 Critical Path

The minimum sequence to deliver MVP1 usable functionality is:

T036 -> T001 -> T002 -> T003 -> T004 -> T005 -> T012A -> T012B -> T012C -> T012D -> T006 -> T007 -> T008 -> T009 -> T010 -> T010A -> T010B -> T010C -> T010D -> T011 -> T012 -> T013 -> T014 -> T015 -> T016 -> T019 -> T022 -> T020 -> T023 -> T024 -> T028 -> T028A -> T037 -> T030 -> T030A -> T030B -> T017 -> T018 -> T025 -> T025A -> T026 -> T026A -> T026B -> T026C -> T027 -> T033 -> T038 -> T039

Notes:
- Daily monitoring support remains outside MVP1; MVP1 implements only the Agency-CN-Monthly flow defined in the PRD.
- Tasks marked `MVP1 = Yes` but not on critical path are quality/completeness tasks that can run in parallel.

## 4. Suggested Execution Waves

### Wave A - Foundation (Day 1 to Day 3 equivalent effort)
- T001, T002, T003, T004, T005, T006

### Wave B - Rules and Calendar (Day 3 to Day 5 equivalent effort)
- T007, T008, T009, T010, T011, T012

### Wave C - Data and Orchestration (Day 5 to Day 7 equivalent effort)
- T013, T014, T015, T016, T019, T020, T021, T022

### Wave D - MVP1 Data and Verification (Day 7 to Day 9 equivalent effort)
- T023, T024, T028, T029, T030, T031, T032, T033

### Wave E - Dashboard and Handover (Day 9 to Day 10 equivalent effort)
- T017, T018, T025, T026, T027

### Wave F - Post-MVP1 Readiness (Optional)
- T034, T035

### Wave G - MVP1 Governance and Handover Controls
- T036, T037, T038, T039

## 5. Deferred to V2

The following items are explicitly deferred and not required for MVP1 delivery:

- CI/CD quality gates
- Performance benchmarking
- Full idempotency and preservation of all rerun versions; MVP1 uses overwrite-on-rerun.
- Configuration approval workflow

## 6. Accepted Review Items Incorporated

The accepted review items are incorporated as follows:

- MVP Scope Confirmation: T036
- Configuration Validation: T006
- Schema Drift Validation: T037
- Provider Error Handling: T014
- Business UAT: T038
- Operational Runbook: T039

## 7. Definition of Done for MVP1

MVP1 is complete when all conditions are met:

- All `P0` tasks with `MVP1 = Yes` are completed and accepted.
- End-to-end Agency CN Monthly run produces expected `NOT_DUE`, `READY`, `LATE`, and `MISSING` outcomes using Excel source.
- Pre-run schema contract validation is active and blocks invalid configuration or source schema before execution.
- Dashboard displays latest status and history from persisted monitoring results.
- UAT is completed with documented acceptance decision.
- Operations runbook is published and reviewed.
- Contract-level architecture ambiguity is closed through implemented schemas and interface-aligned code.
- Test suite includes unit and integration coverage for rule engine, calendar, provider normalization, and orchestration pipeline.
