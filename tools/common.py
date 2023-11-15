# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common modules for CrosPTS tools."""

PTSWORLD_TAG = "ptsworld"

# PTS related folder
PTS_DATA_PATH = "var/lib/phoronix-test-suite"
INSTALLED_TESTS = PTS_DATA_PATH + "/installed-tests/pts"

# GS bucket
BUCKET_LOCALMIRROT_URL = "gs://chromeos-localmirror/distfiles"
BUCKET_TEST_ASSETS_PUBLIC_URL = (
    "gs://chromiumos-test-assets-public/tast/cros/crospts"
)

# DLC
DLC_NAME = PTSWORLD_TAG
