 # Copyright 2023 The ChromiumOS Authors
 # Use of this source code is governed by a BSD-style license that can be
 # found in the LICENSE file.

# Use param `--build-arg ARCH=arm64v8/` for docker build to build ARM image
ARG ARCH=
FROM ${ARCH}ubuntu:22.04

# When build ARM64 image on x86 system, it runs the ARM64 docker by qemu.
# But the apt-get install hits the Segmentation fault when processing libc-bin.
# The workaround is move out the libc-bin.* files and run the apt-get install.
# The libc-bin* files will be restored after apt-get install complete.
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    mkdir /tmp/backup && mv /var/lib/dpkg/info/libc-bin.* /tmp/backup && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    unzip php-cli apt-utils mesa-utils php-xml git-core apt-file sudo wget \
    python3 linux-libc-dev ; \
    mv /tmp/backup/* /var/lib/dpkg/info/
RUN apt-file update

# Download and extract the Phoronix Test Suite tarball
ENV PTS=phoronix-test-suite
# phoronix-test-suite-10.8.4.tar.gz is a copy of PTS which uploaded
# to chromeos-localmirror
RUN wget http://commondatastorage.googleapis.com/chromeos-localmirror/distfiles/phoronix-test-suite-10.8.4.tar.gz \
    -O ${PTS}.tar.gz
RUN tar -xzf ${PTS}.tar.gz -C / && rm ${PTS}.tar.gz

# Download the installed tests requires list
ENV REQUIRES_LIST=crospts-installed-tests-requires-list
ENV REQUIRES_LIST_VERSION=2023.11.06.202549
ENV REQUIRES_LIST_TARBALL=${REQUIRES_LIST}-${REQUIRES_LIST_VERSION}.tar.xz
RUN wget http://commondatastorage.googleapis.com/chromeos-localmirror/distfiles/${REQUIRES_LIST_TARBALL} \
    -O ${REQUIRES_LIST_TARBALL} && tar -xf ${REQUIRES_LIST_TARBALL} -C / && \
    rm ${REQUIRES_LIST_TARBALL}

# Install test suite config file
ENV SUITE_NAME=cros-core-performance
ENV SUITE_ROOT=/var/lib/${PTS}/test-suites/local/${SUITE_NAME}
RUN mkdir -p -m 755 ${SUITE_ROOT}
COPY ${SUITE_NAME} ${SUITE_ROOT}

# Install the test packages
ENV PTS_ROOT=/${PTS}
COPY pts_shrink.py /
RUN ${PTS_ROOT}/${PTS} openbenchmarking-refresh
# Install the suite and shrink the installed-tests based on REQUIRES_LIST
RUN ${PTS_ROOT}/${PTS} install ${SUITE_NAME} && /pts_shrink.py \
    -r ${REQUIRES_LIST} -t /var/lib/${PTS}/installed-tests && \
    rm /pts_shrink.py ${REQUIRES_LIST}

# Configure PTS to skip uploading benchmark results to OpenBenchmarking
# Configure PTS to no prompt when running PTS batch mode test, which is no user interaction by default.
RUN sed -i 's/<AllowResultUploadsToOpenBenchmarking>TRUE/<AllowResultUploadsToOpenBenchmarking>FALSE/' \
    /etc/phoronix-test-suite.xml && \
    sed -i 's/<UploadResults>TRUE/<UploadResults>FALSE/' /etc/phoronix-test-suite.xml && \
    sed -i 's/<PromptForTestIdentifier>TRUE/<PromptForTestIdentifier>FALSE/' /etc/phoronix-test-suite.xml && \
    sed -i 's/<PromptForTestDescription>TRUE/<PromptForTestDescription>FALSE/' /etc/phoronix-test-suite.xml && \
    sed -i 's/<PromptSaveName>TRUE/<PromptSaveName>FALSE/' /etc/phoronix-test-suite.xml && \
    sed -i 's/<Configured>FALSE/<Configured>TRUE/' /etc/phoronix-test-suite.xml

CMD ["${PTS_ROOT}/phoronix-test-suite", "shell"]
