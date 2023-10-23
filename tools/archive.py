# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Archive module for uploading file to chromeos-localmirror bucket."""

import subprocess


BUCKET_URL = "gs://chromeos-localmirror/distfiles"


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
