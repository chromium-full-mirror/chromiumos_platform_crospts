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
import contextlib
import datetime
import getpass
import json
import math
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
CHROMIUMOS_RESULTS_DIR = CHROMIUMOS_ROOT / "out/tmp/tast/results"

CNS_ROOT = "/cns/yb-d/home/crospts-storage/crospts"


def flash_image(dut, version):
    """Flash image on to DUT."""
    flash = CHROMIUMOS_ROOT / "src/platform/dev/contrib/fflash/fflash"
    flash_cmd = [flash, dut, "--clobber-stateful=yes", f"-{version}"]
    subprocess.run(flash_cmd, check=True)


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


def is_4g_ram(dut):
    """Detect DUT is 4GB RAM."""
    ssh_command = ["ssh", dut, "cat", "/proc/meminfo"]
    meminfo = subprocess.run(
        ssh_command, stdout=subprocess.PIPE, check=True
    ).stdout.decode("utf-8")
    match = re.search(r"MemTotal:\s+(\d+) kB", meminfo)
    if match:
        mem_size = int(match.group(1))
    else:
        raise RuntimeError("No MemTotal value be found")
    # The 4GB is 4194304 kB
    return mem_size < 4194304


def tast_test_name(test_name, arch):
    """Return the tast test name."""
    return f"crospts.PerfSuite.{test_name}_cros_{arch}"


def run_crospts_tests(dut, tests):
    """Run the CrosPTS tests."""
    tast_tests = []
    arch = get_target_arch(dut)

    if tests == "all":
        # TODO(darrenwu): Add back the mbw and compress lz4 tests for 4GB DUT.
        # The crospts test encounters a stuck state when run on DUT with 4GB of
        # RAM during testing compress lz4(b/316035777) and mbw (b/315897893)
        # tests. Remove these tests when run all tests for 4GB RAM DUT.
        if is_4g_ram(dut):
            tast_run_command = [
                "cros_sdk",
                "tast",
                "list",
                dut,
                tast_test_name("*", arch),
            ]
            crospts_list = subprocess.run(
                tast_run_command, stdout=subprocess.PIPE, check=True
            )
            tast_tests = crospts_list.stdout.decode("utf-8").splitlines()
            tast_tests = [
                test
                for test in tast_tests
                if "lz4" not in test and "mbw" not in test
            ]
        else:
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
    tarball_path = target_dir / f"{results_dir}.tar.xz"
    tar_command = [
        "tar",
        "-Ipixz",
        "-cf",
        str(tarball_path),
        "-C",
        str(CHROMIUMOS_RESULTS_DIR),
        results_dir,
    ]
    subprocess.run(tar_command, check=True)
    return tarball_path


def get_uploader_info(remote_storage):
    """Return the uploader group and uploader name."""
    if remote_storage == "cns":
        # The uploader is ldap for internal user
        return "internal", getpass.getuser()
    else:
        # For partner, the remote storage is GS bucket
        # The uploader is the last part of the bucket name, i.e. the partner
        # name e.g. chromeos-moblab-<partner>
        return "partners", remote_storage.split("-")[-1]


def parse_dut_info(results_dir_path):
    """Parse the dut_info.txt file."""
    dut_info_txt = CHROMIUMOS_RESULTS_DIR / results_dir_path / "dut-info.txt"
    with dut_info_txt.open("r", encoding="utf-8") as f:
        dut_info = f.read()

    model = re.findall('model: "(.*)"', dut_info)[0].strip().lower()

    # The os_version string is in the format of
    # <variant>/<version tag>
    version_strings = (
        re.findall('os_version: "(.*)"', dut_info)[0].strip().split("/")
    )
    variant = version_strings[0]
    # The version tag is in the format of R<milestone>-<build.branch.patch>
    version_tag = version_strings[1].split("-")
    # Drop the prefix "R"
    milestone = version_tag[0][1:]
    os_version = version_tag[1]

    # size_megabytes is actually the number of MiB usable by the kernel, which
    # is physical RAM minus various reserved regions. Using ceil should give the
    # actual number of GB installed.
    memory_gb = math.ceil(
        int(re.findall("size_megabytes:(.*)", dut_info)[0]) / 1000
    )

    return {
        "model": model,
        "variant": variant,
        "milestone": milestone,
        "os_version": os_version,
        "memory_gb": memory_gb,
    }


def parse_lscpu(results_dir_path):
    """Parse the lscpu output."""
    lscpu_txt = (
        CHROMIUMOS_RESULTS_DIR / results_dir_path / "system_logs/lscpu.txt"
    )
    with lscpu_txt.open("r", encoding="utf-8") as f:
        lscpu = f.read()

    cpu_model = re.findall("Model name:(.*)", lscpu)[0].strip()
    # The Model name contains some extra characters, e.g.
    # "12th Gen Intel(R) Core(TM) i7-1265U".
    # In order to get the crosbolt like sku format, e.g.
    # 12th_Gen_IntelR_CoreTM_i7_1265U_8GB. Remove all non-alphanumeric
    # characters and extra spaces. As the example string, the result should be
    # "12th Gen IntelR CoreTM i71265U". The crosbolt like sku format will be
    # concatenated later with memory size.
    cpu_model = re.sub(r"[^a-zA-Z0-9 \n\.]", "", cpu_model)

    return {"cpu_model": cpu_model}


def parse_lsb_release(results_dir_path):
    """Parse the lsb_release."""
    lsb_release_txt = (
        CHROMIUMOS_RESULTS_DIR / results_dir_path / "system_logs/lsb-release"
    )
    with lsb_release_txt.open("r", encoding="utf-8") as f:
        lsb_release = f.read()
    board = re.findall("CHROMEOS_RELEASE_BOARD=(.*)", lsb_release)[0].strip()
    return {
        "board": board,
    }


def extract_results_chart(results_chart_json_path):
    """Extract the results-chart.json file to list of dictionaries."""
    results_chart_data = []
    if results_chart_json_path.is_file():
        with results_chart_json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            for test_name, results in data.items():
                summary = results["summary"]
                results_chart_data.append(
                    {
                        "test_name": test_name,
                        "units": summary["units"],
                        "improvement_direction": summary[
                            "improvement_direction"
                        ],
                        "type": summary["type"],
                        "value": summary["value"],
                    }
                )
    return results_chart_data


def parse_results_chart_json(results_dir_path):
    """Parse the results-chart.json files from tests folder."""
    results_chart_data = []
    tests_path = CHROMIUMOS_RESULTS_DIR / results_dir_path / "tests"
    for test_dir in tests_path.iterdir():
        data = extract_results_chart(
            tests_path / test_dir / "results-chart.json"
        )
        if data:
            results_chart_data.extend(data)
        else:
            print(f"Warn: No results be produced in {test_dir.name}")
    return results_chart_data


def generate_results_charts_csv(
    results_dir_path,
    target_dir_path,
    os_type,
    uploader_group,
    uploader,
    tarball_name,
):
    """Generate results-chart.csv from the results directory.

    Args:
        results_dir_path: The Path object of results directory.
        target_dir_path: The Path object of target directory to store the
        results-chart.csv
        os_type: The OS type, e.g. cros
        uploader_group: The uploader group, e.g. partners
        uploader: The uploader name, i.e. ldap or partner name
        tarball_name: The tarball name

    Returns:
        The results-chart.csv path object.
    """
    csv_header = (
        "os_type,"  # The OS that CrosPTS tested on
        "board,"  # The board name
        "model,"  # The model name
        "sku,"  # The Sku, e.g. 12th_Gen_IntelR_CoreTM_i71265U_16GB
        "variant,"  # The image variant, e.g brya-release
        "milestone,"  # The image milestone, e.g. 122
        "cros_version,"  # The cros_version, e.g. 15732.0.0
        "test_name,"  # The test name e.g. cros.system.ctx_clock
        "units,"  # The units, e.g. clock
        "improvement_direction,"  # The data improve direction, e.g. down
        "type,"  # The data type, e.g. scale
        "value,"  # The data value
        "uploader,"  # The data uploader, partner name or Googler ldap
        "archive_path\n"  # The final archive log path in CNS
    )

    dut_info = parse_dut_info(results_dir_path)
    lscpu = parse_lscpu(results_dir_path)
    # The crosbolt like sku format is the combination of cpu_model and
    # memory_gb. e.g. 12th_Gen_IntelR_CoreTM_i71265U_16GB
    sku = "_".join(lscpu["cpu_model"].split() + [f"{dut_info['memory_gb']}GB"])
    lsb_release = parse_lsb_release(results_dir_path)
    results_chart_data = parse_results_chart_json(results_dir_path)

    if len(results_chart_data) == 0:
        print("Warn: No results chart data be found.")
        return ""

    # The uploaded data will be synced to archive folder in CNS.
    # See the go/crospts-data-pipeline-dd for the details.
    cns_path = f"{CNS_ROOT}/{uploader_group}/archive"
    # The archive_path is the tarball file in final storage location.
    archive_path = f"{cns_path}/{uploader}/{tarball_name}"
    results_chart_csv_path = target_dir_path / "results-chart.csv"

    with results_chart_csv_path.open("w", encoding="utf-8") as f:
        f.write(csv_header)
        for results_chart in results_chart_data:
            f.write(
                f"{os_type},{lsb_release['board']},{dut_info['model']},{sku},"
                f"{dut_info['variant']},{dut_info['milestone']},"
                f"{dut_info['os_version']},{results_chart['test_name']},"
                f"{results_chart['units']},"
                f"{results_chart['improvement_direction']},"
                f"{results_chart['type']},{results_chart['value']},"
                f"{uploader},{archive_path}\n"
            )
    return results_chart_csv_path


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


def upload_results_to_gs_bucket(
    bucket_name, uploader, credential, tarball_path, results_chart_csv_path
):
    """Upload the results to GS bucket.

    Args:
        bucket_name: The bucket name to upload the results.
        uploader: The uploader name, i.e. the partner name.
        credential: The service account credential.
        tarball_path: The Path object of the tarball.
        results_chart_csv_path: The Path object of the results-chart.csv.
    """
    client = storage.Client(credentials=credential)
    bucket = client.get_bucket(bucket_name)

    remote_path = f"crospts/archive/{uploader}/{tarball_path.name}"
    print(f"Uploading {tarball_path} to gs://{bucket_name}/{remote_path}...")
    blob = bucket.blob(remote_path)
    blob.upload_from_filename(tarball_path)

    # Extract the datetime string from the tarball_path
    tb_name = tarball_path.name.split(".")[0]
    remote_path = (
        f"crospts/results/{uploader}_{tb_name}_{results_chart_csv_path.name}"
    )
    print(
        f"Uploading {results_chart_csv_path}"
        f" to gs://{bucket_name}/{remote_path}..."
    )
    blob = bucket.blob(remote_path)
    blob.upload_from_filename(results_chart_csv_path)


def check_gcert_status(remaining=None):
    """Check the gcert status by gcertstatus command."""
    if remaining:
        return subprocess.run(
            ["gcertstatus", f"--check_remaining={remaining}"],
            check=False,
        )
    else:
        return subprocess.run(["gcertstatus"], check=False)


def validate_cns_access():
    """Validate the CNS access permissions."""

    print("Validating CNS access permissions...")
    # The crospts may take 4 hours to run the full tests. Check the gcert
    # remaining time in 5 hours to ensure the CNS accessibility.
    result = check_gcert_status(remaining="5h")
    if result.returncode != 0:
        print("Refreshing gcert...")
        subprocess.run(["gcert"], check=True)
    # Try to write an one hour TTL (Time To Live) test file to validate the
    # write permission The test file will be deleted after 1 hour.
    cns_internal = f"{CNS_ROOT}/internal/"
    cns_test_file = (
        f"{cns_internal}"
        + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        + "_test-file%ttl=1h"
    )
    try:
        subprocess.run(
            ["fileutil", "touch", cns_test_file],
            stdout=subprocess.PIPE,
            check=True,
        )
    except Exception as exe:
        raise PermissionError(
            f"No permission to write CNS path: {cns_internal}."
            "Please contact cros-core-systems-perf@google.com,"
            "if you think this is a mistake."
        ) from exe


def upload_results_to_cns(uploader, tarball_path, results_chart_csv_path):
    """Upload the results to CNS."""
    print("Checking gcert status...")
    result = check_gcert_status()
    if result.returncode != 0:
        print("Refreshing gcert...")
        subprocess.run(["gcert"], check=True)

    archive_dir = f"{CNS_ROOT}/internal/archive/{uploader}"
    remote_path = f"{archive_dir}/{tarball_path.name}"
    print(f"Uploading {tarball_path} to {remote_path}...")
    cmd = f"fileutil test -d {archive_dir} || fileutil mkdir {archive_dir}"
    subprocess.run(cmd, check=True, shell=True)
    cmd = ["fileutil", "cp", tarball_path, remote_path]
    subprocess.run(cmd, check=True)

    results_dir = f"{CNS_ROOT}/internal/results"
    # Extract the datetime string from the tarball_path
    tb_name = tarball_path.name.split(".")[0]
    remote_path = (
        f"{results_dir}/{uploader}_{tb_name}_{results_chart_csv_path.name}"
    )
    print(f"Uploading {results_chart_csv_path} to {remote_path}...")
    cmd = ["fileutil", "cp", results_chart_csv_path, remote_path]
    subprocess.run(cmd, check=True)


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
    parser.add_argument(
        "-f",
        "--flash",
        metavar="version",
        help="The release image version to flash to the DUT."
        " ex: R122 or R122-15753.29.0",
    )
    return parser.parse_args(argv)


def main(argv):
    """Command-line front end for building requires list."""
    args = parse_arguments(argv)

    if args.list:
        list_crospts_tests(args.target)
        return 0

    if args.upload:
        if args.upload == "cns":  # Upload to CNS for internal
            validate_cns_access()
        else:  # Upload to the GS bucket for partners
            credential = load_credential(args.credential)
            validate_credential(args.upload, credential, args.credential)

    if args.flash:
        flash_image(args.target, args.flash)

    results_dir_path = Path(run_crospts_tests(args.target, args.pts))
    if args.upload:
        tmp_dir_path = Path(tempfile.mkdtemp())
        with contextlib.ExitStack() as stack:
            stack.callback(shutil.rmtree, tmp_dir_path)

            uploader_group, uploader = get_uploader_info(args.upload)
            tarball_path = tar_results(results_dir_path, tmp_dir_path)
            # TODO(darrenwu): The os_type is hardcoded to cros. Add arcvm once
            # it's supported.
            results_chart_csv_path = generate_results_charts_csv(
                results_dir_path,
                tmp_dir_path,
                "cros",
                uploader_group,
                uploader,
                tarball_path.name,
            )

            if results_chart_csv_path == "":
                print("No test results be found. Skip uploading test data.")
                return -1

            if args.upload == "cns":
                upload_results_to_cns(
                    uploader, tarball_path, results_chart_csv_path
                )
            else:
                upload_results_to_gs_bucket(
                    args.upload,
                    uploader,
                    credential,
                    tarball_path,
                    results_chart_csv_path,
                )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
