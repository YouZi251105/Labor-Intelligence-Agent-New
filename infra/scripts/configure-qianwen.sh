#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env.validation"
MODEL="${QIANWEN_MODEL:-qwen-plus}"

if [[ ! -t 0 ]]; then
  echo "This command requires an interactive terminal." >&2
  exit 1
fi

echo "Qwen API Key input is hidden and is not written to shell history."
read -r -s -p "Paste QIANWEN_API_KEY: " API_KEY
echo

if [[ -z "${API_KEY}" ]]; then
  echo "No API key entered." >&2
  exit 1
fi

if [[ "${API_KEY}" == *"请替换"* || "${API_KEY}" == *"你的"* ]]; then
  echo "The placeholder text was entered instead of a real API key." >&2
  unset API_KEY
  exit 1
fi

umask 077
printf 'QIANWEN_API_KEY=%s\nQIANWEN_MODEL=%s\n' "${API_KEY}" "${MODEL}" > "${ENV_FILE}"
chmod 600 "${ENV_FILE}"
unset API_KEY

echo "Configuration written to ${ENV_FILE}"
echo "Restarting the validation backend..."

sudo -E docker compose \
  -f "${PROJECT_ROOT}/infra/validation/docker-compose.yml" \
  -p labor-stage4-validation \
  up -d --force-recreate backend

sudo docker compose \
  -f "${PROJECT_ROOT}/infra/validation/docker-compose.yml" \
  -p labor-stage4-validation \
  exec -T backend \
  python -c "from app.core.config import get_settings; s=get_settings(); print('KEY_LOADED=', bool(s.qianwen_api_key)); print('PLACEHOLDER=', '你的' in s.qianwen_api_key); print('MODEL=', s.qianwen_model)"
