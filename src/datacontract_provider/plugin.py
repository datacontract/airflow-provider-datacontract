"""Airflow plugin that registers the operator extra link and, on Airflow 3.1+,
a React view in the UI that renders recent data contract test results
collected from XCom."""

from __future__ import annotations

import json
import logging
import mimetypes
from pathlib import Path

from airflow.plugins_manager import AirflowPlugin

from datacontract_provider.consts import XCOM_RESULT_KEY
from datacontract_provider.links import TestResultsLink

log = logging.getLogger(__name__)

_fastapi_apps: list = []
_react_apps: list = []

_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Data Contract Test Results</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, -apple-system, sans-serif; margin: 2rem; max-width: 72rem; }
  h1 { font-size: 1.3rem; }
  table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
  th, td { text-align: left; padding: 0.4rem 0.7rem; border-bottom: 1px solid rgba(128,128,128,0.35); }
  th { font-weight: 600; }
  .badge { padding: 0.1rem 0.5rem; border-radius: 0.6rem; font-size: 0.8rem; color: #fff; }
  .passed { background: #2e7d32; }
  .failed, .error { background: #c62828; }
  .warning { background: #ef6c00; }
  .unknown { background: #616161; }
  details { margin: 0; }
  summary { cursor: pointer; }
  .muted { opacity: 0.7; }
  ul.checks { margin: 0.4rem 0 0.2rem 1rem; padding: 0; }
  ul.checks li { margin: 0.15rem 0; list-style: none; }
</style>
</head>
<body>
<h1>Data Contract Test Results</h1>
<p class="muted">Most recent <code>datacontract test</code> runs, collected from XCom.</p>
<table id="results">
  <thead>
    <tr><th>Time</th><th>Dag / Task</th><th>Run</th><th>Contract</th><th>Result</th><th>Checks</th></tr>
  </thead>
  <tbody></tbody>
</table>
<script>
  function badge(result) {
    const cls = ["passed", "failed", "error", "warning"].includes(result) ? result : "unknown";
    return `<span class="badge ${cls}">${result}</span>`;
  }
  fetch("./api/results").then(r => r.json()).then(rows => {
    const tbody = document.querySelector("#results tbody");
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="muted">No results yet. Run a DataContractTestOperator task first.</td></tr>';
      return;
    }
    for (const row of rows) {
      const res = row.result || {};
      const checks = res.checks || [];
      const notPassed = checks.filter(c => c.result && c.result !== "passed");
      const failing = notPassed.map(c =>
        `<li>${c.result === "warning" ? "⚠" : "✗"} ${c.name || c.type || "check"}` +
        `${c.model ? " (" + [c.model, c.field].filter(Boolean).join(".") + ")" : ""}` +
        `${c.reason ? ": " + c.reason : ""}</li>`).join("");
      const checksCell = !checks.length ? "" :
        `${checks.length - notPassed.length}/${checks.length} passed` +
        (failing ? `<details><summary>details</summary><ul class="checks">${failing}</ul></details>` : "");
      const contract = res.dataContractId
        ? res.dataContractId + (res.dataContractVersion ? " @ " + res.dataContractVersion : "")
        : (res.data_contract_file || "");
      const tr = document.createElement("tr");
      tr.innerHTML =
        `<td>${(row.timestamp || "").replace("T", " ").slice(0, 19)}</td>` +
        `<td>${row.dag_id} / ${row.task_id}</td>` +
        `<td class="muted">${row.run_id || ""}</td>` +
        `<td>${contract}</td>` +
        `<td>${badge(res.result || "unknown")}</td>` +
        `<td>${checksCell}</td>`;
      tbody.appendChild(tr);
    }
  });
</script>
</body>
</html>
"""

try:
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

    mimetypes.add_type("application/javascript", ".cjs")
    _STATIC_DIR = Path(__file__).parent / "static"

    def _recent_results(limit: int) -> list[dict]:
        from airflow.utils.session import create_session

        try:  # Airflow 3
            from airflow.models.xcom import XComModel as XComDb
        except ImportError:  # pragma: no cover
            from airflow.models.xcom import XCom as XComDb

        rows = []
        with create_session() as session:
            query = (
                session.query(XComDb)
                .filter(XComDb.key == XCOM_RESULT_KEY)
                .order_by(XComDb.timestamp.desc())
                .limit(limit)
            )
            for xcom in query:
                value = xcom.value
                if isinstance(value, (str, bytes)):
                    try:
                        value = json.loads(value)
                    except (ValueError, TypeError):
                        value = None
                rows.append(
                    {
                        "dag_id": xcom.dag_id,
                        "task_id": xcom.task_id,
                        "run_id": getattr(xcom, "run_id", None),
                        "timestamp": xcom.timestamp.isoformat() if xcom.timestamp else None,
                        "result": value if isinstance(value, dict) else {},
                    }
                )
        return rows

    app = FastAPI(title="Data Contract Test Results")

    @app.get("/api/results")
    def api_results(limit: int = 50):
        return JSONResponse(_recent_results(min(limit, 200)))

    @app.get("/results")
    def results_page():
        return HTMLResponse(_PAGE)

    @app.get("/static/main.umd.cjs")
    def react_bundle():
        return FileResponse(_STATIC_DIR / "main.umd.cjs", media_type="application/javascript")

    _fastapi_apps = [{"app": app, "url_prefix": "/datacontract", "name": "Data Contract Results"}]
    _react_apps = [
        {
            "name": "Data Contract Results",
            "bundle_url": "/datacontract/static/main.umd.cjs",
            "url_route": "datacontract-results",
            "destination": "nav",
        }
    ]
except ImportError:  # Airflow 2: no FastAPI-based UI plugins
    log.debug("FastAPI not available, Data Contract results view is disabled (requires Airflow 3)")


class DataContractPlugin(AirflowPlugin):
    name = "datacontract"
    operator_extra_links = (TestResultsLink(),)
    fastapi_apps = _fastapi_apps
    # React view in the Airflow UI (Airflow 3.1+; ignored on older versions).
    react_apps = _react_apps
