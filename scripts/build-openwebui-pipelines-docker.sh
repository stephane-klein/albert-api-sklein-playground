#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/../"

docker build -t stephaneklein/openwebui-pipelines:git-7f9f957-with-included-functions .
