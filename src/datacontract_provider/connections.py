"""Map Airflow connections to Data Contract CLI Config fields.

See https://docs.datacontract.com/configuration for the full field list.
Values from a connection's ``extra`` that are prefixed with ``datacontract_``
are always passed through (prefix stripped), so any Config field can be set
even for connection types that have no explicit mapping here.
"""

from __future__ import annotations

from typing import Any

_SQL_LIKE = {
    "postgres": "postgres",
    "mysql": "mysql",
    "oracle": "oracle",
    "impala": "impala",
    "trino": "trino",
    "mssql": "sqlserver",
    "redshift": "redshift",
}


def _set(config: dict[str, Any], key: str, value: Any) -> None:
    if value not in (None, ""):
        config[key] = value


def _passthrough(config: dict[str, Any], extra: dict[str, Any]) -> None:
    for key, value in extra.items():
        lower = key.lower()
        if lower.startswith("datacontract_"):
            _set(config, lower.removeprefix("datacontract_"), value)


def config_from_server_connection(conn: Any) -> dict[str, Any]:
    """Build a Config field dict from an Airflow connection for the server under test."""
    conn_type = (conn.conn_type or "").lower()
    extra = conn.extra_dejson or {}
    config: dict[str, Any] = {}

    if conn_type == "databricks":
        host = (conn.host or "").removeprefix("https://").removeprefix("http://").rstrip("/")
        _set(config, "databricks_server_hostname", host)
        if conn.login:
            # Login set: service principal OAuth (login = client id, password = client secret)
            _set(config, "databricks_client_id", conn.login)
            _set(config, "databricks_client_secret", conn.password)
        else:
            # No login: password is a personal access / SP token
            _set(config, "databricks_token", conn.password)
        _set(config, "databricks_http_path", extra.get("http_path"))
        _set(config, "databricks_client_id", extra.get("client_id"))
        _set(config, "databricks_client_secret", extra.get("client_secret"))
    elif conn_type == "snowflake":
        _set(config, "snowflake_username", conn.login)
        _set(config, "snowflake_password", conn.password)
        for key in ("account", "warehouse", "role", "authenticator", "private_key_file"):
            _set(config, f"snowflake_{key}", extra.get(key))
    elif conn_type in _SQL_LIKE:
        prefix = _SQL_LIKE[conn_type]
        _set(config, f"{prefix}_username", conn.login)
        _set(config, f"{prefix}_password", conn.password)
        _set(config, f"{prefix}_host", conn.host)
        _set(config, f"{prefix}_port", conn.port)
        if prefix in ("postgres", "mysql", "sqlserver", "redshift", "impala"):
            _set(config, f"{prefix}_database", conn.schema)
        if prefix == "oracle":
            _set(config, "oracle_service_name", extra.get("service_name"))
    elif conn_type == "aws":
        _set(config, "s3_access_key_id", conn.login)
        _set(config, "s3_secret_access_key", conn.password)
        _set(config, "s3_region", extra.get("region_name"))
        _set(config, "s3_session_token", extra.get("aws_session_token"))
    elif conn_type == "google_cloud_platform":
        _set(
            config,
            "bigquery_account_info_json_path",
            extra.get("key_path") or extra.get("extra__google_cloud_platform__key_path"),
        )
        _set(
            config,
            "bigquery_project",
            extra.get("project") or extra.get("extra__google_cloud_platform__project"),
        )
    elif conn_type in ("wasb", "azure", "adls"):
        _set(config, "azure_connection_string", extra.get("connection_string"))
        _set(config, "azure_tenant_id", extra.get("tenant_id"))
        _set(config, "azure_client_id", extra.get("client_id") or conn.login)
        _set(config, "azure_client_secret", extra.get("client_secret") or conn.password)
    elif conn_type == "kafka":
        _set(config, "kafka_sasl_username", conn.login)
        _set(config, "kafka_sasl_password", conn.password)
        _set(config, "kafka_schema_registry_url", extra.get("schema_registry_url"))
    else:
        has_passthrough = any(k.lower().startswith("datacontract_") for k in extra)
        if not has_passthrough:
            raise ValueError(
                f"No Data Contract CLI mapping for connection type '{conn_type}' "
                f"(connection '{conn.conn_id}'). Supported types: databricks, snowflake, "
                f"{', '.join(sorted(_SQL_LIKE))}, aws, google_cloud_platform, wasb, kafka. "
                "Alternatively, add 'datacontract_'-prefixed keys to the connection extra, "
                "e.g. datacontract_databricks_token."
            )

    _passthrough(config, extra)
    return config


def config_from_entropy_data_connection(conn: Any) -> dict[str, Any]:
    """Build a Config field dict from an Airflow connection for Entropy Data."""
    extra = conn.extra_dejson or {}
    config: dict[str, Any] = {}
    _set(config, "entropy_data_api_key", conn.password or extra.get("api_key"))
    if conn.host:
        host = conn.host if "://" in conn.host else f"https://{conn.host}"
        _set(config, "entropy_data_host", host)
    _passthrough(config, extra)
    return config
