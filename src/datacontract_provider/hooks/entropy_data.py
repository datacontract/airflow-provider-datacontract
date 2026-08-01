from __future__ import annotations

from typing import Any

try:  # Airflow 3
    from airflow.sdk import BaseHook
except ImportError:  # Airflow 2
    from airflow.hooks.base import BaseHook

DEFAULT_HOST = "https://api.entropy-data.com"


class EntropyDataHook(BaseHook):
    """Connection to Entropy Data (https://entropy-data.com).

    The connection stores the API key as password and optionally a custom
    host (defaults to https://api.entropy-data.com). Used by
    :class:`~datacontract_provider.operators.datacontract.DataContractTestOperator`
    to publish test results.
    """

    conn_name_attr = "entropy_data_conn_id"
    default_conn_name = "entropy_data_default"
    conn_type = "entropy_data"
    hook_name = "Entropy Data"

    def __init__(self, entropy_data_conn_id: str = default_conn_name) -> None:
        super().__init__()
        self.entropy_data_conn_id = entropy_data_conn_id

    @classmethod
    def get_ui_field_behaviour(cls) -> dict[str, Any]:
        return {
            "hidden_fields": ["login", "schema", "port", "extra"],
            "relabeling": {
                "password": "API Key",
                "host": "Host",
            },
            "placeholders": {
                "host": DEFAULT_HOST,
            },
        }

    def config_fields(self) -> dict[str, Any]:
        """Data Contract CLI Config fields for this connection."""
        from datacontract_provider.connections import config_from_entropy_data_connection

        return config_from_entropy_data_connection(self.get_connection(self.entropy_data_conn_id))

    @property
    def host(self) -> str:
        conn = self.get_connection(self.entropy_data_conn_id)
        host = conn.host or DEFAULT_HOST
        return host if "://" in host else f"https://{host}"

    @property
    def publish_url(self) -> str:
        """The test-results publish endpoint for this connection."""
        return f"{self.host.rstrip('/')}/api/test-results"
