#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""The unit tests for archive.py.

Usage:
    python3 archive_unittest.py
"""

from pathlib import Path
import tarfile
import tempfile
import unittest
import unittest.mock

import archive
import common


class TestArchive(unittest.TestCase):
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
            bucket = common.BUCKET_LOCALMIRROT_URL
            archive.upload(file_mock, bucket)

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
                    f"{bucket}/{file_mock.name}",
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
                archive.upload(file_mock, common.BUCKET_LOCALMIRROT_URL)

            # Verify that the `gsutil` command-line tool was not called.
            mock_check_call.assert_not_called()

    def test_generate_tarball(self):
        """Tests the `test_generate_tarball` function."""
        # Create a temporary file.
        with tempfile.NamedTemporaryFile() as f:
            f_path = Path(f.name)
            # Generate a tarball of the temporary file.
            tarball, version = archive.generate_tarball(f_path)

            # Check that the tarball exists.
            self.assertTrue(tarball.exists())

            # Check that the version match the version format in
            # %Y.%m.%d.%H%M%S.
            self.assertRegex(version, r"\d{8}\.\d{6}")
            # Check that the tarball contains the temporary file.
            with tarfile.open(tarball) as tf:
                self.assertIn(f_path.name, tf.getnames())


if __name__ == "__main__":
    unittest.main()
