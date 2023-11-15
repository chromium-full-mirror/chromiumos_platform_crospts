# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Archive module for uploading file to chromeos-localmirror bucket."""

import datetime
from pathlib import Path
import subprocess


BUCKET_URL = "gs://chromeos-localmirror/distfiles"


def generate_tarball(target_file):
    """Generates a compressed tarball of the specified file.

    This function generates tarball file and appends a version to the tarball
    filename.

    Args:
        target_file: Path of the target file to be archived.

    Returns:
        The path to the generated tarball and version.
    """
    version = datetime.datetime.now().strftime("%Y.%m.%d.%H%M%S")
    tarball = Path(f"{target_file}-{version}.tar.xz")
    work_dir = target_file.parents[0]
    subprocess.check_call(
        [
            "tar",
            "-Ipixz",
            "-c",
            "-f",
            str(tarball),
            "-C",
            str(work_dir),
            target_file.name,
        ]
    )
    return tarball, version


def upload(archive_file):
    """Uploads the provided file to the chromeos-localmirror bucket.

    Upload the file using `gsutil` command-line tool to upload
    the file with the "public-read" access level.

    Args:
        archive_file: Path to the archive file to be uploaded.
    """
    if not archive_file:
        raise TypeError("Archive file not set")
    if not archive_file.exists():
        raise FileNotFoundError(f"Local copy of {archive_file.name} not found")

    print("Uploading:", archive_file.name)
    cmd = [
        "gsutil",
        "cp",
        "-n",
        "-a",
        "public-read",
        str(archive_file),
        f"{BUCKET_URL}/{archive_file.name}",
    ]
    subprocess.check_call(cmd)
