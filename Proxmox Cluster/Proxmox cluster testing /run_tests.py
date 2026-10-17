#!/usr/bin/env python3
"""
Proxmox Cluster Automated Test Runner & Orchestrator
Innspark / CISAI Proxmox Testing Environment
"""

import os
import sys
import yaml
import json
import argparse
import datetime
from typing import Dict, Any, List

from lib.ssh_client import ProxmoxSSHClient
from lib.test_cluster import ClusterHealthTest
from lib.test_network import NetworkHealthTest
from lib.test_ceph import CephStorageTest
from lib.test_zfs import ZfsStorageTest
from lib.test_migration import MigrationTest
from lib.test_ha import HighAvailabilityTest

# Terminal colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_banner():
    print(f"{CYAN}{BOLD}")
    print("=" * 70)
    print("      PROXMOX 3-NODE CLUSTER AUTOMATED TESTING ENVIRONMENT")
    print("      Ceph (4-Disk) | ZFS RAIDZ2 (7-Disk) | HA | Live Migration")
    print("=" * 70)
    print(f"{RESET}")

def load_config(config_path: str) -> Dict[str, Any]:
    if not os.path.isfile(config_path):
        print(f"{RED}Error: Config file not found at '{config_path}'{RESET}")
        sys.exit(1)
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def format_status(status: str) -> str:
    if status == "PASS":
        return f"{GREEN}{BOLD}[PASS]{RESET}"
    elif status == "WARN":
        return f"{YELLOW}{BOLD}[WARN]{RESET}"
    else:
        return f"{RED}{BOLD}[FAIL]{RESET}"

def generate_markdown_report(report_data: Dict[str, Any], output_path: str):
    ts = report_data.get("timestamp", datetime.datetime.now().isoformat())
    md = []
    md.append(f"# Proxmox Cluster Test Execution Report")
    md.append(f"\n**Execution Timestamp**: `{ts}`  ")
    md.append(f"**Overall Status**: `{'PASS' if report_data.get('all_passed') else 'FAIL'}`\n")
    md.append(f"---\n")

    md.append(f"## Test Summary\n")
    md.append(f"| Test Suite | Result | Total Checks | Passes | Warnings | Failures |")
    md.append(f"| :--- | :---: | :---: | :---: | :---: | :---: |")

    for suite in report_data.get("suites", []):
        name = suite.get("test_name", "Unknown")
        checks = suite.get("checks", [])
        passes = sum(1 for c in checks if c["status"] == "PASS")
        warns = sum(1 for c in checks if c["status"] == "WARN")
        fails = sum(1 for c in checks if c["status"] == "FAIL")
        res_str = "**PASS**" if suite.get("passed") else "**FAIL**"
        md.append(f"| {name} | {res_str} | {len(checks)} | {passes} | {warns} | {fails} |")

    md.append(f"\n---\n")
    md.append(f"## Detailed Test Findings\n")

    for suite in report_data.get("suites", []):
        md.append(f"### {suite.get('test_name')}\n")
        md.append(f"| Check Item | Status | Details |")
        md.append(f"| :--- | :---: | :--- |")
        for c in suite.get("checks", []):
            md.append(f"| {c['name']} | `{c['status']}` | {c['details']} |")
        md.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(md))
    print(f"\n{GREEN}Markdown report saved to:{RESET} {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Proxmox Cluster Automated Test Suite")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--all", action="store_true", help="Run all test suites")
    parser.add_argument("--test", action="append", choices=["cluster", "network", "ceph", "zfs", "migration", "ha"], help="Run specific test suite(s)")
    parser.add_argument("--skip-benchmark", action="store_true", help="Skip safe I/O benchmarks")
    parser.add_argument("--skip-migration", action="store_true", help="Skip VM live migration")
    args = parser.parse_args()

    # Determine suites to run
    selected_tests = args.test if args.test else []
    if args.all or not selected_tests:
        selected_tests = ["cluster", "network", "ceph", "zfs", "ha", "migration"]

    print_banner()
    config = load_config(args.config)
    ssh = ProxmoxSSHClient(config)

    report_data = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cluster_name": config.get("cluster", {}).get("name", "Unknown"),
        "leader_ip": config.get("cluster", {}).get("leader_ip", "Unknown"),
        "all_passed": True,
        "suites": []
    }

    test_classes = {
        "cluster": (ClusterHealthTest, [ssh, config]),
        "network": (NetworkHealthTest, [ssh, config]),
        "ceph": (CephStorageTest, [ssh, config]),
        "zfs": (ZfsStorageTest, [ssh, config]),
        "ha": (HighAvailabilityTest, [ssh, config]),
        "migration": (MigrationTest, [ssh, config])
    }

    for t_key in selected_tests:
        cls, params = test_classes[t_key]
        instance = cls(*params)
        print(f"\n{BOLD}{CYAN}>>> Running: {t_key.upper()} Test Suite...{RESET}")

        if t_key == "ceph":
            res = instance.run(run_benchmark=not args.skip_benchmark)
        elif t_key == "zfs":
            res = instance.run(run_io_test=not args.skip_benchmark)
        elif t_key == "migration":
            res = instance.run(perform_live_migration=not args.skip_migration)
        else:
            res = instance.run()

        report_data["suites"].append(res)
        if not res.get("passed", False):
            report_data["all_passed"] = False

        for c in res.get("checks", []):
            st = c.get("status", "UNKNOWN")
            print(f"  {format_status(st)} {c.get('name')}: {c.get('details')}")

    # Output reports
    os.makedirs("reports", exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    md_file = f"reports/test_report_{stamp}.md"
    json_latest = "reports/test_report_latest.json"
    web_data = "web/data.json"

    generate_markdown_report(report_data, md_file)

    with open(json_latest, "w") as f:
        json.dump(report_data, f, indent=2)
    with open(web_data, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"{GREEN}JSON data saved to:{RESET} {json_latest}")
    print(f"{GREEN}Web dashboard data updated at:{RESET} {web_data}")

    print("\n" + "=" * 70)
    if report_data["all_passed"]:
        print(f"{GREEN}{BOLD}OVERALL RESULT: ALL TESTS PASSED SUCCESSFULLY!{RESET}")
    else:
        print(f"{RED}{BOLD}OVERALL RESULT: SOME CHECKS FAILED - REVIEW REPORT ABOVE.{RESET}")
    print("=" * 70 + "\n")

    sys.exit(0 if report_data["all_passed"] else 1)

if __name__ == "__main__":
    main()
