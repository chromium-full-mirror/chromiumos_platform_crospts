#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Extracts the docker container image to a PTSWorld chroot image."""

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import archive
import common


# Minimal ext4 image without journal is 128KB
MIN_EXT4_SIZE = 131072
EXTERNAL_DATA_PATH = (
    Path(__file__).parents[2]
    / "tast-tests"
    / "src"
    / "go.chromium.org"
    / "tast-tests"
    / "cros"
    / "local"
    / "bundles"
    / "cros"
    / "crospts"
    / "data"
)


@contextlib.contextmanager
def mount(src, dst, mount_type):
    """Context manager for mounting a filesystem.

    This context manager mounts a filesystem and automatically unmounting it on
    exit.

    Args:
        src: Path to the source device or directory.
        dst: Path to the mount point directory.
        mount_type: Type of filesystem to mount (e.g., "ext4").
    """

    try:
        cmd = ["sudo", "mount"]
        if mount_type:
            cmd += ["-t", mount_type]
        subprocess.check_call(cmd + [src, dst])
        yield
    finally:
        subprocess.check_call(["sudo", "umount", dst])


def make_ext4_image(image, size):
    """Creates an ext4 filesystem image.

    This function creates an ext4 filesystem image with the specified size, and
    removes the journal. The minimum size of the image is 128KB which will be
    auto expanded.

    Args:
        image: String of the output image file.
        size: Size of the image in bytes.

    Returns:
        None
    """
    size = max(size, MIN_EXT4_SIZE)

    with open(image, "wb+") as image_file:
        image_file.truncate(size)
    subprocess.check_call(
        [
            "/sbin/mkfs.ext4",
            "-O",
            "^has_journal",
            image,
        ]
    )


def uprev_tast_external_data(external_data, package):
    """Updates the tast external data file with the package information.

    The tast external data is json format data which stores url, size and
    sha256sum information. This function get the package data information and
    update to external data.

    Args:
        external_data: Path to the external data file.
        package: Path to the package file.
    """
    with package.open("rb") as p:
        data = p.read()
        sha256sum = hashlib.sha256(data).hexdigest()

    meta = json.dumps(
        {
            "url": f"{common.BUCKET_TEST_ASSETS_PUBLIC_URL}/{package.name}",
            "size": os.stat(package).st_size,
            "sha256sum": sha256sum,
        },
        indent=4,
    )

    with external_data.open("w") as f:
        f.write(meta)


def create_fs_image(
    source,
    image,
    shrink=True,
    exclude_dir=None,
):
    """Creates a filesystem image

    This function creates a filesystem image from a directory.

    Args:
        source: String of the source directory.
        image: String of the output image file.
        shrink: Whether to shrink the image after copying.
               Defaults to True.
        exclude_dir: Path to the directory to exclude from the image.
               Defaults to None.

    Returns:
        None
    """
    cmd = ["sudo", "du", "-bsx", source]
    if exclude_dir is not None:
        # Use normpath to normalize the path and remove any trailing '/'
        # to ensure compatibility with the exclude parameter.
        cmd.extend(["--exclude", os.path.normpath(exclude_dir)])

    du = subprocess.check_output(cmd).decode("utf-8")
    # du command reports the size of the files. Allocate additional space
    # for filesystem metadata needed during the copy process. After the
    # copy,  the image will be shrank to fit.
    image_size = round(int(du.split()[0]) * 1.2)

    if os.path.isfile(image):
        os.remove(image)

    make_ext4_image(image, image_size)
    # Copy the files into the image.
    with tempfile.TemporaryDirectory() as mnt_dir:
        with mount(image, mnt_dir, "ext4"):
            # Normalize source path and add '/' to ensure compatibility with
            # rsync.
            src = os.path.normpath(source) + "/"
            cmd = ["sudo", "rsync", "-aH", src, mnt_dir]
            if exclude_dir is not None:
                # Convert to relative path to ensure compatibility with the
                # exclude parameter.
                exclude = os.path.relpath(exclude_dir, src)
                cmd.extend(["--exclude", exclude])
            subprocess.check_call(cmd)

    # Shrink the image to save space.
    if shrink:
        subprocess.check_call(["/sbin/e2fsck", "-y", "-f", image])
        subprocess.check_call(["/sbin/resize2fs", "-M", image])


@contextlib.contextmanager
def create_container_for_export(docker_image_name):
    """Creates a Docker container for export.

    This function gets the Docker container for export and returns the
    container ID.

    Args:
        docker_image_name: Name of the docker image to export.

    Returns:
        Container ID
    """
    container = (
        subprocess.check_output(["sudo", "docker", "create", docker_image_name])
        .decode(sys.stdout.encoding)
        .strip()
    )
    try:
        yield container
    finally:
        subprocess.check_call(["sudo", "docker", "container", "rm", container])


def extract_container(container_id, output_dir):
    """Extracts a Docker container to a directory.

    This function extracts a Docker container to a directory.

    Args:
        container_id: ID of the Docker container to extract.
        output_dir: Path to the directory to extract the container to.

    Returns:
        None
    """
    print("Extracting to", output_dir, " - This may take a while")
    cmd = ["sudo", "docker", "export", container_id]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as extract:
        subprocess.check_call(
            ["tar", "-x", "-F", "-", "-C", output_dir], stdin=extract.stdout
        )
        ret = extract.wait()
        if ret != 0:
            raise subprocess.CalledProcessError(extract.returncode, cmd)


def convert(docker_image_name, base_img, pts_img, should_shrink):
    """Converts a docker container image to a PTSWorld chroot image.

    Args:
        docker_image_name: Name of the docker image to export.
        base_img: Name of the base rootfs image to be created.
        pts_img: Name of the pts data image to be created.
        should_shrink: Whether to shrink the image after copying.

    Returns:
        None
    """
    with create_container_for_export(docker_image_name) as container_id:
        with tempfile.TemporaryDirectory() as tempdir:
            extract_container(container_id, tempdir)
            create_fs_image(
                tempdir,
                base_img,
                shrink=should_shrink,
                exclude_dir=f"{tempdir}/{common.PTS_DATA_PATH}",
            )
            create_fs_image(
                f"{tempdir}/{common.PTS_DATA_PATH}",
                pts_img,
                shrink=should_shrink,
            )


def main():
    """Command-line front end for extracting docker image to PTSWorld image."""
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--base-img",
        default="base.img",
        help="Name of the base rootfs image to be created",
    )
    parser.add_argument(
        "--pts-img",
        default="pts-data.img",
        help="Name of the pts data image to be created, which is \
              /var/lib/phoronix-test-suite in chroot",
    )
    parser.add_argument(
        "--no-shrink",
        action="store_false",
        dest="shrink",
        help=(
            "Do not shrink the disk image. Useful when you need to make "
            "live modifications to it"
        ),
    )
    parser.add_argument(
        "--docker-image",
        default=common.PTSWORLD_TAG,
        help="Name of the docker image you want to export",
    )
    parser.add_argument(
        "-n",
        "--no-upload",
        dest="upload",
        action="store_false",
        help="Do not upload the artifact tarball.",
    )
    parser.add_argument(
        "--no-uprev",
        dest="uprev",
        action="store_false",
        help="Do not uprev the external data in crospts tast test.",
    )

    args = parser.parse_args()

    convert(args.docker_image, args.base_img, args.pts_img, args.shrink)
    base_tarball, _ = archive.generate_tarball(Path(args.base_img))
    pts_tarball, _ = archive.generate_tarball(Path(args.pts_img))
    if args.upload:
        archive.upload(base_tarball, common.BUCKET_TEST_ASSETS_PUBLIC_URL)
        archive.upload(pts_tarball, common.BUCKET_TEST_ASSETS_PUBLIC_URL)

    if args.uprev:
        strip_version_pattern = r"-\d{8}.\d{6}"
        base_external_data_name = (
            re.sub(strip_version_pattern, "", base_tarball.name) + ".external"
        )
        pts_external_data_name = (
            re.sub(strip_version_pattern, "", pts_tarball.name) + ".external"
        )
        uprev_tast_external_data(
            EXTERNAL_DATA_PATH / f"{base_external_data_name}", base_tarball
        )
        uprev_tast_external_data(
            EXTERNAL_DATA_PATH / f"{pts_external_data_name}", pts_tarball
        )


if __name__ == "__main__":
    main()
