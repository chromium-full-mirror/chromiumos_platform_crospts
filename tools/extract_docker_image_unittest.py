#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""The unit tests for extract_docker_image.py.

Usage:
    python3 extract_docker_image_unittest.py
"""

import os
from pathlib import Path
import unittest
import unittest.mock

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


# TODO(darrenwu): Add unittest for docker container functions.


if __name__ == "__main__":
    unittest.main()
