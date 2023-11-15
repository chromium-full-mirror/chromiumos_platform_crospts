#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""The unit tests for requires_gen.py.

Usage:
    python3 requires_gen_unittest.py
"""

from pathlib import Path
import tempfile
import unittest

import common
import requires_gen


class TestRequiresGen(unittest.TestCase):
    """Tests the requires_gen module.

    This class contains unit tests for the `requires_gen` module.
    """

    def test_generate_requires_list(self):
        """Tests the `generate_requires_list` function."""
        test_file = "file"
        # Create a temporary directory and a file inside it.
        # pylint: disable=line-too-long
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as output_dir:
            src_dir_path = Path(src_dir) / common.INSTALLED_TESTS
            src_dir_path.mkdir(parents=True)
            (src_dir_path / test_file).touch()

            output_dir_path = Path(output_dir)

            # Generate the requires list.
            requires_list = requires_gen.generate_requires_list(
                output_dir_path, src_dir_path
            )

            # Check that the requires list contains the file path.
            with requires_list.open() as f:
                expected_string = f"/{common.INSTALLED_TESTS}/{test_file}"
                self.assertIn(expected_string, f.read())

    def test_uprev_dockerfile(self):
        """Tests the `test_uprev_dockerfile` function."""
        new_version = "2023.01.01.112233"
        version_field = f"ENV {requires_gen.REQUIRES_LIST_VERSION}"

        # Create a temporary Dockerfile.
        with tempfile.NamedTemporaryFile() as dockerfile:
            # Write the following content to the Dockerfile:
            old_version_string = f"{version_field}=2023.01.01.000000\n"
            dockerfile.write(old_version_string.encode("utf-8"))
            dockerfile.flush()

            # Uprev the requires list tarball version in the Dockerfile.
            requires_gen.uprev_dockerfile(Path(dockerfile.name), new_version)

            with open(dockerfile.name, encoding="utf-8") as f:
                expected_new_version_string = f"{version_field}={new_version}\n"
                self.assertEqual(expected_new_version_string, f.read())


if __name__ == "__main__":
    unittest.main()
