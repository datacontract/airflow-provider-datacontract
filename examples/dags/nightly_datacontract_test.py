"""Nightly data contract test as a quality gate."""

from datetime import datetime

from datacontract_provider.operators.datacontract import DataContractTestOperator

try:  # Airflow 3
    from airflow.sdk import dag
except ImportError:  # Airflow 2
    from airflow.decorators import dag


@dag(
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["datacontract"],
)
def nightly_datacontract_test():
    DataContractTestOperator(
        task_id="test_orders_contract",
        data_contract_file="https://demo.datacontract.com/orders-latest/datacontract.yaml",
        # server="production",
        # Optional: publish results to Entropy Data (set ENTROPY_DATA_API_KEY on the worker)
        # publish_url="https://api.entropy-data.com/api/test-results",
        # results_web_url="https://app.entropy-data.com/...",  # adds a "Test Results" button
    )


nightly_datacontract_test()
