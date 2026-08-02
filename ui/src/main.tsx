import { FC, useCallback, useEffect, useMemo, useState } from "react";

// Mirrors the datacontract-cli Run model (the test-results API shape) that
// DataContractTestOperator pushes to XCom. None-valued fields are omitted.
type Check = {
  id?: string;
  key?: string;
  category?: string;
  type?: string;
  name?: string;
  model?: string;
  field?: string;
  quality_id?: string;
  tags?: string[];
  engine?: string;
  language?: string;
  implementation?: string;
  result?: string;
  reason?: string;
  diagnostics?: Record<string, unknown>;
  failed_samples?: unknown[];
};

type LogEntry = {
  level?: string;
  message?: string;
  timestamp?: string;
};

type Run = {
  runId?: string;
  datacontractCliVersion?: string;
  dataContractId?: string;
  dataContractVersion?: string;
  dataProductId?: string;
  outputPortId?: string;
  server?: string;
  filters?: Record<string, string>;
  timestampStart?: string;
  timestampEnd?: string;
  result?: string;
  checks?: Check[];
  logs?: LogEntry[];
  // Legacy payload (provider < 0.5) field, rendered best-effort.
  data_contract_file?: string;
};

type Row = {
  dag_id: string;
  task_id: string;
  run_id?: string;
  timestamp?: string;
  result: Run;
};

const palette = {
  passed: "#2e7d32",
  failed: "#c62828",
  error: "#c62828",
  warning: "#ef6c00",
  info: "#1565c0",
  unknown: "#616161",
} as const;

const icons: Record<string, string> = {
  passed: "✓",
  warning: "⚠",
  failed: "✗",
  error: "✗",
  info: "i",
};

const badgeColor = (result?: string): string =>
  palette[(result ?? "unknown") as keyof typeof palette] ?? palette.unknown;

const Badge: FC<{ result?: string; count?: number }> = ({ result, count }) => (
  <span
    style={{
      background: badgeColor(result),
      borderRadius: "0.6rem",
      color: "#fff",
      fontSize: "0.8rem",
      padding: "0.1rem 0.6rem",
      whiteSpace: "nowrap",
    }}
  >
    {count != null ? `${count} ` : ""}
    {result ?? "unknown"}
  </span>
);

const cell: React.CSSProperties = {
  borderBottom: "1px solid rgba(128,128,128,0.3)",
  padding: "0.45rem 0.75rem",
  textAlign: "left",
  verticalAlign: "top",
};

const mutedStyle: React.CSSProperties = { fontSize: "0.8rem", opacity: 0.65 };

const linkButton: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "inherit",
  cursor: "pointer",
  opacity: 0.75,
  padding: 0,
  textDecoration: "underline",
};

const formatTime = (value?: string): string => (value ?? "").replace("T", " ").slice(0, 19);

const duration = (run: Run): string | undefined => {
  if (!run.timestampStart || !run.timestampEnd) return undefined;
  const seconds = (new Date(run.timestampEnd).getTime() - new Date(run.timestampStart).getTime()) / 1000;
  if (!Number.isFinite(seconds) || seconds < 0) return undefined;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}m ${whole % 60}s`;
};

const contractLabel = (run: Run): string => {
  if (run.dataContractId) {
    return run.dataContractVersion ? `${run.dataContractId} @ ${run.dataContractVersion}` : run.dataContractId;
  }
  return run.data_contract_file ?? "";
};

const resultCounts = (checks: Check[]): Map<string, number> => {
  const counts = new Map<string, number>();
  for (const check of checks) {
    const key = check.result ?? "unknown";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return counts;
};

const Json: FC<{ value: unknown }> = ({ value }) => (
  <pre
    style={{
      background: "rgba(128,128,128,0.12)",
      borderRadius: "0.3rem",
      fontSize: "0.8rem",
      margin: "0.3rem 0",
      maxHeight: "16rem",
      overflow: "auto",
      padding: "0.5rem",
      whiteSpace: "pre-wrap",
    }}
  >
    {JSON.stringify(value, null, 2)}
  </pre>
);

const CheckRow: FC<{ check: Check }> = ({ check }) => {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = check.diagnostics != null || (check.failed_samples?.length ?? 0) > 0;
  const location = [check.model, check.field].filter(Boolean).join(".");
  return (
    <>
      <tr>
        <td style={{ ...cell, whiteSpace: "nowrap" }}>
          <span style={{ color: badgeColor(check.result), fontWeight: 600 }}>
            {icons[check.result ?? ""] ?? "?"} {check.result ?? "unknown"}
          </span>
        </td>
        <td style={cell}>
          {check.name ?? check.type ?? "check"}
          {check.quality_id ? <div style={mutedStyle}>quality: {check.quality_id}</div> : null}
        </td>
        <td style={cell}>{location}</td>
        <td style={cell}>
          {check.category ?? ""}
          {check.type && check.type !== check.category ? <div style={mutedStyle}>{check.type}</div> : null}
        </td>
        <td style={cell}>
          {check.reason ?? ""}
          {hasDetails ? (
            <div>
              <button onClick={() => setExpanded((value) => !value)} style={linkButton} type="button">
                {expanded ? "hide diagnostics" : "diagnostics"}
              </button>
            </div>
          ) : null}
        </td>
      </tr>
      {expanded ? (
        <tr>
          <td colSpan={5} style={{ ...cell, borderBottom: "none" }}>
            {check.diagnostics != null ? <Json value={check.diagnostics} /> : null}
            {(check.failed_samples?.length ?? 0) > 0 ? (
              <>
                <div style={mutedStyle}>failed samples</div>
                <Json value={check.failed_samples} />
              </>
            ) : null}
          </td>
        </tr>
      ) : null}
    </>
  );
};

const MetaItem: FC<{ label: string; value?: string }> = ({ label, value }) =>
  value ? (
    <div>
      <div style={{ ...mutedStyle, letterSpacing: "0.04em", textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: "0.9rem" }}>{value}</div>
    </div>
  ) : null;

const LogsSection: FC<{ logs: LogEntry[] }> = ({ logs }) => {
  const [expanded, setExpanded] = useState(false);
  if (logs.length === 0) return null;
  const levelColor = (level?: string) =>
    level === "ERROR" ? palette.failed : level === "WARN" ? palette.warning : "inherit";
  return (
    <div style={{ marginTop: "1rem" }}>
      <button onClick={() => setExpanded((value) => !value)} style={linkButton} type="button">
        {expanded ? "hide run logs" : `run logs (${logs.length})`}
      </button>
      {expanded ? (
        <div
          style={{
            background: "rgba(128,128,128,0.12)",
            borderRadius: "0.3rem",
            fontFamily: "ui-monospace, monospace",
            fontSize: "0.8rem",
            marginTop: "0.4rem",
            maxHeight: "20rem",
            overflow: "auto",
            padding: "0.5rem",
          }}
        >
          {logs.map((log, index) => (
            <div key={index}>
              <span style={{ opacity: 0.6 }}>{formatTime(log.timestamp)}</span>{" "}
              <span style={{ color: levelColor(log.level), fontWeight: 600 }}>{log.level}</span> {log.message}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

const RunDetails: FC<{ run: Run }> = ({ run }) => {
  const checks = run.checks ?? [];
  const [resultFilter, setResultFilter] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");

  const counts = useMemo(() => resultCounts(checks), [checks]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return checks.filter((check) => {
      if (resultFilter && (check.result ?? "unknown") !== resultFilter) return false;
      if (!term) return true;
      return [check.name, check.type, check.model, check.field, check.reason, check.category]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term));
    });
  }, [checks, resultFilter, search]);

  const byModel = useMemo(() => {
    const groups = new Map<string, Check[]>();
    for (const check of filtered) {
      const key = check.model ?? "";
      const group = groups.get(key);
      if (group) group.push(check);
      else groups.set(key, [check]);
    }
    return groups;
  }, [filtered]);

  return (
    <div style={{ margin: "0.5rem 0 1rem", padding: "0.5rem 0.75rem" }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1.5rem", marginBottom: "0.8rem" }}>
        <MetaItem label="Contract" value={contractLabel(run)} />
        <MetaItem label="Server" value={run.server} />
        <MetaItem label="Started" value={formatTime(run.timestampStart)} />
        <MetaItem label="Duration" value={duration(run)} />
        <MetaItem label="Data product" value={run.dataProductId} />
        <MetaItem label="Output port" value={run.outputPortId} />
        <MetaItem label="CLI" value={run.datacontractCliVersion} />
        <MetaItem label="Run ID" value={run.runId} />
      </div>
      {run.filters ? (
        <div style={{ ...mutedStyle, marginBottom: "0.8rem" }}>
          filters:{" "}
          {Object.entries(run.filters)
            .map(([schema, predicate]) => `${schema}: ${predicate}`)
            .join(" · ")}
        </div>
      ) : null}
      {checks.length > 0 ? (
        <>
          <div
            style={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.7rem" }}
          >
            <button
              onClick={() => setResultFilter(undefined)}
              style={{ ...linkButton, fontWeight: resultFilter === undefined ? 700 : 400, opacity: 1 }}
              type="button"
            >
              all ({checks.length})
            </button>
            {[...counts.entries()].map(([result, count]) => (
              <button
                key={result}
                onClick={() => setResultFilter((current) => (current === result ? undefined : result))}
                style={{
                  background: "none",
                  border: "none",
                  borderRadius: "0.7rem",
                  cursor: "pointer",
                  opacity: resultFilter && resultFilter !== result ? 0.45 : 1,
                  outline: resultFilter === result ? "2px solid rgba(128,128,128,0.6)" : "none",
                  padding: 0,
                }}
                type="button"
              >
                <Badge count={count} result={result} />
              </button>
            ))}
            <input
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Filter checks…"
              style={{
                background: "transparent",
                border: "1px solid rgba(128,128,128,0.4)",
                borderRadius: "0.3rem",
                color: "inherit",
                marginLeft: "auto",
                padding: "0.25rem 0.5rem",
              }}
              value={search}
            />
          </div>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={cell}>Result</th>
                <th style={cell}>Check</th>
                <th style={cell}>Field</th>
                <th style={cell}>Category</th>
                <th style={cell}>Reason</th>
              </tr>
            </thead>
            {[...byModel.entries()].map(([model, group]) => (
              <tbody key={model || "(contract)"}>
                {model ? (
                  <tr>
                    <td colSpan={5} style={{ ...cell, fontWeight: 600, paddingTop: "0.8rem" }}>
                      {model} <span style={mutedStyle}>({group.length})</span>
                    </td>
                  </tr>
                ) : null}
                {group.map((check, index) => (
                  <CheckRow check={check} key={`${model}-${index}`} />
                ))}
              </tbody>
            ))}
          </table>
          {filtered.length === 0 ? <p style={{ opacity: 0.7 }}>No checks match the current filter.</p> : null}
        </>
      ) : (
        <p style={{ opacity: 0.7 }}>No checks in this run.</p>
      )}
      <LogsSection logs={run.logs ?? []} />
    </div>
  );
};

const RowView: FC<{ row: Row }> = ({ row }) => {
  const [expanded, setExpanded] = useState(false);
  const run = row.result ?? {};
  const checks = run.checks ?? [];
  const counts = resultCounts(checks);
  const failing = (counts.get("failed") ?? 0) + (counts.get("error") ?? 0);
  const warnings = counts.get("warning") ?? 0;
  return (
    <>
      <tr onClick={() => setExpanded((value) => !value)} style={{ cursor: "pointer" }}>
        <td style={cell}>{formatTime(row.timestamp)}</td>
        <td style={cell}>
          {row.dag_id} / {row.task_id}
          <div style={mutedStyle}>{row.run_id}</div>
        </td>
        <td style={cell}>
          {contractLabel(run)}
          {run.server ? <div style={mutedStyle}>server: {run.server}</div> : null}
        </td>
        <td style={cell}>
          <Badge result={run.result} />
        </td>
        <td style={cell}>
          {checks.length > 0
            ? `${counts.get("passed") ?? 0}/${checks.length} passed` +
              (failing ? `, ${failing} failed` : "") +
              (warnings ? `, ${warnings} warnings` : "")
            : ""}
          <div>
            <span style={{ ...linkButton, cursor: "pointer" }}>{expanded ? "hide details" : "details"}</span>
          </div>
        </td>
      </tr>
      {expanded ? (
        <tr>
          <td colSpan={5} style={{ borderBottom: "1px solid rgba(128,128,128,0.3)", padding: 0 }}>
            <RunDetails run={run} />
          </td>
        </tr>
      ) : null}
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
    <div style={{ fontSize: "0.95rem", margin: "1.5rem", maxWidth: "80rem" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 600, marginBottom: "0.3rem" }}>Data Contract Test Results</h1>
      <p style={{ marginBottom: "1rem", opacity: 0.7 }}>
        Most recent <code>datacontract test</code> runs, collected from XCom.
        {refreshedAt ? ` Refreshed ${refreshedAt.toLocaleTimeString()}.` : ""}{" "}
        <button onClick={load} style={linkButton} type="button">
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
