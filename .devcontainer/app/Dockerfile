FROM python:3.12-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        git curl ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /workspace
