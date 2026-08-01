import json
import sys
import types
from unittest.mock import MagicMock, patch

from airflow.models import Connection
from test_operator import FakeRun

from datacontract_provider.operators.datacontract import DataContractTestOperator


class FakeConfig:
    def __init__(self, **kwargs):
        self.fields = kwargs


def _install_fake_datacontract(monkeypatch, run):
    instance = MagicMock()
    instance.test.return_value = run
    data_contract_cls = MagicMock(return_value=instance)

    module = types.ModuleType("datacontract.data_contract")
    module.DataContract = data_contract_cls
    package = types.ModuleType("datacontract")
    package.data_contract = module
    package.Config = FakeConfig
    monkeypatch.setitem(sys.modules, "datacontract", package)
    monkeypatch.setitem(sys.modules, "datacontract.data_contract", module)
    return data_contract_cls


def test_conn_ids_build_config(monkeypatch):
    dc_cls = _install_fake_datacontract(monkeypatch, FakeRun("passed", []))
    connections = {
        "databricks_prod": Connection(
            conn_id="databricks_prod",
            conn_type="databricks",
            host="adb-1.2.azuredatabricks.net",
            password="dapi-token",
            extra=json.dumps({"http_path": "/sql/1.0/warehouses/abc"}),
        ),
        "entropy_data": Connection(
            conn_id="entropy_data",
            conn_type="http",
            password="ed-key",
        ),
    }
    operator = DataContractTestOperator(
        task_id="test",
        data_contract_file="datacontract.yaml",
        server="production",
        server_conn_id="databricks_prod",
        entropy_data_conn_id="entropy_data",
        config={"max_errors": 25},
    )
    with patch.object(DataContractTestOperator, "_get_connection", side_effect=connections.get):
        operator.execute({"ti": MagicMock()})

    config = dc_cls.call_args.kwargs["config"]
    assert isinstance(config, FakeConfig)
    assert config.fields == {
        "databricks_server_hostname": "adb-1.2.azuredatabricks.net",
        "databricks_token": "dapi-token",
        "databricks_http_path": "/sql/1.0/warehouses/abc",
        "entropy_data_api_key": "ed-key",
        "max_errors": 25,
    }
    # publish_url is derived from the Entropy Data connection when not set explicitly
    assert dc_cls.call_args.kwargs["publish_url"] == "https://api.entropy-data.com/api/test-results"


def test_no_conn_id_means_no_config(monkeypatch):
    dc_cls = _install_fake_datacontract(monkeypatch, FakeRun("passed", []))
    operator = DataContractTestOperator(task_id="test", data_contract_file="datacontract.yaml")
    operator.execute({"ti": MagicMock()})
    assert "config" not in dc_cls.call_args.kwargs
