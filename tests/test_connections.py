import json

import pytest
from airflow.models import Connection

from datacontract_provider.connections import (
    config_from_entropy_data_connection,
    config_from_server_connection,
)


def test_databricks_connection():
    conn = Connection(
        conn_id="databricks_prod",
        conn_type="databricks",
        host="https://adb-123.4.azuredatabricks.net",
        password="dapi-token",
        extra=json.dumps({"http_path": "/sql/1.0/warehouses/abc"}),
    )
    config = config_from_server_connection(conn)
    assert config == {
        "databricks_server_hostname": "adb-123.4.azuredatabricks.net",
        "databricks_token": "dapi-token",
        "databricks_http_path": "/sql/1.0/warehouses/abc",
    }


def test_snowflake_connection():
    conn = Connection(
        conn_id="sf",
        conn_type="snowflake",
        login="user",
        password="secret",
        extra=json.dumps({"account": "xy123", "warehouse": "COMPUTE_WH", "role": "TESTER"}),
    )
    config = config_from_server_connection(conn)
    assert config["snowflake_username"] == "user"
    assert config["snowflake_password"] == "secret"
    assert config["snowflake_account"] == "xy123"
    assert config["snowflake_warehouse"] == "COMPUTE_WH"
    assert config["snowflake_role"] == "TESTER"


def test_postgres_connection_maps_schema_to_database():
    conn = Connection(
        conn_id="pg",
        conn_type="postgres",
        host="db.example.com",
        port=5432,
        login="u",
        password="p",
        schema="appdb",
    )
    config = config_from_server_connection(conn)
    assert config["postgres_host"] == "db.example.com"
    assert config["postgres_port"] == 5432
    assert config["postgres_database"] == "appdb"


def test_datacontract_prefixed_extra_passthrough_overrides():
    conn = Connection(
        conn_id="databricks_prod",
        conn_type="databricks",
        password="token",
        extra=json.dumps({"datacontract_databricks_catalog": "prod_catalog"}),
    )
    config = config_from_server_connection(conn)
    assert config["databricks_catalog"] == "prod_catalog"


def test_unknown_type_without_passthrough_raises():
    conn = Connection(conn_id="ftp1", conn_type="ftp", host="x")
    with pytest.raises(ValueError, match="No Data Contract CLI mapping"):
        config_from_server_connection(conn)


def test_unknown_type_with_passthrough_works():
    conn = Connection(
        conn_id="generic1",
        conn_type="generic",
        extra=json.dumps({"datacontract_trino_jwt_token": "jwt"}),
    )
    assert config_from_server_connection(conn) == {"trino_jwt_token": "jwt"}


def test_entropy_data_connection():
    conn = Connection(
        conn_id="entropy_data",
        conn_type="http",
        host="api.entropy-data.com",
        password="ed-key",
    )
    config = config_from_entropy_data_connection(conn)
    assert config == {
        "entropy_data_api_key": "ed-key",
        "entropy_data_host": "https://api.entropy-data.com",
    }
