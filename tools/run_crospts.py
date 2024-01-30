#!/usr/bin/env vpython3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tools to run CrosPTS tast tests and upload results.

run_crospts.py wraps the `cros_sdk tast` to list or run the CrosPTS tast tests
and upload the results to the Google Cloud bucket or CNS for internal user.
"""

# [VPYTHON:BEGIN]
# wheel: <
#  name: "infra/python/wheels/google-auth-py3"
#  version: "version:2.16.2"
# >
# # google-auth dep
# wheel: <
#  name: "infra/python/wheels/rsa-py3"
#  version: "version:4.7.2"
# >
# # google-auth dep
# wheel: <
#  name: "infra/python/wheels/cachetools-py3"
#  version: "version:4.2.2"
# >
# # google-auth dep
# wheel: <
#  name: "infra/python/wheels/six-py2_py3"
#  version: "version:1.16.0"
# >
# # google-auth dep
# wheel: <
#  name: "infra/python/wheels/pyasn1_modules-py2_py3"
#  version: "version:0.2.8"
# >
# # pyasn1_modules dep
# wheel: <
#  name: "infra/python/wheels/pyasn1-py3"
#  version: "version:0.4.8"
# >
# wheel: <
#  name: "infra/python/wheels/google-cloud-storage-py3"
#  version: "version:2.1.0"
# >
# # google-cloud-storage dep
# wheel: <
#   name: "infra/python/wheels/google-resumable-media-py3"
#   version: "version:2.3.0"
# >
# # google-cloud-storage dep
# wheel: <
#   name: "infra/python/wheels/google-cloud-core-py3"
#   version: "version:2.2.2"
# >
# # google-cloud-storage dep
# wheel: <
#   name: "infra/python/wheels/google-crc32c/${vpython_platform}"
#   version: "version:1.3.0"
# >
# # google-cloud-storage dep
# wheel: <
#   name: "infra/python/wheels/google-api-core-py3"
#   version: "version:2.11.0"
# >
# # google-api-core-dep
# wheel: <
#   name: "infra/python/wheels/grpcio/${vpython_platform}"
#   version: "version:1.44.0"
# >
# # google-api-core-dep
# wheel: <
#   name: "infra/python/wheels/grpcio-status-py3"
#   version: "version:1.44.0"
# >
# # google-api-core dep
# wheel: <
#   name: "infra/python/wheels/requests-py2_py3"
#   version: "version:2.26.0"
# >
# # requests dep
# wheel: <
#   name: "infra/python/wheels/urllib3-py2_py3"
#   version: "version:1.26.6"
# >
# # requests dep
# wheel: <
#   name: "infra/python/wheels/certifi-py2_py3"
#   version: "version:2021.5.30"
# >
# # requests dep
# wheel: <
#   name: "infra/python/wheels/idna-py3"
#   version: "version:3.2"
# >
# # requests dep
# wheel: <
#   name: "infra/python/wheels/certifi-py2_py3"
#   version: "version:2021.5.30"
# >
# # requests dep
# wheel: <
#   name: "infra/python/wheels/charset_normalizer-py3"
#   version: "version:2.0.4"
# >
# # google-api-core dep
# wheel: <
#   name: "infra/python/wheels/googleapis-common-protos-py2_py3"
#   version: "version:1.59.0"
# >
# # google-api-core dep
# wheel: <
#   name: "infra/python/wheels/protobuf-py3"
#   version: "version:4.21.9"
# >
# wheel: <
#   name: "infra/python/wheels/google-auth-py3"
#   version: "version:2.16.2"
# >
# [VPYTHON:END]

import argparse
import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from google.cloud import storage  # pylint:disable=import-error
from google.oauth2 import service_account  # pylint:disable=import-error


THIS_FILE = Path(__file__).resolve()
CHROMIUMOS_ROOT = THIS_FILE.parent.parent.parent.parent.parent


# List the available tests
def list_crospts_tests(dut):
    """List the available CrosPTS tests."""
    tast_run_command = ["cros_sdk", "tast", "list", dut, "crospts.PerfSuite*"]
    crospts_list = subprocess.run(
        tast_run_command, stdout=subprocess.PIPE, check=True
    )

    supported_tests = {}
    pattern = r"crospts\.PerfSuite\.(\w+)_cros_(x86|arm64)"
    tests = crospts_list.stdout.decode("utf-8").splitlines()
    for test in tests:
        match = re.search(pattern, test)
        if match:
            test_name = match.group(1)
            arch = match.group(2)

            if test_name not in supported_tests:
                supported_tests[test_name] = arch
            elif supported_tests[test_name] != arch:
                supported_tests[test_name] = "both"

    print("The microbenchmarks of CrosPTS:")
    for test, supported_arch in supported_tests.items():
        if supported_arch == "both":
            print(f"   {test}")
        else:
            print(f"   {test}\t({supported_arch} only)")


def get_target_arch(dut):
    """Get the target architecture in result string x86 or arm64."""
    ssh_command = ["ssh", dut, "uname", "-m"]
    arch = subprocess.run(ssh_command, stdout=subprocess.PIPE, check=True)
    if arch.stdout.decode("utf-8").strip() == "x86_64":
        return "x86"
    elif arch.stdout.decode("utf-8").strip() == "aarch64":
        return "arm64"

    raise RuntimeError("Unknown target architecture.")


def tast_test_name(test_name, arch):
    """Return the tast test name."""
    return f"crospts.PerfSuite.{test_name}_cros_{arch}"


def run_crospts_tests(dut, tests):
    """Run the CrosPTS tests."""
    tast_tests = []
    arch = get_target_arch(dut)

    if tests == "all":
        tast_tests = [tast_test_name("*", arch)]
    else:
        tast_tests = [tast_test_name(test, arch) for test in tests.split(",")]

    results_dir = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    tast_run_command = [
        "cros_sdk",
        "tast",
        "run",
        "-resultsdir",
        f"/tmp/tast/results/{results_dir}",
        dut,
    ] + tast_tests
    subprocess.run(tast_run_command, check=True)
    return results_dir


def tar_results(results_dir, target_dir):
    """Tar the results directory to xz tarball to new created tmp folder."""
    tarball_path = f"{target_dir}/{results_dir}.tar.xz"
    tar_command = [
        "tar",
        "-Ipixz",
        "-cf",
        tarball_path,
        "-C",
        f"{CHROMIUMOS_ROOT}/out/tmp/tast/results/",
        results_dir,
    ]
    subprocess.run(tar_command, check=True)
    return tarball_path


def load_credential(credential_path):
    """Load the credential file."""
    if not os.path.isfile(credential_path):
        raise FileNotFoundError(
            f"Credential file {credential_path} does not exist."
        )
    return service_account.Credentials.from_service_account_file(
        credential_path
    )


def validate_credential(bucket_name, credential, credential_path):
    """Validate the credential."""
    client = storage.Client(credentials=credential)
    try:
        client.get_bucket(bucket_name)
        return True
    except Exception as exe:
        raise PermissionError(
            f"Invalid credential: {credential_path} cannot"
            f" access GS bucket: {bucket_name}."
        ) from exe


def upload_results(bucket_name, credential, tarball_path):
    """Upload the results to GS bucket."""
    # The partner name is the last part of the bucket name
    # e.g. chromeos-moblab-<partner>
    partner = bucket_name.split("-")[-1]
    remote_path = f"crospts/archive/{partner}/{tarball_path.split('/')[-1]}"
    print(f"Uploading {tarball_path} to gs://{bucket_name}/{remote_path}...")

    client = storage.Client(credentials=credential)
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(remote_path)
    blob.upload_from_filename(tarball_path)


def parse_arguments(argv):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-l", "--list", action="store_true", help="List the available tests"
    )
    group.add_argument(
        "-p",
        "--pts",
        metavar="tests",
        type=str,
        help="Specify the test(s) to run (comma-separated or 'all')",
    )

    parser.add_argument(
        "target", help='SSH connection spec of the form "[user@]host[:port]"'
    )
    parser.add_argument(
        "-u",
        "--upload",
        metavar="storage",
        help="Specify the storage. For Googler, please use 'cns'."
        "For partner, please use your GS bucket name",
    )
    parser.add_argument(
        "-c",
        "--credential",
        metavar="path",
        default="~/.service_account.json",
        help="Path to the credential file",
    )
    return parser.parse_args(argv)


def main(argv):
    """Command-line front end for building requires list."""
    args = parse_arguments(argv)

    if args.list:
        list_crospts_tests(args.target)
        return 0

    if args.upload:
        # TODO(darrenwu): Add uploading to CNS
        credential = load_credential(args.credential)
        validate_credential(args.upload, credential, args.credential)

    results_dir = run_crospts_tests(args.target, args.pts)

    if args.upload:
        tmp_dir = tempfile.mkdtemp()
        tarball_path = tar_results(results_dir, tmp_dir)
        # TODO(darrenwu): Add uploading CSV file.
        upload_results(args.upload, credential, tarball_path)
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
