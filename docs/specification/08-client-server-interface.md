# 08 — Client/Server Interface

## 8.1 Communication model

- `IF-001` Browser and server communicate over a **bidirectional, real-time, message-based** channel using **named topics** (publish/subscribe) with JSON payloads.
  - Server → clients: periodic **broadcasts** to all connected clients.
  - Client → server: **commands**; each command gets a **reply** to the sending client only.
- `IF-002` The transport is a phase-2 technology decision. Requirements: works in current browsers without plugins; automatic reconnect after network loss or server restart; works over plain HTTP in a LAN; one server port (default **8080**, config `server.port`) serves both the web UI and the real-time channel.
  (Legacy: CometD/Bayeux long-polling at `/cometd`, WebSocket disabled on the client.)
- `IF-003` Topic names below are **logical names**, kept from the legacy system for traceability. The concrete addressing may differ.
- `IF-004` All payloads are validated against [data/messages.schema.json](data/messages.schema.json).
- `IF-005` A newly connected client MUST receive the current value of every broadcast topic within **1 s**.

## 8.2 Broadcast topics (server → all clients)

| Topic | Period | Payload | Req |
|---|---|---|---|
| `/hardware/status` | 500 ms | `HardwareStatus` | `IF-010` |
| `/process/state` | 500 ms | `ProcessState` | `IF-020` |
| `/process/recipes` | 500 ms (MAY be reduced to on-connect + on-change) | `RecipeList` | `IF-030` |
| `/process/chart` | 1000 ms | `ChartData` | `IF-040` |

Periods are configurable (`broadcast.*Milliseconds`). A failure while building
one broadcast is logged and MUST NOT stop the broadcast loop (legacy behaviour).

### `IF-010` HardwareStatus

```json
{ "temperature": 62.5, "pumpstatus": true, "heatingstatus": 0.5 }
```

| Field | Type | Meaning |
|---|---|---|
| `temperature` | number (1 decimal) or `null` | Current kettle temperature; `null` if INVALID `[FIX-02, FIX-16]` |
| `pumpstatus` | boolean | Pump on |
| `heatingstatus` | number 0…1 | Requested heating power |

Legacy: `temperature` was a **string** formatted with the server locale (`"62,5"` on a German system) and showed the error sentinel as a huge negative number. `[FIX-16]`

### `IF-020` ProcessState

No process loaded `[FIX-18]` (legacy sent the string `"null"`):

```json
{ "state": "NoProcess" }
```

Process loaded:

```json
{
  "processid": "ZORA",
  "processname": "München 12.6 - SUD1:ZORA",
  "state": "Running",
  "goals": [
    { "name": "Add Water", "description": "Pour in the brewing water.",
      "status": "Done", "statuspercent": 100, "statusmessage": "100%" },
    { "name": "Heat Up", "description": "Heat up mash to 40.0 degrees (C).",
      "status": "Active", "statuspercent": 37, "statusmessage": "37%" },
    { "name": "Mash In", "description": "Now it's your job to mash in the malt.",
      "status": "Waiting", "statuspercent": 0, "statusmessage": "0%" }
  ]
}
```

A goal with an active request additionally contains:

```json
"activeRequest": { "message": "Iodine test successfull?", "options": ["Yes", "No"] }
```

- `state` is `[NEW, FIX-20]`; all other field names are legacy.
- `activeRequest` is **omitted** when there is no request (legacy behaviour).
- Snapshot consistency: a published ProcessState MUST reflect one consistent point in time (`ENG-040`).

### `IF-030` RecipeList

```json
[ { "id": "ZORA", "name": "München 12.6 - SUD1:ZORA" }, { "id": "HANCOCK", "name": "München 12.6 - SUD3:HANCOCK" } ]
```

Order = catalogue order (`DOM-002`).

### `IF-040` ChartData

```json
[ { "key": "Kettle Temperature", "values": [ { "x": 1718197200000, "y": 62.5 } ] } ]
```

- `IF-041` The server samples the temperature every chart period (1 s) and appends `{x: epoch milliseconds, y: °C}` **if the reading is valid** (legacy: if `> 0`). `[FIX-17]`
- `IF-042` History covers the time since **server start** and is shared by all clients; it is **not** reset when a process is loaded (legacy; see `Q-08`).
- `IF-043` **Thinning**: after appending, while the number of points exceeds **200** (`chart.maxPoints`):
  find the adjacent pair `(i, i+1)` with the **smallest time gap** `x[i+1] − x[i]` (first such pair on ties) and **remove point `i+1`**. The first point is never removed. This keeps the full time range with decreasing resolution for older data.
- `IF-044` The whole series is sent every period (legacy). A phase-2 implementation MAY send deltas if the UI result is identical.

## 8.3 Commands (client → server)

| Command topic | Payload | Engine command |
|---|---|---|
| `/service/process/load` | `{ "recipe": "<recipeId>" }` | `load` (`ENG-010`) |
| `/service/process/unload` | `{}` | `unload` (`ENG-011`) |
| `/service/process/start` | `{}` | `start` (`ENG-012`) |
| `/service/process/pause` | `{}` | `pause` (`ENG-013`) |
| `/service/process/stop` | `{}` | `stop` (`ENG-014`) |
| `/service/process/request` | `{ "response": "<option>" }` | `respond` (`ENG-015`) |

### `IF-050` CommandReply `[FIX-15]`

Sent only to the issuing client:

```json
{ "command": "load", "success": true, "message": "Process München 12.6 - SUD1:ZORA (ZORA) loaded." }
```

- Legacy only answered `load` (on a topic the UI did not listen to), and the UI listened for replies of unload/start/pause/stop that were never sent — so no feedback was ever shown.
- `IF-051` Malformed payloads (missing/invalid fields) → `success=false` with an explanatory message; never a server-side crash.

## 8.4 Security

- `IF-060` No authentication/authorisation (legacy). Intended for a trusted LAN only. See `Q-10`.
