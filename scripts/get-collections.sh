#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/../"

curl -s https://albert.api.etalab.gouv.fr/v1/collections?limit=100 \
    -H "Authorization: Bearer ${ALBERT_OPENAI_API_KEY}" | jq
