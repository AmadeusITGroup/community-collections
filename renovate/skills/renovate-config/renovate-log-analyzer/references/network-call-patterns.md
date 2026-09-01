# Renovate Network Call Patterns

Network-call analysis requires a Renovate run with `LOG_LEVEL=debug`. Treat URLs and headers as sensitive: redact tokens, cookies, and signed query parameters in reports.

## Request Signals

Search for request and response entries around these signals:

- `http` or `http-stats`
- `GET`, `POST`, `HEAD`, and `PUT`
- `datasource`, `registry`, `lookup`, and `host`
- response status codes such as `200`, `301`, `401`, `403`, `404`, `429`, and `5xx`
- `retry`, `timeout`, `ECONNRESET`, `ENOTFOUND`, and `ETIMEDOUT`

## Analysis Procedure

1. Extract the request method, host, path, datasource or manager, status, duration, and retry count.
2. Group calls by host and datasource.
3. Tally successful responses, non-2xx responses, retries, and timeouts.
4. Correlate failed hosts with `Package lookup failures`, `WARN:`, and `ERROR:` log entries.
5. Separate platform API calls, package-registry calls, source-control metadata calls, and artifact downloads.

## Status Interpretation

| Status or signal     | Likely meaning                                                    | Recommended next check                          |
| -------------------- | ----------------------------------------------------------------- | ----------------------------------------------- |
| `401` or `403`       | Missing or insufficient credentials                               | Token scope and Renovate host rules             |
| `404`                | Missing package, unsupported endpoint, or hidden private resource | Package coordinate and registry URL             |
| `429`                | Rate limited                                                      | Retry behavior, request volume, and host limits |
| `5xx`                | Remote service failure                                            | Retry outcome and provider status               |
| Timeout or DNS error | Network, proxy, or host availability issue                        | Host reachability and configured proxy          |

## Reporting Rules

- Report aggregate counts and representative sanitized endpoints instead of every request line.
- Mark a network issue as causal only when its timing and package or datasource match a failed lookup.
- Distinguish Renovate configuration errors from external registry and platform failures.
