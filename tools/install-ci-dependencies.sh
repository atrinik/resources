#!/usr/bin/env bash
set -euo pipefail

test -n "${RUNNER_TEMP:-}"
test -n "${GITHUB_PATH:-}"
install -d "${RUNNER_TEMP}/bin"
curl --fail --silent --show-error --location \
  https://github.com/rhysd/actionlint/releases/download/v1.7.9/actionlint_1.7.9_linux_amd64.tar.gz \
  --output "${RUNNER_TEMP}/actionlint.tar.gz"
printf '%s  %s\n' 233b280d05e100837f4af1433c7b40a5dcb306e3aa68fb4f17f8a7f45a7df7b4 \
  "${RUNNER_TEMP}/actionlint.tar.gz" | sha256sum --check --strict
tar -xzf "${RUNNER_TEMP}/actionlint.tar.gz" -C "${RUNNER_TEMP}/bin" actionlint
echo "${RUNNER_TEMP}/bin" >>"${GITHUB_PATH}"
