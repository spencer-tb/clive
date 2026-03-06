"""clive — CLI for Ethereum Hive test results."""
from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

API_URL = os.environ.get("HIVE_API_URL", "http://localhost:8080").rstrip("/")


def api_get(path: str, params: dict | None = None) -> dict:
    url = f"{API_URL}{path}"
    if params:
        params = {k: v for k, v in params.items() if v is not None}
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params)
    if resp.status_code != 200:
        print(f"error: API {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2))


def rate(r: float) -> str:
    return f"{r:.1f}%"


def print_table(headers: tuple, rows: list[tuple]) -> None:
    all_rows = [headers] + rows
    widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(headers))]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for row in rows:
        print(fmt.format(*row))


# --- commands ---


def cmd_groups(args: argparse.Namespace) -> None:
    data = api_get("/api/v1/groups")
    if args.json:
        return print_json(data)
    print("Available groups:")
    for g in data["groups"]:
        print(f"  {g}")


def cmd_summary(args: argparse.Namespace) -> None:
    data = api_get(f"/api/v1/groups/{args.group}/summary")
    if args.json:
        return print_json(data)

    print(f"{args.group.upper()} SUMMARY")
    print(f"Last run: {data['last_run']}\n")

    rows = []
    for name, c in sorted(data["clients"].items()):
        total = c["pass"] + c["fail"]
        r = rate(c["pass"] / total * 100) if total else "-"
        rows.append((name, c["version"], c["pass"], c["fail"], c.get("timeout", 0), r, c.get("repo", ""), c.get("branch", "")))
    print_table(("CLIENT", "VERSION", "PASS", "FAIL", "TIMEOUT", "RATE", "REPO", "BRANCH"), rows)

    print()
    sim_rows = [(s, d["pass"], d["fail"], d["total"]) for s, d in data["simulators"].items()]
    print_table(("SIMULATOR", "PASS", "FAIL", "TOTAL"), sim_rows)


def cmd_fails(args: argparse.Namespace) -> None:
    params = {"client": args.client, "simulator": args.simulator}
    data = api_get(f"/api/v1/groups/{args.group}/fails", params)
    if args.json:
        return print_json(data)

    print(f"{args.group.upper()} FAILS — {data['total_fails']} total ({rate(data['fail_rate'])} fail rate)\n")

    rows = []
    for name, c in data["clients"].items():
        total = sum(s["total_tests"] for s in c["simulators"].values())
        rows.append((name, c["version"], c["total_fails"], total, rate(c["fail_rate"]), c.get("repo", ""), c.get("branch", "")))
    rows.sort(key=lambda r: float(str(r[4]).rstrip("%")))
    print_table(("CLIENT", "VERSION", "FAILS", "TOTAL", "FAIL RATE", "REPO", "BRANCH"), rows)


def cmd_passes(args: argparse.Namespace) -> None:
    params = {"client": args.client, "simulator": args.simulator}
    data = api_get(f"/api/v1/groups/{args.group}/passes", params)
    if args.json:
        return print_json(data)

    print(f"{args.group.upper()} PASSES — {data['total_passes']} total ({rate(data['pass_rate'])} pass rate)\n")

    rows = []
    for name, c in data["clients"].items():
        total = sum(s["total_tests"] for s in c["simulators"].values())
        rows.append((name, c["version"], c["total_passes"], total, rate(c["pass_rate"]), c.get("repo", ""), c.get("branch", "")))
    rows.sort(key=lambda r: -float(str(r[4]).rstrip("%")))
    print_table(("CLIENT", "VERSION", "PASSES", "TOTAL", "PASS RATE", "REPO", "BRANCH"), rows)


def cmd_tests(args: argparse.Namespace) -> None:
    status = args.status or "fail"
    endpoint = f"/api/v1/groups/{args.group}/{'passes' if status == 'pass' else 'fails'}/tests"
    params = {"client": args.client, "simulator": args.simulator, "filter": args.filter, "limit": args.limit}
    data = api_get(endpoint, params)
    if args.json:
        return print_json(data)

    label = "PASSING" if status == "pass" else "FAILING"
    tests = data["tests"]
    print(f"{args.group.upper()} {label} TESTS — {data['total']} total (showing {len(tests)})\n")

    for i, t in enumerate(tests, 1):
        print(f"{i}. {t['eels_test_function']}")
        print(f"   module:    {t['eels_test_module']}")
        print(f"   client:    {t['client']}")
        print(f"   simulator: {t['simulator']}")
        print(f"   fork:      {t['fork']}")
        print(f"   pytest_id: {t['pytest_id']}")
        if t.get("eels_test_url"):
            print(f"   source:    {t['eels_test_url']}")
        print()


def cmd_detail(args: argparse.Namespace) -> None:
    if not args.filter:
        print("error: --filter is required", file=sys.stderr)
        sys.exit(1)
    params = {"filter": args.filter, "client": args.client, "simulator": args.simulator}
    if args.full_log:
        params["full_log"] = "true"
    data = api_get(f"/api/v1/groups/{args.group}/detail", params)
    if args.json:
        return print_json(data)

    status = "PASS" if data["pass"] else "FAIL"
    print(f"TEST DETAIL [{status}]")
    print("=" * 40)
    print(f"\nFunction:  {data['eels_test_function']}")
    print(f"Module:    {data['eels_test_module']}")
    print(f"Client:    {data['client']}")
    print(f"Fork:      {data['fork']}")
    print(f"Pytest ID: {data['pytest_id']}")
    if data.get("eels_test_url"):
        print(f"Source:    {data['eels_test_url']}")

    print("\nCOMMANDS\n--------")
    print(f"Fill:    {data['fill_command']}")
    if data.get("consume_command"):
        print(f"Consume: {data['consume_command']}")
    if data.get("hive_command"):
        print(f"Hive:    {data['hive_command']}")

    if data.get("error_log"):
        print(f"\nERROR LOG\n---------\n{data['error_log']}")
    if data.get("detail_log"):
        print(f"\nDETAIL LOG\n----------\n{data['detail_log']}")
    if data.get("client_log"):
        print(f"\nCLIENT LOG (tail)\n-----------------\n{data['client_log']}")


def cmd_diff(args: argparse.Namespace) -> None:
    data = api_get(f"/api/v1/groups/{args.group}/diff")
    if args.json:
        return print_json(data)

    print(f"{args.group.upper()} DIFF")
    print(f"From: {data['from_run']}")
    print(f"To:   {data['to_run']}\n")

    for label, key in [
        ("REGRESSIONS (new failures)", "regressions"),
        ("FIXES (no longer failing)", "fixes"),
        ("UNCHANGED FAILS", "unchanged_fails"),
    ]:
        clients = data[key]
        total = sum(c["total_fails"] for c in clients.values())
        print(f"{label}: {total}")
        for name, c in clients.items():
            print(f"  {name}: {c['total_fails']}")
        print()


def cmd_search(args: argparse.Namespace) -> None:
    params = {"q": args.query, "client": args.client, "simulator": args.simulator, "status": args.status, "limit": args.limit}
    data = api_get(f"/api/v1/groups/{args.group}/search", params)
    if args.json:
        return print_json(data)

    results = data["results"]
    print(f'SEARCH: "{data["query"]}" — {data["total"]} results\n')

    for i, r in enumerate(results, 1):
        s = "PASS" if r["pass"] else "FAIL"
        print(f"{i}. [{s}] {r['eels_test_function']}")
        print(f"   client: {r['client']} | simulator: {r['simulator']} | fork: {r['fork']}")
        print(f"   module: {r['eels_test_module']}")
        print(f"   detail: clive detail {args.group} {r['suite_file']} {r['hive_suite_test_index']}")
        if r.get("eels_test_url"):
            print(f"   source: {r['eels_test_url']}")
        print()


# --- main ---


def main() -> None:
    global API_URL

    parser = argparse.ArgumentParser(prog="clive", description="CLI for Ethereum Hive test results")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--api", default=None, help="API base URL (default: $HIVE_API_URL or http://localhost:8080)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("groups", help="List available groups")

    p = sub.add_parser("summary", help="Client/simulator overview")
    p.add_argument("group")

    p = sub.add_parser("fails", help="Fail summary with rates")
    p.add_argument("group")
    p.add_argument("--client", default=None)
    p.add_argument("--simulator", default=None)

    p = sub.add_parser("passes", help="Pass summary with rates")
    p.add_argument("group")
    p.add_argument("--client", default=None)
    p.add_argument("--simulator", default=None)

    p = sub.add_parser("tests", help="List individual test cases")
    p.add_argument("group")
    p.add_argument("--client", default=None)
    p.add_argument("--simulator", default=None)
    p.add_argument("--status", default=None, choices=["fail", "pass"])
    p.add_argument("--filter", default=None)
    p.add_argument("--limit", default=None)

    p = sub.add_parser("detail", help="Full detail for a single test")
    p.add_argument("group")
    p.add_argument("--filter", default=None)
    p.add_argument("--client", default=None)
    p.add_argument("--simulator", default=None)
    p.add_argument("--full-log", action="store_true")

    p = sub.add_parser("diff", help="Compare latest two runs")
    p.add_argument("group")

    p = sub.add_parser("search", help="Search tests by name")
    p.add_argument("group")
    p.add_argument("query")
    p.add_argument("--client", default=None)
    p.add_argument("--simulator", default=None)
    p.add_argument("--status", default=None, choices=["fail", "pass"])
    p.add_argument("--limit", default=None)

    args = parser.parse_args()
    if args.api:
        API_URL = args.api.rstrip("/")

    cmds = {
        "groups": cmd_groups, "summary": cmd_summary, "fails": cmd_fails,
        "passes": cmd_passes, "tests": cmd_tests, "detail": cmd_detail,
        "diff": cmd_diff, "search": cmd_search,
    }
    cmds[args.command](args)
