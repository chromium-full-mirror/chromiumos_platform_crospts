#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Runs the python unittest files in tools folder.

Script for Running Unit Tests in the Tools Folder
This script serves two purposes:
1. Pre-submit hook: When invoked with the "files" argument containing a list of
   pre-submit files, it runs all unit tests in the "tools" folder if any of
   those files belong to the "tools" folder.
2. Standalone runner: If no "files" argument is provided, it simply runs all
   unit tests in the "tools" folder.
"""

import argparse
import glob
import os
import sys
import unittest


# The root directory of the tools folder.
TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Function to find the files which are named as *_unittest.py in ../ folders
def run_all_unittests(base_dir):
    """Finds and runs all unittests in the specified directory.

    Finds all files ending with "_unittest.py" in the specified directory and
    runs them as Python unittests.

    Args:
        base_dir: The directory to search for test files.
    """
    sys.path.append(base_dir)

    # Find all files matching the unittest file pattern.
    test_files = glob.glob(f"{base_dir}/*_unittest.py")

    test_suite = unittest.TestSuite()
    for test_file in test_files:
        # Import the test module from the file.
        module_name = os.path.basename(test_file)[:-3]
        test_module = __import__(module_name)

        # Find all test cases in the module.
        test_cases = unittest.defaultTestLoader.loadTestsFromModule(test_module)

        # Add the test cases to the test suite.
        test_suite.addTests(test_cases)

    # Run the test suite.
    runner = unittest.TextTestRunner()
    runner.run(test_suite)


def is_change_for_tools(files):
    """Checks if the changed files in the 'tools' directory.

    Args:
        files: The files to check.

    Returns:
        True if the file name starts with 'tools', False otherwise.
    """
    for f in files:
        if f.startswith("tools"):
            return True
    return False


def main():
    """Command-line front end to run unittest for tools."""
    parser = argparse.ArgumentParser(description="Run the unittest for tools")
    parser.add_argument(
        "--presubmit_files", nargs="*", help="List of presubmit files to check."
    )
    args = parser.parse_args()
    if not args.presubmit_files or is_change_for_tools(args.presubmit_files):
        run_all_unittests(TOOLS_ROOT)


if __name__ == "__main__":
    main()
