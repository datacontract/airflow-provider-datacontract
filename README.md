# Data Contract Provider for Apache Airflow

Run [Data Contract CLI](https://cli.datacontract.com) tests as quality gates in your Airflow DAGs.

[![CI](https://github.com/datacontract/airflow-provider-datacontract/actions/workflows/ci.yml/badge.svg)](https://github.com/datacontract/airflow-provider-datacontract/actions/workflows/ci.yml)

## Features

- `DataContractTestOperator` runs `datacontract test` against a contract and fails the task when the contract is violated, so bad data stops before it propagates downstream.
- Per-check results are rendered in the task log (pass/fail, reason, model/field).
- Structured results are pushed to XCom (key `datacontract_result`), so downstream tasks can branch on the outcome.
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

Available extras: `snowflake`, `databricks`, `bigquery`, `postgres`, `s3`, `azure`, `kafka`, `trino`.

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
| `publish_url` | URL to publish test results to (optional) |
| `results_web_url` | Web page of the published results, shown as a "Test Results" button (optional) |
| `include_failed_samples` | Collect samples of failing rows |
| `fail_on_warning` | Also fail the task on result `warning` |
| `datacontract_kwargs` | Extra kwargs for the `DataContract` constructor, e.g. `spark` |

Credentials for the server under test are read from environment variables by the
Data Contract CLI, e.g. `DATACONTRACT_SNOWFLAKE_USERNAME`. Set them on the
worker (secret-backed where possible).

### XCom

The operator pushes two XCom entries:

- `datacontract_result`: `{result, data_contract_file, server, checks_total, checks_failed, checks: [{name, result, category, type, model, field, reason}]}`
- `datacontract_results_url`: the `results_web_url`, if configured

### Results view in the Airflow UI (Airflow 3)

The provider ships a plugin that adds a **Data Contract Results** entry to the
navigation, rendering the most recent test runs across all DAGs with
expandable check details. It is served under `/datacontract/results` by the
API server and reads the results from XCom. On Airflow 2 the plugin degrades
gracefully and only registers the extra link.

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
