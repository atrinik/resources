#!/usr/bin/env bash

set -euo pipefail

repository=$(git rev-parse --show-toplevel)
cd "${repository}"

python3 -m compileall -q tools
tools/resource-inventory.py validate
jq empty catalog/*.json catalog/allowlists/*.json
while IFS= read -r row; do
  jq -e 'type == "object"' >/dev/null <<<"${row}"
done < <(cat inventory/*.jsonl)

bash -n tools/*.sh
shellcheck tools/*.sh
actionlint

first=$(mktemp -d /tmp/atrinik-resources-release-first.XXXXXX)
second=$(mktemp -d /tmp/atrinik-resources-release-second.XXXXXX)
trap 'rm -rf -- "${first}" "${second}"' EXIT
tools/package-release.sh --version 0.0.0 --revision HEAD "${first}"
tools/package-release.sh --version 0.0.0 --revision HEAD "${second}"
cmp "${first}/atrinik-resources-0.0.0.tar.gz" \
  "${second}/atrinik-resources-0.0.0.tar.gz"
(
  cd "${first}"
  sha256sum --check SHA256SUMS
)
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
