#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/../"

#docker push stephaneklein/openwebui-pipelines:latest
docker push stephaneklein/openwebui-pipelines:git-7f9f957-with-included-functions
