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
| T002 | Finalize domain model classes | 0.5 day | P0 | Yes | T001 (FS) | `config_models.py` and `result_models.py` include models aligned with architecture schemas (KPI config, ready rule, calendar entry, monitoring result); model validation works for sample payloads. |
| T003 | Implement configuration loader entrypoint | 0.5 day | P0 | Yes | T002 (FS) | Config loader resolves configured source type and returns typed config entities; loader handles invalid source selection with clear error. |
| T004 | Build Excel configuration reader | 0.5 day | P0 | Yes | T003 (FS) | Excel configuration files can be read into normalized dataframes; column normalization rules are applied; malformed sheet structure returns validation error. |
| T005 | Implement source table mapping resolution | 0.5 day | P0 | Yes | T004 (FS) | Logical `source_table_key` resolves to physical Excel object name per market; missing mapping is detected and reported. |
| T006 | Implement configuration validation rules | 0.75 day | P0 | Yes | T004 (FS), T005 (FS) | Validation catches overlapping effective dates, missing ready rules, invalid calendar code references, and duplicate active KPI keys; validation report is machine-readable. |
| T007 | Implement business calendar data loading | 0.5 day | P0 | Yes | T004 (FS) | CN calendar entries load with complete date coverage for test period; duplicates and missing dates are detected. |
| T008 | Implement business calendar service core functions | 0.75 day | P0 | Yes | T007 (FS) | `is_business_day`, `add_business_days`, `add_calendar_days`, next/previous business day behaviors verified by unit tests on weekends and holidays. |
| T009 | Implement ready-rule parser | 0.5 day | P0 | Yes | T002 (FS), T008 (FS) | Parser supports `M+nBD`, `M+nCD`, `D+nBD`, `D+nCD`; invalid formats are rejected with explicit error. |
| T010 | Implement expected ready date calculator | 0.5 day | P0 | Yes | T009 (FS), T008 (FS) | Expected ready date computation matches architecture rules for monthly anchor `M` and daily anchor `D`; unit tests pass for CN examples. |
| T011 | Define readiness condition evaluator primitives | 0.5 day | P0 | Yes | T002 (FS) | Evaluator supports `record_exists`, `record_count_greater_than`, `required_column_not_null`; each condition returns pass/fail plus reason. |
| T012 | Implement composite readiness evaluator (`all_of`, `any_of`) | 0.5 day | P0 | Yes | T011 (FS) | Nested condition evaluation works; `all_of` returns first failed reason; `any_of` returns aggregated failure when all fail. |
| T013 | Implement Excel data provider table read | 0.5 day | P0 | Yes | T001 (FS), T005 (FS) | Provider reads source data by logical key and date range; returns normalized dataframe with expected columns and dtypes. |
| T014 | Implement provider error mapping and retry handling | 0.5 day | P1 | Yes | T013 (FS) | Provider raises standardized error categories for config, schema, and transient failures; retry behavior defined for transient errors. |
| T015 | Implement provider factory selection | 0.25 day | P0 | Yes | T013 (FS) | Factory creates provider from configuration; unsupported provider type fails fast with clear message. |
| T016 | Implement result repository write path (MVP memory/file) | 0.5 day | P0 | Yes | T002 (FS) | Monitoring results persist with execution metadata and result version; save operation is idempotent per key+version policy. |
| T017 | Implement latest result retrieval query | 0.5 day | P1 | Yes | T016 (FS) | Latest query returns newest version per KPI slice and monitoring date; filters (channel, market, frequency, status) function correctly. |
| T018 | Implement result history retrieval query | 0.5 day | P1 | Yes | T016 (FS) | History query returns ordered results across date range including multiple versions where present. |
| T019 | Build monitoring orchestration skeleton | 0.5 day | P0 | Yes | T006 (FS), T015 (FS), T016 (FS) | Orchestrator accepts run parameters (`channel`, `market`, `frequency`, `monitoring_date`) and executes configuration-to-result pipeline steps without KPI-specific branching. |
| T020 | Implement per-KPI execution loop | 0.75 day | P0 | Yes | T019 (FS), T010 (FS), T012 (FS), T013 (FS) | For each active KPI, system computes expected date, evaluates readiness, derives actual date and status, and creates output record matching monitoring result schema. |
| T021 | Add execution metadata and versioning strategy | 0.5 day | P1 | Yes | T020 (FS), T016 (FS) | Execution ID generation, execution timestamp, and version increment behavior are deterministic and documented; rerun scenario covered by tests. |
| T022 | Implement monitoring status derivation rules | 0.5 day | P0 | Yes | T020 (FS) | `Ready`, `Late`, `Missing` semantics implemented exactly as architecture definitions and verified via unit tests. |
| T023 | Seed MVP1 sample configuration data | 0.5 day | P0 | Yes | T006 (FS), T007 (FS) | Agency-CN-Monthly representative KPI config, ready rules, calendar, and source mappings are available and pass validation. |
| T024 | Prepare MVP1 sample Excel source data | 0.5 day | P0 | Yes | T013 (SS), T023 (SS) | Sample source tables include ready, late, and missing cases; data conforms to normalized contract expectations. |
| T025 | Build Streamlit dashboard skeleton and navigation | 0.5 day | P1 | Yes | T017 (FS), T018 (FS) | Dashboard loads successfully and includes overview plus drill-down navigation structure. |
| T026 | Implement dashboard KPI status summary view | 0.5 day | P1 | Yes | T025 (FS), T022 (FS) | Summary cards and table show counts by status and filtering by channel/market/frequency; values match repository output. |
| T027 | Implement dashboard trend/history view | 0.5 day | P1 | Yes | T025 (FS), T018 (FS) | Trend view renders historical KPI statuses over time and supports KPI selection for Agency CN monthly scope. |
| T028 | Add unit tests for calendar and rule engine | 0.75 day | P0 | Yes | T010 (FS), T012 (FS) | Test suite covers rule parsing, expected date calculations, and readiness condition evaluation with pass/fail variants. |
| T029 | Add unit tests for provider normalization | 0.5 day | P1 | Yes | T013 (FS), T014 (FS) | Tests verify normalized columns, data types, null handling, and error mapping behavior for Excel provider. |
| T030 | Add integration test for end-to-end monthly run | 0.75 day | P0 | Yes | T020 (FS), T023 (FS), T024 (FS), T016 (FS) | One run from config load to result persistence succeeds and produces expected statuses for ready, late, missing sample KPIs. |
| T031 | Add regression test for rerun version behavior | 0.5 day | P1 | Yes | T021 (FS), T030 (FS) | Re-execution on same monitoring date produces correct version semantics and preserves prior versions. |
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

T036 -> T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008 -> T009 -> T010 -> T011 -> T012 -> T013 -> T014 -> T015 -> T016 -> T019 -> T020 -> T022 -> T023 -> T024 -> T037 -> T030 -> T025 -> T026 -> T038 -> T039

Notes:
- Daily monitoring support remains in architecture scope; MVP1 implementation validates monthly CN flow first as defined in PRD implementation scope.
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
- Idempotency
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
- End-to-end Agency CN Monthly run produces expected `Ready`, `Late`, and `Missing` outcomes using Excel source.
- Pre-run schema contract validation is active and blocks invalid configuration or source schema before execution.
- Dashboard displays latest status and history from persisted monitoring results.
- UAT is completed with documented acceptance decision.
- Operations runbook is published and reviewed.
- Contract-level architecture ambiguity is closed through implemented schemas and interface-aligned code.
- Test suite includes unit and integration coverage for rule engine, calendar, provider normalization, and orchestration pipeline.
