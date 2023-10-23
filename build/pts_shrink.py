#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cleans a Phoronix Test Suite (PTS) installation based on a requires list

This script removes files from a PTS installation that are not listed in a
provided requires list file. This can be used to reduce the size of the PTS
installation by removing unused or unnecessary files.
"""

import argparse
from pathlib import Path


def shrink(requires_list, target_folder):
    """Shrinks the target folder based on a requires list.

    This function removes files from the specified target folder that are not
    listed in the provided requires list. The allowlist is a set of file paths,
    and any file not present in the requires list is considered extraneous and
    removed.

    Args:
        requires_list: Path to the requires list file containing the list of
                       files to keep.
        target_folder: Target folder to clean, removing files not in the
                       requires_list.
    """
    allowlist = set()
    with requires_list.open("r") as f:
        for line in f:
            allowlist.add(line.strip())

    for file in target_folder.glob("**/*"):
        if file.is_file() and file.as_posix() not in allowlist:
            file.unlink()


def main():
    """Command-line front end for shrinking target folder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-r",
        "--requires_list",
        type=Path,
        required=True,
        help="Path to the allowlist file",
    )
    parser.add_argument(
        "-t",
        "--target_folder",
        type=Path,
        required=True,
        help="Target folder to shrink",
    )
    args = parser.parse_args()

    shrink(args.requires_list, args.target_folder)


if __name__ == "__main__":
    main()
