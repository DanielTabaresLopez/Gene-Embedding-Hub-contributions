#!/usr/bin/env bash

set -euo pipefail

resource="${1:?Usage: exchange_hf_oidc_token.sh <resource>}"

: "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:?Missing GitHub OIDC request token}"
: "${ACTIONS_ID_TOKEN_REQUEST_URL:?Missing GitHub OIDC request URL}"

oidc_token="$(
  curl \
    --fail \
    --silent \
    --show-error \
    -H "Authorization: Bearer ${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" \
    "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=https%3A%2F%2Fhuggingface.co" \
  | jq -er '.value'
)"

jq -n \
  --arg subject_token "$oidc_token" \
  --arg resource "$resource" \
  '{
    grant_type:
      "urn:ietf:params:oauth:grant-type:token-exchange",
    subject_token_type:
      "urn:ietf:params:oauth:token-type:id_token",
    subject_token: $subject_token,
    resource: $resource
  }' \
| curl \
    --fail-with-body \
    --silent \
    --show-error \
    -X POST \
    -H "Content-Type: application/json" \
    --data-binary @- \
    https://huggingface.co/oauth/token \
| jq -er '.access_token'
