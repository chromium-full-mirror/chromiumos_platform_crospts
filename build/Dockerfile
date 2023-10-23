 # Copyright 2023 The ChromiumOS Authors
 # Use of this source code is governed by a BSD-style license that can be
 # found in the LICENSE file.

FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    unzip php-cli apt-utils mesa-utils php-xml git-core apt-file sudo wget \
    python3 linux-libc-dev
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
    -r ${REQUIRES_LIST} -t /var/lib/${PTS}/installed-tests

CMD ["${PTS_ROOT}/phoronix-test-suite", "shell"]
