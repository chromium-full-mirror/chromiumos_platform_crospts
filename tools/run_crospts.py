#!/usr/bin/env vpython3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tools to run CrosPTS tast tests and upload results.

run_crospts.py wraps the `cros_sdk tast` to list or run the CrosPTS tast tests
and upload the results to the Google Cloud bucket or CNS for internal user.
"""

import argparse
from pathlib import Path
import re
import subprocess
import sys


THIS_FILE = Path(__file__).resolve()
CHROMIUMOS_ROOT = THIS_FILE.parent.parent.parent.parent.parent


# List the available tests
def list_crospts_tests(dut):
    """List the available CrosPTS tests."""
    tast_run_command = ["cros_sdk", "tast", "list", dut, "crospts.PerfSuite*"]
    crospts_list = subprocess.run(
        tast_run_command, stdout=subprocess.PIPE, check=True
    )

    supported_tests = {}
    pattern = r"crospts\.PerfSuite\.(\w+)_cros_(x86|arm64)"
    tests = crospts_list.stdout.decode("utf-8").splitlines()
    for test in tests:
        match = re.search(pattern, test)
        if match:
            test_name = match.group(1)
            arch = match.group(2)

            if test_name not in supported_tests:
                supported_tests[test_name] = arch
            elif supported_tests[test_name] != arch:
                supported_tests[test_name] = "both"

    print("The microbenchmarks of CrosPTS:")
    for test, supported_arch in supported_tests.items():
        if supported_arch == "both":
            print(f"   {test}")
        else:
            print(f"   {test}\t({supported_arch} only)")


def parse_arguments(argv):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-l", "--list", action="store_true", help="List the available tests"
    )

    parser.add_argument(
        "target", help='SSH connection spec of the form "[user@]host[:port]"'
    )
    return parser.parse_args(argv)


def main(argv):
    """Command-line front end for building requires list."""
    args = parse_arguments(argv)

    if args.list:
        list_crospts_tests(args.target)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
