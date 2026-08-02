# Data Contract Provider for Apache Airflow

Run [Data Contract CLI](https://cli.datacontract.com) tests as quality gates in your Airflow DAGs.

[![CI](https://github.com/datacontract/airflow-provider-datacontract/actions/workflows/ci.yml/badge.svg)](https://github.com/datacontract/airflow-provider-datacontract/actions/workflows/ci.yml)

## Features

- `DataContractTestOperator` runs `datacontract test` against a contract and fails the task when the contract is violated, so bad data stops before it propagates downstream.
- Per-check results are rendered in the task log (pass/fail, reason, model/field).
- The full run report is pushed to XCom (key `datacontract_result`) in the test-results API model, so downstream tasks can branch on the outcome.
- On Airflow 3, a "Data Contract Results" view in the UI shows recent test runs across all DAGs.
- A "Test Results" button on the task instance links to the published results, e.g. in Entropy Data.

## Installation

```bash
pip install airflow-provider-datacontract
```

Extras are passed through to the Data Contract CLI, e.g. for Snowflake:

```bash
pip install "airflow-provider-datacontract[snowflake]"
```

Available extras: `duckdb` (local files, csv/parquet), `snowflake`, `databricks`, `bigquery`, `postgres`, `s3`, `azure`, `kafka`, `trino`.

## Usage

```python
from datetime import datetime
from airflow.sdk import dag
from datacontract_provider.operators.datacontract import DataContractTestOperator


@dag(schedule="0 2 * * *", start_date=datetime(2026, 1, 1), catchup=False)
def nightly_datacontract_test():
    DataContractTestOperator(
        task_id="test_orders_contract",
        data_contract_file="https://demo.datacontract.com/orders-latest/datacontract.yaml",
        server="production",
    )


nightly_datacontract_test()
```

### Operator parameters

| Parameter | Description |
|---|---|
| `data_contract_file` | Path or URL of the data contract YAML (templated) |
| `data_contract_str` | Contract as a YAML string, alternative to `data_contract_file` |
| `server` | Server key from the contract's `servers` section to test against |
| `schema_name` | Schema/model to test, defaults to all |
| `check_categories` | Subset of `schema`, `quality`, `servicelevel`, `custom` |
| `server_conn_id` | Airflow connection with credentials for the server under test (see below) |
| `entropy_data_conn_id` | Airflow connection for Entropy Data (password = API key, host optional) |
| `config` | Dict of additional [Data Contract CLI configuration](https://docs.datacontract.com/configuration) fields |
| `publish_url` | URL to publish test results to (optional) |
| `results_web_url` | Web page of the published results, shown as a "Test Results" button (optional) |
| `include_failed_samples` | Collect samples of failing rows |
| `fail_on_warning` | Also fail the task on result `warning` |
| `datacontract_kwargs` | Extra kwargs for the `DataContract` constructor, e.g. `spark` |

### Credentials via Airflow connections (recommended)

Pass `server_conn_id` to resolve credentials through Airflow's connection
machinery, including any configured secrets backend (Vault, AWS Secrets
Manager, Azure Key Vault, ...). The connection is mapped to
[Data Contract CLI configuration](https://docs.datacontract.com/configuration)
based on its type and passed programmatically; credentials never touch the
process environment.

```python
DataContractTestOperator(
    task_id="test_orders_contract",
    data_contract_file="...",
    server="production",
    server_conn_id="databricks_prod",       # conn type: databricks
    entropy_data_conn_id="entropy_data",    # conn type: entropydata
)
```

The provider registers an **Entropy Data** connection type: create a
connection with type `entropydata`, put the API key in the password field,
and optionally override the host (default `https://api.entropy-data.com`).
When `entropy_data_conn_id` is set and no `publish_url` is given, test
results are published to `<host>/api/test-results` automatically.

Supported connection types: `databricks` (host, extra `http_path`; token
auth: password = token, login empty; service principal OAuth: login =
client id, password = client secret), `snowflake` (login/password, extra
`account`, `warehouse`, `role`), `postgres`, `mysql`, `oracle`, `impala`,
`trino`, `mssql`, `redshift` (login/password/host/port/schema), `aws`
(login/password=key pair, extra `region_name`), `google_cloud_platform`
(extra `key_path`, `project`), `wasb`/`azure`, and `kafka`. For anything else, add
`datacontract_`-prefixed keys to the connection extra
(e.g. `datacontract_trino_jwt_token`); those pass through to any config field
and also override the mapped values. The `config` parameter is merged last.

Requires `datacontract-cli >= 1.0`. Alternatively, the CLI still reads
credentials from environment variables, e.g. `DATACONTRACT_SNOWFLAKE_USERNAME`,
set on the worker.

### XCom

The operator pushes two XCom entries:

- `datacontract_result`: the full run report in the shape of the test-results API model (the Data Contract CLI `Run`): `{runId, dataContractId, dataContractVersion, server, timestampStart, timestampEnd, result, checks: [{name, result, category, type, model, field, reason, diagnostics, ...}], logs}`. `None` fields are omitted. This is the same JSON the CLI publishes to `/api/test-results`.
- `datacontract_results_url`: the `results_web_url`, if configured

### Results view in the Airflow UI (Airflow 3.1+)

The provider ships a React app (registered via the plugin `react_apps`
interface) that adds a **Data Contract Results** entry to the navigation,
rendering the most recent test runs across all DAGs natively in the Airflow
UI, with expandable check details and auto-refresh. The data comes from XCom
via `/datacontract/api/results`; a standalone HTML fallback is available at
`/datacontract/results`. On Airflow 2 the plugin degrades gracefully and only
registers the extra link.

The React source lives in `ui/`; the built UMD bundle is committed at
`src/datacontract_provider/static/main.umd.cjs` and shipped with the package
(rebuild with `cd ui && npm install && npm run build`, then copy
`ui/dist/main.umd.cjs` there).

### Entropy Data (optional)

To publish test results to [Entropy Data](https://entropy-data.com) (formerly
Data Mesh Manager), set the `ENTROPY_DATA_API_KEY` environment variable on
the worker and configure:

```python
DataContractTestOperator(
    task_id="test_orders_contract",
    data_contract_file="...",
    server="production",
    publish_url="https://api.entropy-data.com/api/test-results",
    results_web_url="https://app.entropy-data.com/...",  # optional deep link
)
```

## Version support

- Apache Airflow 2.10+ and 3.x (the UI results view requires Airflow 3)
- Python 3.10+

## Development

```bash
pip install -e ".[dev]"
ruff check src tests
pytest
```

## License

[MIT](LICENSE)
