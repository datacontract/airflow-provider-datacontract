import { FC, useCallback, useEffect, useState } from "react";

type Check = {
  name?: string;
  result?: string;
  category?: string;
  type?: string;
  model?: string;
  field?: string;
  reason?: string;
};

type RunResult = {
  result?: string;
  data_contract_file?: string;
  server?: string;
  checks_total?: number;
  checks_failed?: number;
  checks?: Check[];
};

type Row = {
  dag_id: string;
  task_id: string;
  run_id?: string;
  timestamp?: string;
  result: RunResult;
};

const palette = {
  passed: "#2e7d32",
  failed: "#c62828",
  error: "#c62828",
  warning: "#ef6c00",
  unknown: "#616161",
} as const;

const Badge: FC<{ result?: string }> = ({ result }) => {
  const key = (result ?? "unknown") as keyof typeof palette;
  const background = palette[key] ?? palette.unknown;
  return (
    <span
      style={{
        background,
        borderRadius: "0.6rem",
        color: "#fff",
        fontSize: "0.8rem",
        padding: "0.1rem 0.6rem",
        whiteSpace: "nowrap",
      }}
    >
      {result ?? "unknown"}
    </span>
  );
};

const cell: React.CSSProperties = {
  borderBottom: "1px solid rgba(128,128,128,0.3)",
  padding: "0.45rem 0.75rem",
  textAlign: "left",
  verticalAlign: "top",
};

const CheckList: FC<{ checks: Check[] }> = ({ checks }) => (
  <ul style={{ listStyle: "none", margin: "0.4rem 0 0.2rem 1rem", padding: 0 }}>
    {checks.map((check, index) => (
      <li key={index} style={{ margin: "0.2rem 0" }}>
        {check.result === "warning" ? "⚠" : "✗"} {check.name ?? check.type ?? "check"}
        {check.model ? ` (${[check.model, check.field].filter(Boolean).join(".")})` : ""}
        {check.reason ? `: ${check.reason}` : ""}
      </li>
    ))}
  </ul>
);

const RowView: FC<{ row: Row }> = ({ row }) => {
  const [expanded, setExpanded] = useState(false);
  const result = row.result ?? {};
  const failing = (result.checks ?? []).filter((c) => c.result && c.result !== "passed");
  const total = result.checks_total;
  const passedCount = total != null && result.checks_failed != null ? total - result.checks_failed : undefined;
  return (
    <>
      <tr>
        <td style={cell}>{(row.timestamp ?? "").replace("T", " ").slice(0, 19)}</td>
        <td style={cell}>
          {row.dag_id} / {row.task_id}
          <div style={{ fontSize: "0.8rem", opacity: 0.65 }}>{row.run_id}</div>
        </td>
        <td style={cell}>
          {result.data_contract_file ?? ""}
          {result.server ? <div style={{ fontSize: "0.8rem", opacity: 0.65 }}>server: {result.server}</div> : null}
        </td>
        <td style={cell}>
          <Badge result={result.result} />
        </td>
        <td style={cell}>
          {total != null ? `${passedCount}/${total} passed` : ""}
          {failing.length > 0 ? (
            <div>
              <button
                onClick={() => setExpanded((value) => !value)}
                style={{
                  background: "none",
                  border: "none",
                  color: "inherit",
                  cursor: "pointer",
                  opacity: 0.75,
                  padding: 0,
                  textDecoration: "underline",
                }}
                type="button"
              >
                {expanded ? "hide details" : `${failing.length} not passed`}
              </button>
              {expanded ? <CheckList checks={failing} /> : null}
            </div>
          ) : null}
        </td>
      </tr>
    </>
  );
};

const DataContractResults: FC = () => {
  const [rows, setRows] = useState<Row[] | undefined>(undefined);
  const [error, setError] = useState<string | undefined>(undefined);
  const [refreshedAt, setRefreshedAt] = useState<Date | undefined>(undefined);

  const load = useCallback(() => {
    fetch("/datacontract/api/results?limit=100")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((data: Row[]) => {
        setRows(data);
        setError(undefined);
        setRefreshedAt(new Date());
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, [load]);

  return (
    <div style={{ fontSize: "0.95rem", margin: "1.5rem", maxWidth: "72rem" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 600, marginBottom: "0.3rem" }}>Data Contract Test Results</h1>
      <p style={{ marginBottom: "1rem", opacity: 0.7 }}>
        Most recent <code>datacontract test</code> runs, collected from XCom.
        {refreshedAt ? ` Refreshed ${refreshedAt.toLocaleTimeString()}.` : ""}{" "}
        <button
          onClick={load}
          style={{
            background: "none",
            border: "none",
            color: "inherit",
            cursor: "pointer",
            padding: 0,
            textDecoration: "underline",
          }}
          type="button"
        >
          Refresh
        </button>
      </p>
      {error ? <p style={{ color: palette.failed }}>Failed to load results: {error}</p> : null}
      {rows === undefined && !error ? <p style={{ opacity: 0.7 }}>Loading…</p> : null}
      {rows !== undefined && rows.length === 0 ? (
        <p style={{ opacity: 0.7 }}>No results yet. Run a DataContractTestOperator task first.</p>
      ) : null}
      {rows !== undefined && rows.length > 0 ? (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={cell}>Time</th>
              <th style={cell}>Dag / Task</th>
              <th style={cell}>Contract</th>
              <th style={cell}>Result</th>
              <th style={cell}>Checks</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <RowView key={`${row.dag_id}-${row.run_id}-${index}`} row={row} />
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
};

export default DataContractResults;
