#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generates a requires list from PTS installed-tests folder

This script generates a requires file specified by the -r option containing the
paths of the root of chroot. It recursively traverses the
var/lib/phoronix-test-suite/installed-tests/pts and collects the full path of
each file, adding it to the requires file. The generated requires list can be
used to identify and managed desired files within a directory tree.
"""

import argparse
from pathlib import Path
import re

import archive
import common


REQUIRES_LIST = "crospts-installed-tests-requires-list"
REQUIRES_LIST_VERSION = "REQUIRES_LIST_VERSION"


def generate_requires_list(output_dir, target_folder):
    """Generates a list of files required in the specified target folder.

    This function scans the target folder recursively for files
    and constructs a list of relative paths prefixed with the `INSTALLED_TESTS`
    directory. The generated list is written to output_dir and the returns the
    requires list file full path.

    Args:
        output_dir: The folder to create requires list file.
        target_folder: The folder containing the test files.

    Returns:
        The path to the temporary file containing the generated requires list.
    """
    requires_list = output_dir / REQUIRES_LIST
    with requires_list.open("w") as f:
        for file in target_folder.glob("**/*"):
            if file.is_file():
                relative_path = file.relative_to(target_folder)
                requires_file = f"/{common.INSTALLED_TESTS}/{relative_path}"
                f.write(f"{requires_file}\n")
    return requires_list


def uprev_dockerfile(dockerfile, version):
    """Uprevs the requires list tarball version from Dockerfile.

    Update the Dockerfile by replacing the value of the `REQUIRES_LIST_VERSION`
    with the version of the provided tarball.

    Args:
        dockerfile: Path to the Dockerfile to be updated.
        version: String of the tarball version.
    """
    pattern = f"ENV {REQUIRES_LIST_VERSION}=.*"
    with dockerfile.open("r+") as f:
        content = f.read()
        updated_content = re.sub(
            pattern, f"ENV {REQUIRES_LIST_VERSION}={version}", content
        )
        f.seek(0)
        f.write(updated_content)
        f.truncate()


def main():
    """Command-line front end for building requires list."""
    parser = argparse.ArgumentParser(
        description="Generate a requires from a directory tree"
    )
    parser.add_argument(
        "-r",
        "--root_folder",
        type=Path,
        required=True,
        help="Root folder of the PTSworld chroot to generate requires from",
    )
    parser.add_argument(
        "-n",
        "--no_upload",
        dest="upload",
        action="store_false",
        help="Do not upload the artifact tarball.",
    )
    parser.add_argument(
        "-d",
        "--dockerfile",
        type=Path,
        help="Path to Dockerfile to uprev the requires list tarball version.",
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        type=Path,
        default=Path.cwd(),
        help="Path at which to create the requires list file",
    )
    args = parser.parse_args()

    target_folder = args.root_folder / common.INSTALLED_TESTS

    requires_list = generate_requires_list(args.output_dir, target_folder)
    print(f"Generated installed_tests requires list: {requires_list}")
    tarball, version = archive.generate_tarball(requires_list)
    print(f"Generated installed_tests requires list tarball: {tarball}")

    if args.upload:
        archive.upload(tarball, common.BUCKET_LOCALMIRROT_URL)

    if args.dockerfile:
        uprev_dockerfile(args.dockerfile, version)


if __name__ == "__main__":
    main()
