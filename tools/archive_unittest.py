#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""The unit tests for archive.py.

Usage:
    python3 archive_unittest.py
"""

import unittest
import unittest.mock

import archive


class TestUpload(unittest.TestCase):
    """Tests the archive module.

    This class contains unit tests for the `archive` module.
    """

    def test_upload_file(self):
        """Tests the `upload` function."""
        # Create a mock file object.
        file_mock = unittest.mock.Mock()
        file_mock.name = "test.tar.xz"
        file_mock.exists.return_value = True

        # Patch the `gsutil` command-line tool.
        with unittest.mock.patch("subprocess.check_call") as mock_check_call:
            archive.upload(file_mock)

            # Verify that the `gsutil` command-line tool was called with the
            # correct arguments.
            mock_check_call.assert_called_with(
                [
                    "gsutil",
                    "cp",
                    "-n",
                    "-a",
                    "public-read",
                    str(file_mock),
                    f"{archive.BUCKET_URL}/{file_mock.name}",
                ]
            )

    def test_upload_missing_file(self):
        """Tests the `upload` when file not exists."""
        # Create a mock file object that does not exist.
        file_mock = unittest.mock.Mock()
        file_mock.name = "test.tar.xz"
        file_mock.exists.return_value = False

        # Patch the `gsutil` command-line tool.
        with unittest.mock.patch("subprocess.check_call") as mock_check_call:
            # Call the `upload` function.
            with self.assertRaises(FileNotFoundError):
                archive.upload(file_mock)

            # Verify that the `gsutil` command-line tool was not called.
            mock_check_call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
