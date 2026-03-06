# Use Clive

Query Ethereum Hive test results from the terminal. Run this skill when you need to check client test failures, regressions, or test details.

## Install

```bash
curl -LsSf https://raw.githubusercontent.com/spencer-tb/clive/main/install.sh | sh
```

## Quick Reference

```bash
# What groups are available?
clive groups

# Client overview (versions, pass/fail counts)
clive summary bal-quick

# Fail summary with rates (per client, per simulator)
clive fails bal-quick
clive fails bal-quick --client=besu
clive fails bal-quick --simulator=consume-engine

# Pass summary with rates
clive passes bal-quick

# List individual failing tests
clive tests bal-quick --client=besu
clive tests bal-quick --client=reth --eip=7702 --limit=20

# List passing tests
clive tests bal-quick --status=pass --limit=10

# Full detail for a single test (fill/consume commands, error logs, client logs)
clive detail bal-quick <suite_file> <test_index>

# Compare latest two runs — find regressions and fixes
clive diff bal-quick

# Search tests by name
clive search bal-quick state_creation --status=fail
clive search bal-quick eip7702 --client=besu

# Raw JSON output (pipe to jq, parse programmatically)
clive fails bal-quick --json
```

## Workflows

### Investigate a client's failures

```bash
clive fails bal-quick --client=besu          # how many failures?
clive tests bal-quick --client=besu          # which tests?
clive detail bal-quick <suite_file> <index>  # error logs + commands
```

### Check for regressions after a new run

```bash
clive diff bal-quick                         # regressions vs fixes
```

### Find tests related to an EIP

```bash
clive tests bal-quick --eip=7702            # all failing tests for EIP-7702
clive search bal-quick eip7702 --status=fail # search by name substring
```

### Get fill/consume commands to reproduce locally

```bash
clive detail bal-quick <suite_file> <index>  # shows fill_command and consume_command
```

## Tips

- The `detail` command output includes the exact `fill` and `consume` commands to reproduce the test locally
- Use `--json` on any command for machine-readable output
- Group names match what's on [hive.ethpandaops.io](https://hive.ethpandaops.io) (e.g., `bal-quick`, `bal-full`)
- Supported clients: go-ethereum, reth, besu, nethermind, erigon, nimbus-el, ethrex
