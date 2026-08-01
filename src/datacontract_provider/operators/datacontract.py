from __future__ import annotations

from collections.abc import Collection
from typing import Any

from airflow.exceptions import AirflowException

from datacontract_provider.connections import (
    config_from_entropy_data_connection,
    config_from_server_connection,
)
from datacontract_provider.consts import XCOM_RESULT_KEY, XCOM_RESULTS_URL_KEY
from datacontract_provider.links import TestResultsLink

try:  # Airflow 3
    from airflow.sdk import BaseOperator
except ImportError:  # Airflow 2
    from airflow.models import BaseOperator

_ICONS = {"passed": "✓", "warning": "⚠", "failed": "✗", "error": "✗", "skipped": "-", "info": "i"}


def _plain(value: Any) -> Any:
    """Normalize enums and other scalars to JSON-friendly values."""
    if value is None:
        return None
    return getattr(value, "value", value)


class DataContractTestOperator(BaseOperator):
    """Run ``datacontract test`` for a data contract and fail the task if the contract is violated.

    The full check results are written to the task log and pushed to XCom
    (key ``datacontract_result``), so downstream tasks can branch on the outcome.

    :param data_contract_file: Path or URL of the data contract YAML. Templated.
    :param data_contract_str: The data contract as a YAML string, as an alternative
        to ``data_contract_file``. Templated.
    :param server: Server (key in the contract's ``servers`` section) to test against. Templated.
    :param schema_name: Schema/model to test, defaults to all. Templated.
    :param check_categories: Subset of check categories to run,
        e.g. ``{"schema", "quality"}``.
    :param server_conn_id: Airflow connection with credentials for the server under
        test. Mapped to Data Contract CLI configuration based on the connection type
        (databricks, snowflake, postgres, mysql, oracle, impala, trino, mssql,
        redshift, aws, google_cloud_platform, wasb, kafka). Keys in the connection
        extra prefixed with ``datacontract_`` are passed through as additional
        configuration. Resolved via Airflow's secrets machinery; credentials are
        passed programmatically and never written to the process environment.
    :param entropy_data_conn_id: Airflow connection for Entropy Data. The
        connection password (or ``api_key`` in extra) becomes the API key, the
        host (if set) the Entropy Data host.
    :param config: Additional Data Contract CLI configuration fields
        (see https://docs.datacontract.com/configuration), merged over the
        connection-derived values.
    :param publish_url: Optional URL to publish the test results to, e.g.
        ``https://api.entropy-data.com/api/test-results`` for Entropy Data
        (API key via ``entropy_data_conn_id`` or the ``ENTROPY_DATA_API_KEY``
        environment variable). Templated.
    :param results_web_url: Optional URL of a web page showing the published results.
        When set, it is exposed as a "Test Results" button on the task instance. Templated.
    :param include_failed_samples: Collect a sample of failing rows in the results.
    :param fail_on_warning: Also fail the task when the run result is ``warning``.
    :param datacontract_kwargs: Extra keyword arguments passed through to the
        ``DataContract`` constructor, e.g. ``spark`` or ``duckdb_connection``.
    """

    template_fields = (
        "data_contract_file",
        "data_contract_str",
        "server",
        "schema_name",
        "server_conn_id",
        "entropy_data_conn_id",
        "publish_url",
        "results_web_url",
    )
    ui_color = "#8bd0c0"
    operator_extra_links = (TestResultsLink(),)

    def __init__(
        self,
        *,
        data_contract_file: str | None = None,
        data_contract_str: str | None = None,
        server: str | None = None,
        schema_name: str | None = None,
        check_categories: Collection[str] | None = None,
        server_conn_id: str | None = None,
        entropy_data_conn_id: str | None = None,
        config: dict[str, Any] | None = None,
        publish_url: str | None = None,
        results_web_url: str | None = None,
        include_failed_samples: bool = False,
        fail_on_warning: bool = False,
        datacontract_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not data_contract_file and not data_contract_str:
            raise ValueError("Either data_contract_file or data_contract_str must be provided")
        self.data_contract_file = data_contract_file
        self.data_contract_str = data_contract_str
        self.server = server
        self.schema_name = schema_name
        self.check_categories = check_categories
        self.server_conn_id = server_conn_id
        self.entropy_data_conn_id = entropy_data_conn_id
        self.config = config
        self.publish_url = publish_url
        self.results_web_url = results_web_url
        self.include_failed_samples = include_failed_samples
        self.fail_on_warning = fail_on_warning
        self.datacontract_kwargs = datacontract_kwargs

    def execute(self, context: Any) -> dict[str, Any]:
        from datacontract.data_contract import DataContract

        dc_kwargs: dict[str, Any] = dict(self.datacontract_kwargs or {})
        if self.data_contract_file:
            dc_kwargs["data_contract_file"] = self.data_contract_file
        if self.data_contract_str:
            dc_kwargs["data_contract_str"] = self.data_contract_str
        if self.server:
            dc_kwargs["server"] = self.server
        if self.schema_name:
            dc_kwargs["schema_name"] = self.schema_name
        if self.check_categories:
            dc_kwargs["check_categories"] = set(self.check_categories)
        if self.publish_url:
            dc_kwargs["publish_url"] = self.publish_url
        if self.include_failed_samples:
            dc_kwargs["include_failed_samples"] = True

        config_fields = self._build_config_fields()
        if config_fields:
            dc_kwargs["config"] = self._build_config(config_fields)

        run = DataContract(**dc_kwargs).test()

        payload = self._build_payload(run)
        self._log_run(payload)

        ti = context["ti"]
        ti.xcom_push(key=XCOM_RESULT_KEY, value=payload)
        if self.results_web_url:
            ti.xcom_push(key=XCOM_RESULTS_URL_KEY, value=self.results_web_url)

        result = payload["result"]
        if result in ("failed", "error") or (self.fail_on_warning and result == "warning"):
            raise AirflowException(
                f"Data contract test finished with result '{result}' "
                f"({payload['checks_failed']} of {payload['checks_total']} checks failed)"
            )
        return payload

    def _build_config_fields(self) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if self.server_conn_id:
            fields.update(config_from_server_connection(self._get_connection(self.server_conn_id)))
        if self.entropy_data_conn_id:
            fields.update(config_from_entropy_data_connection(self._get_connection(self.entropy_data_conn_id)))
        if self.config:
            fields.update(self.config)
        if fields:
            self.log.info("Data Contract CLI configuration from connections: %s", ", ".join(sorted(fields)))
        return fields

    @staticmethod
    def _get_connection(conn_id: str) -> Any:
        try:  # Airflow 3
            from airflow.sdk import BaseHook
        except ImportError:  # Airflow 2
            from airflow.hooks.base import BaseHook
        return BaseHook.get_connection(conn_id)

    @staticmethod
    def _build_config(fields: dict[str, Any]) -> Any:
        try:
            from datacontract import Config
        except ImportError as e:
            raise AirflowException(
                "server_conn_id / entropy_data_conn_id / config require datacontract-cli >= 1.0 "
                "with programmatic configuration support (https://docs.datacontract.com/configuration)."
            ) from e
        return Config(**fields)

    def _build_payload(self, run: Any) -> dict[str, Any]:
        checks = []
        for check in getattr(run, "checks", None) or []:
            checks.append(
                {
                    "name": _plain(getattr(check, "name", None)),
                    "result": _plain(getattr(check, "result", None)),
                    "category": _plain(getattr(check, "category", None)),
                    "type": _plain(getattr(check, "type", None)),
                    "model": _plain(getattr(check, "model", None)),
                    "field": _plain(getattr(check, "field", None)),
                    "reason": _plain(getattr(check, "reason", None)),
                }
            )
        failed = sum(1 for c in checks if c["result"] in ("failed", "error"))
        return {
            "result": _plain(getattr(run, "result", None)) or "unknown",
            "data_contract_file": self.data_contract_file,
            "server": self.server,
            "checks_total": len(checks),
            "checks_failed": failed,
            "checks": checks,
        }

    def _log_run(self, payload: dict[str, Any]) -> None:
        result = payload["result"]
        self.log.info("Data contract test result: %s", str(result).upper())
        self.log.info(
            "%s of %s checks passed",
            payload["checks_total"] - payload["checks_failed"],
            payload["checks_total"],
        )
        for check in payload["checks"]:
            icon = _ICONS.get(check["result"], "?")
            location = ".".join(x for x in (check["model"], check["field"]) if x)
            line = f"{icon} [{check['result']}] {check['name'] or check['type'] or 'check'}"
            if location:
                line += f" ({location})"
            if check["reason"] and check["result"] != "passed":
                line += f": {check['reason']}"
            if check["result"] in ("failed", "error"):
                self.log.error("%s", line)
            elif check["result"] == "warning":
                self.log.warning("%s", line)
            else:
                self.log.info("%s", line)
