FROM ubuntu:24.04

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates file git libimage-exiftool-perl pandoc python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY requirements.txt .
# server.py uses the FastMCP API from MCP 1.x.
RUN python3 -m venv /opt/venv \
    && python3 -m pip install --no-cache-dir -r requirements.txt 'mcp<2' \
    && useradd --create-home --shell /bin/bash dev

COPY . .
USER dev
CMD ["python3", "server.py"]
