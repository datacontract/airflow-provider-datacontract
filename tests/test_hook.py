from unittest.mock import patch

from airflow.models import Connection

from datacontract_provider import get_provider_info
from datacontract_provider.hooks.entropy_data import EntropyDataHook


def test_connection_type_registered():
    info = get_provider_info()
    types = {c["connection-type"]: c["hook-class-name"] for c in info["connection-types"]}
    assert types["entropy_data"] == "datacontract_provider.hooks.entropy_data.EntropyDataHook"


def test_hook_class_attributes():
    assert EntropyDataHook.conn_type == "entropy_data"
    assert EntropyDataHook.hook_name == "Entropy Data"
    behaviour = EntropyDataHook.get_ui_field_behaviour()
    assert behaviour["relabeling"]["password"] == "API Key"
    assert "login" in behaviour["hidden_fields"]


def test_hook_defaults_and_publish_url():
    conn = Connection(conn_id="entropy_data", conn_type="entropy_data", password="key")
    with patch.object(EntropyDataHook, "get_connection", return_value=conn):
        hook = EntropyDataHook("entropy_data")
        assert hook.host == "https://api.entropy-data.com"
        assert hook.publish_url == "https://api.entropy-data.com/api/test-results"
        assert hook.config_fields() == {"entropy_data_api_key": "key"}


def test_hook_custom_host():
    conn = Connection(conn_id="entropy_data", conn_type="entropy_data", host="eu.example.com", password="key")
    with patch.object(EntropyDataHook, "get_connection", return_value=conn):
        hook = EntropyDataHook("entropy_data")
        assert hook.publish_url == "https://eu.example.com/api/test-results"
