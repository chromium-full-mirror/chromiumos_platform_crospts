#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""The unit tests for extract_docker_image.py.

Usage:
    python3 extract_docker_image_unittest.py
"""

import json
import os
from pathlib import Path
import unittest
import unittest.mock

import common
import extract_docker_image


class TestFileSystemImage(unittest.TestCase):
    """Tests the extract_docker_image module.

    This class contains unit tests for the file system image related functions
    in the extract_docker_image module.
    """

    def test_mount_ext4(self):
        """Tests the `mount_ext4` function."""
        with unittest.mock.patch("subprocess.check_call") as mock_check_call:
            src = "/tmp/src"
            dst = "/tmp/dst"
            fs = "ext4"
            with extract_docker_image.mount(
                src=src,
                dst=dst,
                mount_type=fs,
            ):
                # User code here
                pass

            mock_check_call.assert_has_calls(
                [
                    unittest.mock.call(["sudo", "mount", "-t", fs, src, dst]),
                    unittest.mock.call(["sudo", "umount", dst]),
                ]
            )

    def test_make_ext4_image(self):
        """Tests the `make_ext4_image` function."""
        target = "/tmp/test.img"
        expected_call = [
            "/sbin/mkfs.ext4",
            "-O",
            "^has_journal",
            target,
        ]
        with unittest.mock.patch("subprocess.check_call") as mock_check_call:
            with self.subTest("Less than minimum size"):
                size = extract_docker_image.MIN_EXT4_SIZE - 1024
                extract_docker_image.make_ext4_image(target, size)

                self.assertTrue(Path(target).is_file())
                mock_check_call.assert_has_calls(
                    [unittest.mock.call(expected_call)]
                )
                self.assertEqual(
                    os.path.getsize(target), extract_docker_image.MIN_EXT4_SIZE
                )
            with self.subTest("Greater than minimum size"):
                size = extract_docker_image.MIN_EXT4_SIZE + 1024
                extract_docker_image.make_ext4_image(target, size)

                self.assertTrue(Path(target).is_file())
                mock_check_call.assert_has_calls(
                    [unittest.mock.call(expected_call)]
                )
                self.assertEqual(
                    os.path.getsize(target),
                    extract_docker_image.MIN_EXT4_SIZE + 1024,
                )

    def test_uprev_external_data(self):
        """Tests the `uprev_external_data` function."""
        test_package = Path("/tmp/test_package")
        external_data = Path("/tmp/external_data")
        expected_size = 1024
        # The sha256sum of zeros filled file in 1024 bytes.
        expected_sha256sum = (
            "5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef"
        )
        with test_package.open("wb") as f:
            f.write(b"\x00" * expected_size)

        extract_docker_image.uprev_tast_external_data(
            external_data, test_package
        )

        with external_data.open("r", encoding="utf-8") as f:
            json_object = json.load(f)
            self.assertEqual(
                json_object["url"],
                f"{common.BUCKET_TEST_ASSETS_PUBLIC_URL}/{test_package.name}",
            )
            self.assertEqual(json_object["size"], expected_size)
            self.assertEqual(json_object["sha256sum"], expected_sha256sum)


# TODO(darrenwu): Add unittest for docker container functions.


if __name__ == "__main__":
    unittest.main()
