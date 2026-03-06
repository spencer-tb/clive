# CLAUDE.md

Go project for the Hive test results API and CLI.

## Project Structure

- `main.go` — Server entry point (flags, CORS, health check)
- `handlers.go` — All HTTP handlers and route registration
- `store.go` — Data fetching, caching, refresh loop
- `parser.go` — Version parsing, test name splitting, HTML extraction
- `types.go` — All Go types (hive data + API responses)
- `cmd/hive-cli/main.go` — Go CLI (`clive`, wraps the API)
- `install.sh` — curl installer for clive binary
- `.github/workflows/release.yml` — Cross-compile and publish releases
- `Dockerfile` — Multi-stage Go build

## Building

```bash
# Both binaries (hapi + clive)
make build

# Individual
go build -o hapi .
go build -o clive ./cmd/hive-cli/

# Cross-compile release binaries
make release   # outputs to dist/
```

## Running the Server

```bash
./hapi --groups bal-quick          # specific group
./hapi                             # auto-discover all groups
./hapi --addr :9090 --refresh 1m   # custom port and refresh
```

Server must be running for CLIs to work. Default: `http://localhost:8080`. Override with `HIVE_API_URL` env var or `--api=` flag.

## Key Design Decisions

- **Zero dependencies** — Go server and CLI use only stdlib.
- **Read-through cache** — Store fetches and caches listing + detail files. Refreshes periodically.
- **Auto-discovery** — Groups discovered from `discovery.json` at the base URL.
- **Latest runs** — Only the most recent run per (client, simulator) pair is served.
- **Lean summaries + unified test list** — `/fails` and `/passes` return rates/counts only. `/tests?status=fail|pass` returns the actual test entries.
- **Client log tail** — Detail endpoint returns last 30 lines of client log by default. `?full_log=true` for everything.

## Adding a New Endpoint

1. Add response type(s) to `types.go`
2. Add handler method to `handlers.go`
3. Register route in `RegisterRoutes()` in `handlers.go`
4. Update the `handleIndex` static endpoint list
5. Add corresponding command to the CLI (`cmd/hive-cli/main.go`)

## Client Version Parsing

Each Ethereum client has a different version string format. Parsing logic in `parser.go`:
- `commitPatterns` — per-client regex to extract commit hash
- `versionPatterns` — per-client regex to extract clean version string
- `NormalizeClientName()` — strips `_nametag` suffix (e.g., `reth_default` → `reth`)

To add a new client, add entries to both maps.

## Test Name Anatomy

Hive test names follow this pattern:
```
module::function[fork_Fork-test_type-params]-client_nametag
```

Example:
```
tests/amsterdam/eip7928_.../test_block_access_lists.py::test_bal_gas_limit[fork_Amsterdam-blockchain_test_engine-below_boundary]-besu_default
```

Key parsers:
- `SplitTestName()` — splits at `::`, strips `[...]` from function name
- `ExtractPytestID()` — strips client suffix after last `]`
- `ExtractFork()` — extracts fork name from `[fork_X-...]`
- `ExtractSourceURL()` — extracts `[source]` href from description HTML

## Naming

- **hapi** — the Go API server binary
- **clive** — the Python CLI package and Go CLI alias
- **hive-cli** — original Go CLI name
