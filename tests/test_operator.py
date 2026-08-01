import sys
import types
from unittest.mock import MagicMock

import pytest
from airflow.exceptions import AirflowException

from datacontract_provider.consts import XCOM_RESULT_KEY, XCOM_RESULTS_URL_KEY
from datacontract_provider.operators.datacontract import DataContractTestOperator


class FakeCheck:
    def __init__(self, result, name="check", reason=None, model=None, field=None, category="schema"):
        self.result = result
        self.name = name
        self.reason = reason
        self.model = model
        self.field = field
        self.category = category
        self.type = category


class FakeRun:
    def __init__(self, result, checks):
        self.result = result
        self.checks = checks

    def has_passed(self):
        return self.result == "passed"


def _install_fake_datacontract(monkeypatch, run):
    data_contract_instance = MagicMock()
    data_contract_instance.test.return_value = run
    data_contract_cls = MagicMock(return_value=data_contract_instance)

    module = types.ModuleType("datacontract.data_contract")
    module.DataContract = data_contract_cls
    package = types.ModuleType("datacontract")
    package.data_contract = module
    monkeypatch.setitem(sys.modules, "datacontract", package)
    monkeypatch.setitem(sys.modules, "datacontract.data_contract", module)
    return data_contract_cls


def test_passing_run_pushes_xcom(monkeypatch):
    run = FakeRun("passed", [FakeCheck("passed", name="row count"), FakeCheck("passed", name="not null")])
    dc_cls = _install_fake_datacontract(monkeypatch, run)

    operator = DataContractTestOperator(
        task_id="test",
        data_contract_file="datacontract.yaml",
        server="production",
    )
    ti = MagicMock()
    payload = operator.execute({"ti": ti})

    dc_cls.assert_called_once_with(data_contract_file="datacontract.yaml", server="production")
    assert payload["result"] == "passed"
    assert payload["checks_total"] == 2
    assert payload["checks_failed"] == 0
    ti.xcom_push.assert_any_call(key=XCOM_RESULT_KEY, value=payload)


def test_failing_run_raises_and_still_pushes_xcom(monkeypatch):
    run = FakeRun(
        "failed",
        [FakeCheck("passed"), FakeCheck("failed", name="freshness", reason="too old", model="orders")],
    )
    _install_fake_datacontract(monkeypatch, run)

    operator = DataContractTestOperator(task_id="test", data_contract_file="datacontract.yaml")
    ti = MagicMock()
    with pytest.raises(AirflowException, match="result 'failed'"):
        operator.execute({"ti": ti})

    payload = ti.xcom_push.call_args_list[0].kwargs["value"]
    assert payload["checks_failed"] == 1
    assert payload["checks"][1]["reason"] == "too old"


def test_warning_passes_unless_fail_on_warning(monkeypatch):
    run = FakeRun("warning", [FakeCheck("warning", name="slo")])
    _install_fake_datacontract(monkeypatch, run)

    operator = DataContractTestOperator(task_id="test", data_contract_file="datacontract.yaml")
    operator.execute({"ti": MagicMock()})

    _install_fake_datacontract(monkeypatch, FakeRun("warning", [FakeCheck("warning")]))
    strict = DataContractTestOperator(task_id="strict", data_contract_file="datacontract.yaml", fail_on_warning=True)
    with pytest.raises(AirflowException):
        strict.execute({"ti": MagicMock()})


def test_results_web_url_pushed_for_extra_link(monkeypatch):
    run = FakeRun("passed", [])
    _install_fake_datacontract(monkeypatch, run)

    operator = DataContractTestOperator(
        task_id="test",
        data_contract_file="datacontract.yaml",
        results_web_url="https://app.entropy-data.com/runs/42",
    )
    ti = MagicMock()
    operator.execute({"ti": ti})
    ti.xcom_push.assert_any_call(key=XCOM_RESULTS_URL_KEY, value="https://app.entropy-data.com/runs/42")


def test_requires_contract():
    with pytest.raises(ValueError):
        DataContractTestOperator(task_id="test")
