# Ubuntu environment for this project.
# Windows-only project? Delete this file. Add Windows Sandbox instructions to docs/ instead.
#
# Build: docker build -t repo-template .
# Run:   docker run --rm -it -v "$PWD":/work repo-template
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash ca-certificates curl git python3 util-linux \
    && rm -rf /var/lib/apt/lists/*

# Run as a normal user. Do not run project code as root.
RUN useradd --create-home --shell /bin/bash dev
USER dev
WORKDIR /work

# Git refuses a mounted repository that another user owns.
RUN git config --global --add safe.directory /work

CMD ["bash"]
