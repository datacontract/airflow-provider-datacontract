import sys
import types
from unittest.mock import MagicMock

import pytest
from airflow.exceptions import AirflowException

from datacontract_provider.consts import XCOM_RESULT_KEY, XCOM_RESULTS_URL_KEY
from datacontract_provider.operators.datacontract import DataContractTestOperator


def make_check(result, name="check", reason=None, model=None, field=None, category="schema"):
    from datacontract.model.run import Check

    return Check(type=category, category=category, name=name, result=result, reason=reason, model=model, field=field)


def make_run(result, checks):
    from datacontract.model.run import Run

    run = Run.create_run()
    run.result = result
    run.checks = checks
    return run


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
    run = make_run("passed", [make_check("passed", name="row count"), make_check("passed", name="not null")])
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
    # Full test-results API model shape (datacontract-cli Run)
    assert "runId" in payload
    assert "timestampStart" in payload
    assert [c["name"] for c in payload["checks"]] == ["row count", "not null"]
    assert all(c["result"] == "passed" for c in payload["checks"])
    ti.xcom_push.assert_any_call(key=XCOM_RESULT_KEY, value=payload)


def test_failing_run_raises_and_still_pushes_xcom(monkeypatch):
    run = make_run(
        "failed",
        [make_check("passed"), make_check("failed", name="freshness", reason="too old", model="orders")],
    )
    _install_fake_datacontract(monkeypatch, run)

    operator = DataContractTestOperator(task_id="test", data_contract_file="datacontract.yaml")
    ti = MagicMock()
    with pytest.raises(AirflowException, match="result 'failed'"):
        operator.execute({"ti": ti})

    payload = ti.xcom_push.call_args_list[0].kwargs["value"]
    assert payload["result"] == "failed"
    assert payload["checks"][1]["reason"] == "too old"
    assert payload["checks"][1]["model"] == "orders"


def test_warning_passes_unless_fail_on_warning(monkeypatch):
    run = make_run("warning", [make_check("warning", name="slo")])
    _install_fake_datacontract(monkeypatch, run)

    operator = DataContractTestOperator(task_id="test", data_contract_file="datacontract.yaml")
    operator.execute({"ti": MagicMock()})

    _install_fake_datacontract(monkeypatch, make_run("warning", [make_check("warning")]))
    strict = DataContractTestOperator(task_id="strict", data_contract_file="datacontract.yaml", fail_on_warning=True)
    with pytest.raises(AirflowException):
        strict.execute({"ti": MagicMock()})


def test_results_web_url_pushed_for_extra_link(monkeypatch):
    run = make_run("passed", [])
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
