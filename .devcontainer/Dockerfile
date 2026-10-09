# Development container (ADR-0001). Same OS and Python as the runtime image (Debian Trixie,
# Python 3.13, python3-libgpiod), plus the build tools: uv, Node 22, make.
FROM mcr.microsoft.com/devcontainers/base:trixie

RUN apt-get update \
 && apt-get install -y --no-install-recommends make python3 python3-venv python3-dev python3-libgpiod \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /uvx /usr/local/bin/

COPY --from=node:22-trixie-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-trixie-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# uv uses Debian's Python 3.13, exactly as in the runtime image; it never downloads its own.
ENV UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy

# Claude Code keeps its login and settings in a named volume (see devcontainer.json); create the
# directory here so the volume is owned by the vscode user.
RUN mkdir -p /home/vscode/.claude && chown vscode:vscode /home/vscode/.claude
