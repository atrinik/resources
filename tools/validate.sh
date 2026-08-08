#!/usr/bin/env bash

set -euo pipefail

repository=$(git rev-parse --show-toplevel)
cd "${repository}"

python3 -m compileall -q tools
tools/resource-inventory.py validate
jq empty catalog/*.json catalog/allowlists/*.json

bash -n tools/*.sh
shellcheck tools/*.sh
actionlint

release_workspace=$(mktemp -d /tmp/atrinik-resources-release.XXXXXX)
first=${release_workspace}/first
second=${release_workspace}/second
trap 'rm -rf -- "${release_workspace}"' EXIT
tools/package-release.sh --version 0.0.0 --revision HEAD "${first}"
tools/package-release.sh --version 0.0.0 --revision HEAD "${second}"
cmp "${first}/atrinik-resources-0.0.0.tar.gz" \
  "${second}/atrinik-resources-0.0.0.tar.gz"
cmp "${first}/RELEASE.json" "${second}/RELEASE.json"
cmp "${first}/SHA256SUMS" "${second}/SHA256SUMS"
(
  cd "${first}"
  sha256sum --check SHA256SUMS
)
jq -e \
  --arg revision "$(git rev-parse HEAD)" \
  --arg catalog_sha256 "$(git show HEAD:catalog/resources.json | sha256sum | cut -d' ' -f1)" \
  '.schema_version == 1 and .version == "0.0.0" and
    .requested_revision == "HEAD" and .resolved_revision == $revision and
    .archive == "atrinik-resources-0.0.0.tar.gz" and
    .catalog_sha256 == $catalog_sha256' \
  "${first}/RELEASE.json" >/dev/null
if tools/package-release.sh --version 0.0.0 --revision HEAD "${first}" \
  >"${first}/no-clobber.stdout" 2>"${first}/no-clobber.stderr"; then
  echo "release packaging overwrote an existing output" >&2
  exit 1
fi
grep -Fx "release output already exists: ${first}" "${first}/no-clobber.stderr" >/dev/null
tar -tzf "${first}/atrinik-resources-0.0.0.tar.gz" >"${first}/contents.txt"
grep -q '/paintings/LICENSE$' "${first}/contents.txt"
grep -q '/catalog/resources.json$' "${first}/contents.txt"
grep -q '/catalog/allowlists/renderer-test.json$' "${first}/contents.txt"
if grep -Eq '/(inventory|tools|\.github|README.md|CONTRIBUTING.md)(/|$)' \
  "${first}/contents.txt"; then
  echo "release contains a development-only path" >&2
  exit 1
fi

git diff --check
