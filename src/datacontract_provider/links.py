from __future__ import annotations

from datacontract_provider.consts import XCOM_RESULTS_URL_KEY

try:  # Airflow 3
    from airflow.sdk import BaseOperatorLink
except ImportError:  # Airflow 2
    from airflow.models.baseoperatorlink import BaseOperatorLink


class TestResultsLink(BaseOperatorLink):
    """Button on the task instance that opens the published test results,
    e.g. in Entropy Data. Only shown when the operator pushed a results URL."""

    name = "Test Results"

    def get_link(self, operator, *, ti_key):
        from airflow.models import XCom

        return XCom.get_value(ti_key=ti_key, key=XCOM_RESULTS_URL_KEY) or ""
