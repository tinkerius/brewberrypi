# ADR-0002: REST for Requests, Server-Sent Events for Push

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** Benedikt Hauptmann (product owner); proposal by Claude Code
- **Supersedes:** the "Web/real-time" row of [ADR-0001](0001-technology-stack.md) (plain WebSocket with a `{topic, payload}` envelope)

## Context

Spec 08 (`IF-001`, `Q-28`) separates two interaction styles: request/response for reads and commands, and push
for state changes. The first implementation (ADR-0001) carried both over one WebSocket, copying the legacy
CometD topics:

- Command replies had no link to their command. Two clicks could not be told apart, and a reply was lost when
  the connection dropped between command and reply, so the UI could not tell whether **Stop** happened.
- Every topic was broadcast every 500 ms, changed or not; a change could arrive up to 500 ms late.
- No tool outside the browser could read the state or send a command, for example the OS update service
  asking whether a brew is running before it restarts the app.
- Any web page in the brewer's browser could open the WebSocket and send commands (`Q-17`).

## Options considered

1. **Keep everything on WebSocket**, adding request ids, timeouts and error codes to the envelope — rebuilds
   what HTTP already provides; still unusable from `curl`.
2. **REST + WebSocket (push only)** — fixes the request side; the WebSocket would only ever send one way.
3. **REST + server-sent events (SSE)** — SSE is plain HTTP made for exactly this one-way push: the browser's
   `EventSource` reconnects by itself, works through proxies, and needs no extra protocol on the server.

## Decision

We choose **option 3**.

### REST: reads and commands

All under `/api`, JSON (UTF-8).

| Method and path | Spec | Success | Errors |
|---|---|---|---|
| `GET /api/hardware` | `IF-010` | 200 HardwareStatus | |
| `GET /api/process` | `IF-020` | 200 ProcessState | |
| `GET /api/recipes` | `IF-030` | 200 RecipeList | |
| `GET /api/recipes/{id}` | `IF-031` | 200 RecipeDetail | 404 |
| `GET /api/chart[?since=<epoch ms>]` | `IF-040`, `IF-044` | 200 ChartData | 422 bad `since` |
| `PUT /api/process` `{"recipe": id}` | `load` | 200 | 404 unknown recipe, 409, 422 |
| `DELETE /api/process` | `unload` | 200 | 409 |
| `POST /api/process/start` · `/pause` · `/resume` · `/stop` | | 200 | 404 unknown command, 409 |
| `POST /api/process/requests/{requestId}` `{"response": option}` | `respond`, `IF-054` | 200 | 409, 422 |
| `GET /healthz` | runtime contract §5 | 200 | |

- Outcomes of `IF-052`: accepted 200, invalid 422, not found 404, conflict 409, forbidden 403. A POST or PUT that
  is not `Content-Type: application/json` gets 415.
- Every command answers with a CommandReply body, also on errors, so the UI can always show its message
  (`UI-050`). `DELETE` answers 200 with a body rather than 204 for the same reason. Errors that are not a
  command's own reply (403, 404, 415, a bad `since`) have the body `{"success": false, "message": …}`.
- Commands are actions on the process state machine (`POST …/start`), not edits of a state field.

### SSE: push

`GET /api/events` answers `text/event-stream` with `Cache-Control: no-cache` and starts with `retry: 1000`.
Each event is `event: <name>` plus one `data:` line of JSON, with the events of `IF-070`. Events carry no id:
every reconnection gets a fresh snapshot (`IF-071`) instead of a resume from `Last-Event-ID`; the state is small.

### Same origin (`IF-061`)

A request to `/api/…` whose `Origin` header is not the server's own `Host` gets 403. Commands must be
`application/json`, which a browser sends cross-site only after a CORS preflight; the server answers no
preflight, so the browser never sends the command. Requests without `Origin` (curl, scripts) are allowed.

### Shutdown

uvicorn waits for open responses before the application's shutdown, which switches the outputs off, so an open
event stream would delay it until the graceful-shutdown timeout (2 s). The server's SIGTERM/SIGINT handler
therefore ends every event stream first (`IF-076`); the contract test checks the exit with a stream open.

## Consequences

- Positive: every command has its own reply and status; a failed command is visible as a network error. State
  changes reach all clients at once, and nothing is sent while nothing changes. The state and the commands can be
  used from `curl`, scripts and other services. Other web pages cannot send commands.
- Negative / risks: two mechanisms instead of one. Browsers allow only six HTTP/1.1 connections per host and
  port, and an open event stream holds one for good: with six tabs open, commands waited forever in the
  browser. Hidden tabs therefore close their stream and reopen it when shown (`UI-062`).
- Follow-ups: `tinkerius/brewberrypi-os` can ask `GET /api/process` before an update restarts the app.
