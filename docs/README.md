# CrosPTS - ChromeOS Performance Test Suite

CrosPTS is a microbenchmark performance test suite based on the [Phoronix Test
Suite](https://github.com/phoronix-test-suite/phoronix-test-suite). The Phoronix
Test Suite runs in the PTSWorld, which is an Ubuntu based chroot environment
contains the required runtime packages.

## Run the CrosTPS microbenchmark tests
CrosPTS provides a test runner script [run_crospts.py](../tools/run_crospts.py),
to run the tests and upload the data to cloud storage. This script is a wrapper
script to run the CrosPST tast tests.

### Prerequisites
- Create the [ChromiumOS
  chroot](https://chromium.googlesource.com/chromiumos/docs/+/HEAD/developer_guide.md#Create-a-chroot).
- Install
  [depot_tools](https://commondatastorage.googleapis.com/chrome-infra-docs/flat/depot_tools/docs/html/depot_tools_tutorial.html#_setting_up)

If you are a chromiumos developer you are probably already set up.

### Set up the DUT for running the run_crospts.py
Make sure:
- You can `ssh ${dut_host}` without typing password.
- Your DUT has access to the internet.

Where `${dut_host}` is the ssh target.

### List CrosPTS microbenchmarks
```
~/chromiumos/src/platform/crospts/tools/run_crospts.py -l ${dut_host}
```

The listed microbenchmakrs depend on the CPU architecture. It prints the only
supported architecture for the microbenchmark tests if any.

Example:
```
The microbenchmarks of CrosPTS:
   ...
   ctxclock    (x86 only)
   mutex       (x86 only)
```

### Run the CrosPTS microbenchmarks
```
~/chromiumos/src/platform/crospts/tools/run_crospts.py -p ${tests} ${dut_host}
```

Where the `${tests}` is the test(s) to be run, with comma-separated if multiple,
e.g. ctxclock,mutex. Or `all` for run all the tests.

This command calls `cros_sdk tast run` with CrosPTS tast pattern
`crospts.PerfSuite.{test}`. Once the tests complete, it prints the test results
and logs location.

Example:
```
2024-02-21T09:17:20.364461Z --------------------------------------------------------------------------------
2024-02-21T09:17:20.364498Z crospts.PerfSuite.ctxclock_cros_x86 [ PASS ]
2024-02-21T09:17:20.364509Z --------------------------------------------------------------------------------
2024-02-21T09:17:20.364521Z Results saved to /tmp/tast/results/20240221-171232
```

The printed `Results saved to` location is in chromiumos chroot. You can find
the results logs in your host machine folder
`~/chromiumos/out/tmp/tast/results/${date-time}/tests/crospts.PerfSuite.${test}/`.

The microbenchmark test scores are stored in `results-chart.json`, which located
in results folder for each test, e.g.
`~/chromiumos/out/tmp/tast/results/20240221-171232/tests/crospts.PerfSuite.ctxclock_cros_x86/results-chart.json`.

### Flash ChromeOS image prior test run
You can specify the ChromeOS image version to be tested. The script will call
[fflash](https://source.chromium.org/chromiumos/chromiumos/codesearch/+/main:src/platform/dev/contrib/fflash/README.md)
to flash image prior the test runs.

```
~/chromiumos/src/platform/crospts/tools/run_crospts.py -f ${version} -p ${tests} ${dut_host}
```

Where the `${version}` is the ChormeOS release image version, e.g. R122 or
R122-15753.29.0.

### Upload the CrosPTS test results
Uploading results function is only available for Googlers and partners. The
uploaded results will be periodically synced to [CrosPTS
dashboard](go/crospts-dash). The data will be synced every 1 hour.

#### Partners
Partners should have already set up the GCS bucket. See the [CPCon
doc](https://chromeos.google.com/partner/dlm/docs/infrastructure/upload-test-that-results-to-cpcon.html)
for the GSC bucket set up.

Please download the **service_account.json** for accessing the GCS bucket.

```
~/chromiumos/src/platform/crospts/tools/run_crospts.py -p ${tests} -u ${bucket_name} -c ${credential} ${dut_host}
```

Where the `${bucket_name}` is the GCS bucket name for your team. The
`${credential}` is the **service_accoun.json** for your GCS bucket.


#### Googlers

The results upload storage for Googlers is CNS.

```
~/chromiumos/src/platform/crospts/tools/run_crospts.py -p ${tests} -u cns ${dut_host}
```

## Build PTSWorld
See the [build_ptsworld.md](../docs/build_ptsworld.md).

## Related code

CrosPTS tast test code: [crospts tast
bundle](https://source.chromium.org/chromiumos/chromiumos/codesearch/+/main:src/platform/tast-tests/src/go.chromium.org/tast-tests/cros/local/bundles/cros/crospts/)


## Bugs & Feedback
- File a bug in [issue
  tracker](https://issuetracker.google.com/issues?q=status:open%20componentid:167279%20hotlistid:5378880&s=created_time:desc).
- Contact `cros-core-systems-perf@google.com` for questions.
