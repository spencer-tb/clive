# clive

[![Go](https://img.shields.io/badge/Go-00ADD8?logo=go&logoColor=white)](https://go.dev)
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://python.org)
[![GitHub Release](https://img.shields.io/github/v/release/spencer-tb/clive?label=Release)](https://github.com/spencer-tb/clive/releases)
[![License](https://img.shields.io/github/license/spencer-tb/clive)](LICENSE)

<p align="center">
  <img src="https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Ftse3.mm.bing.net%2Fth%2Fid%2FOIP.ApM2UlQ5yQwsrEUq3yIPyQHaEK%3Fpid%3DApi&f=1&ipt=8e73a41bb3da646aaa1726c9851f177cdbbe92662c3e0e1c3ce25cce1efc2d68&ipo=images" width="400"/>
  <br/>
  <em>Meet <b><a href="https://www.youtube.com/watch?v=C1UB1-LKX5E&pp=ygUWc2h1dCB1cCBjbGl2ZSBvcmlnaW5hbA%3D%3D">clive</a></b>, queries your test results and is <b>hapi</b> to do it.</em>
</p>

A **h**ive **api** (**hapi**) and **cli** for hi**ve** (**clive**) — query Ethereum [Hive](https://github.com/ethereum/hive) test results. Built for AI agents and developers — structured JSON API, text tables, search, and one-command install. Provides programmatic access to test data hosted at [hive.ethpandaops.io](https://hive.ethpandaops.io), with a focus on [EELS](https://github.com/ethereum/execution-specs) `consume-engine` and `consume-rlp` simulator results.

## Install clive

```bash
curl -LsSf https://raw.githubusercontent.com/spencer-tb/clive/main/install.sh | sh
```

That's it. Now just:

```bash
clive fails bal-quick
```

Other install methods:

```bash
# Build from source (requires Go)
go install github.com/spencer-tb/clive/cmd/hive-cli@latest
mv $(go env GOPATH)/bin/hive-cli $(go env GOPATH)/bin/clive

# From a local clone
make build

# Python wrapper (requires uv/pip, useful for EELS dev)
uv tool install git+https://github.com/spencer-tb/clive
# or: pip install git+https://github.com/spencer-tb/clive
```

## Components

| Component | Language | Description |
|-----------|----------|-------------|
| **hapi** | Go | REST API server — fetches, caches, and serves hive test results |
| **clive** | Go | CLI tool — queries the API, outputs text tables or JSON |

## Server

```bash
# Build and run
go build -o hapi .
./hapi --groups bal-quick

# Or with auto-discovery of all groups
./hapi

# Flags
./hapi --addr :9090 --base-url https://hive.ethpandaops.io --refresh 5m
```

## CLI Usage

Filter by `--client` and `--simulator` on any command to drill into your team's results.

```bash
# What's available?
clive groups

# Overview for all clients
clive summary bal-quick

# Your client's failures
clive fails bal-quick --client=besu
clive tests bal-quick --client=besu

# Filter by simulator too
clive fails bal-quick --client=reth --simulator=consume-engine
clive tests bal-quick --client=reth --simulator=consume-engine

# All clients at a glance
clive fails bal-quick
clive passes bal-quick

# Full detail for a single test (error logs, client logs, reproduce commands)
clive detail bal-quick --filter="test_name_regex" --client=reth

# Or by suite file and test index (shown in `tests` and `search` output)
clive detail bal-quick <suite_file> <test_index>

# Get full client logs (default is last 30 lines)
clive detail bal-quick --filter="test_name" --full-log

# Compare latest two runs — find regressions
clive diff bal-quick

# Search by test name or EIP
clive search bal-quick eip7702 --client=besu --status=fail
clive tests bal-quick --client=nethermind --filter="eip7702"

# Raw JSON output (for scripting / AI agents)
clive fails bal-quick --json

# Point at a different server
clive --api=http://localhost:9090 fails bal-quick
# Or via env var
export HIVE_API_URL=http://localhost:9090
```

## Agent Usage

Clive is designed for AI agent workflows. Use `--json` on any command for structured output.

**Key flags for agents:**
- `--json` — always use this; returns structured data instead of text tables
- `--client=X` — scope to a single client (reth, besu, go-ethereum, etc.)
- `--simulator=Y` — scope to a simulator (consume-engine, consume-rlp)
- `--filter=REGEX` — case-insensitive regex on test names
- `--status=fail|pass` — filter test lists by status (default: fail)
- `--limit=N` — cap the number of results
- `--full-log` — return complete client log instead of last 30 lines

### Step 1: Which clients are failing?

```bash
clive fails bal-quick --json
```

```json
{
  "group": "bal-quick",
  "total_fails": 42,
  "fail_rate": 1.2,
  "clients": {
    "reth": {
      "version": "v1.11.0+b00debcc",
      "repo": "paradigmxyz/reth",
      "branch": "main",
      "commit": "b00debcc",
      "total_fails": 5,
      "fail_rate": 0.3,
      "simulators": {
        "consume-engine": {
          "run_date": "2026-03-06T10:00:00Z",
          "suite_file": "suite-001.json",
          "fixtures_release": "https://github.com/ethereum/fixtures/releases/download/v1.0",
          "total_fails": 5,
          "fail_rate": 0.3,
          "total_tests": 1580
        }
      }
    },
    "besu": {
      "version": "v26.3-develop-f9b20c2",
      "repo": "hyperledger/besu",
      "branch": "main",
      "commit": "f9b20c2",
      "total_fails": 37,
      "fail_rate": 2.3,
      "simulators": {
        "consume-engine": {
          "run_date": "2026-03-06T10:00:00Z",
          "suite_file": "suite-002.json",
          "fixtures_release": "https://github.com/ethereum/fixtures/releases/download/v1.0",
          "total_fails": 37,
          "fail_rate": 2.3,
          "total_tests": 1580
        }
      }
    }
  }
}
```

### Step 2: List failing tests for a client

```bash
clive tests bal-quick --client=reth --json
```

```json
{
  "group": "bal-quick",
  "total": 5,
  "tests": [
    {
      "client": "reth",
      "simulator": "consume-engine",
      "eels_test_module": "tests/osaka/eip7928_eip7929/test_block_access_lists.py",
      "eels_test_function": "test_bal_gas_limit",
      "pytest_id": "tests/osaka/eip7928_eip7929/test_block_access_lists.py::test_bal_gas_limit[fork_Osaka-blockchain_test_engine-below_boundary]",
      "fork": "Osaka",
      "pass": false,
      "hive_suite_test_index": "42",
      "suite_file": "suite-001.json",
      "eels_test_url": "https://github.com/ethereum/execution-spec-tests/blob/main/tests/osaka/eip7928_eip7929/test_block_access_lists.py"
    }
  ]
}
```

### Step 3: Get full detail for a failure

Use either `--filter` (regex match) or suite file + test index from step 2:

```bash
clive detail bal-quick --filter="test_bal_gas_limit" --client=reth --json
# or: clive detail bal-quick suite-001.json 42 --json
```

```json
{
  "eels_test_module": "tests/osaka/eip7928_eip7929/test_block_access_lists.py",
  "eels_test_function": "test_bal_gas_limit",
  "pytest_id": "tests/osaka/eip7928_eip7929/test_block_access_lists.py::test_bal_gas_limit[fork_Osaka-blockchain_test_engine-below_boundary]",
  "fork": "Osaka",
  "hive_suite_test_index": "42",
  "eels_test_url": "https://github.com/ethereum/execution-spec-tests/blob/main/tests/osaka/eip7928_eip7929/test_block_access_lists.py",
  "client": "reth",
  "pass": false,
  "fill_command": "uv run fill tests/osaka/eip7928_eip7929/test_block_access_lists.py::test_bal_gas_limit[fork_Osaka-blockchain_test_engine-below_boundary]",
  "hive_command": "./hive --sim eels/consume-engine --client reth --sim.limit test_bal_gas_limit",
  "consume_command": "uv run consume engine --input=fixtures -k test_bal_gas_limit",
  "error_log": "AssertionError: wrong gas_used in block 1: expected 42000, got 21000",
  "detail_log": "starting test runner\nexecuting test...\nblock validation failed",
  "client_log": "INFO [03-06|10:00:00] Starting Reth v1.11.0\n...(last 30 lines)..."
}
```

Use the returned commands to reproduce locally:
- **`fill_command`** — regenerate the test fixture with EELS
- **`consume_command`** — re-run the test against a client
- **`hive_command`** — reproduce via hive directly
- **`error_log`** — the assertion/error output
- **`client_log`** — EL client stderr (last 30 lines; use `--full-log` for all)

### Step 4: Check for regressions

```bash
clive diff bal-quick --json
```

```json
{
  "group": "bal-quick",
  "from_run": "2026-03-05T10:00:00Z",
  "to_run": "2026-03-06T10:00:00Z",
  "regressions": {
    "reth": {
      "total_fails": 2,
      "simulators": {
        "consume-engine": {
          "total_fails": 2,
          "tests": [
            {
              "eels_test_module": "tests/osaka/eip7928_eip7929/test_block_access_lists.py",
              "eels_test_function": "test_bal_gas_limit",
              "pytest_id": "tests/osaka/eip7928_eip7929/test_block_access_lists.py::test_bal_gas_limit[fork_Osaka-blockchain_test_engine-below_boundary]",
              "fork": "Osaka"
            }
          ]
        }
      }
    }
  },
  "fixes": {},
  "unchanged_fails": {}
}
```

### Step 5: Search by keyword

```bash
clive search bal-quick "access_list" --status=fail --json
```

```json
{
  "group": "bal-quick",
  "query": "access_list",
  "total": 3,
  "results": [
    {
      "client": "reth",
      "simulator": "consume-engine",
      "eels_test_module": "tests/osaka/eip7928_eip7929/test_block_access_lists.py",
      "eels_test_function": "test_bal_gas_limit",
      "pytest_id": "tests/osaka/eip7928_eip7929/test_block_access_lists.py::test_bal_gas_limit[fork_Osaka-blockchain_test_engine-below_boundary]",
      "fork": "Osaka",
      "pass": false,
      "hive_suite_test_index": "42",
      "suite_file": "suite-001.json",
      "eels_test_url": "https://github.com/ethereum/execution-spec-tests/blob/main/tests/osaka/eip7928_eip7929/test_block_access_lists.py"
    }
  ]
}
```

## Example: Investigate Your Client

```bash
# 1. How is besu doing?
clive fails bal-quick --client=besu
clive passes bal-quick --client=besu

# 2. List the failing tests
clive tests bal-quick --client=besu

# 3. Get full detail for a specific failure
clive detail bal-quick --filter="test_bal_invalid_account" --client=besu

# Detail output includes:
#   - Error log (hive/EELS output)
#   - Client log (EL client output, last 30 lines)
#   - Fill command (reproduce the test fixture locally)
#   - Consume command (re-run against your client)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1` | Index — lists all endpoints |
| GET | `/api/v1/groups` | List available test result groups |
| GET | `/api/v1/groups/{group}/summary` | Pass/fail counts per client and simulator |
| GET | `/api/v1/groups/{group}/fails` | Fail summary with rates. `?client=`, `?simulator=` |
| GET | `/api/v1/groups/{group}/passes` | Pass summary with rates. `?client=`, `?simulator=` |
| GET | `/api/v1/groups/{group}/tests` | List tests. `?status=fail\|pass`, `?client=`, `?simulator=`, `?filter=`, `?limit=`, `?offset=` |
| GET | `/api/v1/groups/{group}/tests/lookup` | Find first test matching filter. `?filter=` (required), `?client=`, `?simulator=`, `?full_log=true` |
| GET | `/api/v1/groups/{group}/tests/{file}/{testID}` | Full test detail: commands, logs. `?full_log=true` |
| GET | `/api/v1/groups/{group}/suites` | List latest suite runs |
| GET | `/api/v1/groups/{group}/suites/{file}` | Full suite detail. `?status=fail` |
| GET | `/api/v1/groups/{group}/diff` | Regressions/fixes between two most recent run batches |
| GET | `/api/v1/groups/{group}/search` | Search tests by name. `?q=` (required), `?client=`, `?simulator=`, `?status=`, `?limit=` |

## Architecture

```
hive.ethpandaops.io (S3)
  ├── discovery.json          # available groups
  ├── {group}/
  │   ├── listing.jsonl       # one line per suite run
  │   └── results/
  │       ├── *.json          # suite detail files
  │       └── details/        # test detail logs (byte-range fetched)
  │
  └── hapi (this server)
      ├── fetches listing.jsonl per group on startup + periodic refresh
      ├── finds latest run per (client, simulator) pair
      ├── pre-fetches detail files for runs with failures
      ├── caches everything in memory
      └── serves structured JSON API
```

The server has zero external dependencies — pure Go stdlib. It auto-discovers groups from `discovery.json` and refreshes on a configurable interval (default 5 minutes).

## Docker

```bash
docker build -t hapi .
docker run -p 8080:8080 hapi
```

## Data Source

Test results come from [ethpandaops/bal-devnets](https://github.com/ethpandaops/bal-devnets) CI workflows that run hive tests against Ethereum execution clients. Results are uploaded to S3 and served at `hive.ethpandaops.io`.

Supported clients: go-ethereum, reth, besu, nethermind, erigon, nimbus-el, ethrex.
