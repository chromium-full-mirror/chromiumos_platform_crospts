# CrOSPTS

CrOSPTS is the performance test suite which is based on
PTS([Phoronix-Test-Suite](https://github.com/phoronix-test-suite/phoronix-test-suite)).
The PTS runs on top of PTSWorld which is the Ubuntu based chroot containing the
preloaded microbenchmark suite.

## Building PTSWorld

The PTSWorld can be build by [Dockerfile](../build/Dockerfile).

Ensure you have docker installed on your system. If not start with
[go/installdocker](http://go/installdocker).

### Build PTSWorld for x86_64 and arm64

Invoke the command to build x86_64 image.

```
docker build -t ptsworld-x86_64 build
```

Invoke the command to build arm64 image.

```
docker build -t ptsworld-arm64 build --build-arg ARCH=arm64v8/
```

## Upload the PTSWorld to gs bucket

The PTSWorld is split into two images:

- Base image: The base Ubuntu chroot image.
- PTS data image: The preinstalled PTS data which is located in
  `/var/lib/phoronix-test-suite` in chroot.

The PTSworld images are stored in
[gs://chromiumos-test-asset-public/tast/cros/crospts/](https://pantheon.corp.google.com/storage/browser/chromiumos-test-assets-public/tast/cros/crospts).

Ensure you have gsutil installed on your system. If not start with [gsutil
install](https://cloud.google.com/storage/docs/gsutil_install).

Invoke the command to upload the x86_64 PTSworld images:

```
cd <cros>/src/platform/crospts/tools
./extract_docker_image.py \
  --docker-image ptsworld-x86_64 \
  --base-img base-x86_64.img \
  --pts-img pts-data-x86_64.img
```

Invoke the command to upload the arm64 PTSworld images:

```
cd <cros>/src/platform/crospts/tools
./extract_docker_image.py \
  --docker-image ptsworld-arm64 \
  --base-img base-arm64.img \
  --pts-img pts-data-arm64.img
```
