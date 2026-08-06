#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 TAG OUTPUT_DIRECTORY" >&2
  exit 2
fi

tag=$1
output_directory=$2
if [[ ! ${tag} =~ ^v([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
  echo "invalid release tag: ${tag}" >&2
  exit 1
fi

version=${BASH_REMATCH[1]}
package=atrinik-resources-${version}
mkdir -p "${output_directory}"

git cat-file -e "${tag}^{commit}"
mapfile -t runtime_paths <runtime-paths.txt
if [[ ${#runtime_paths[@]} -eq 0 ]]; then
  echo "runtime-paths.txt must list at least one path" >&2
  exit 1
fi
declare -A seen_paths=()
for path in "${runtime_paths[@]}"; do
  if [[ -z ${path} || ${path} == /* || ${path} == */ || ${path} == *//* ||
    ${path} =~ (^|/)\.\.?(/|$) || -n ${seen_paths[${path}]+present} ]]; then
    echo "invalid runtime resource path: ${path}" >&2
    exit 1
  fi
  seen_paths[${path}]=1
  git cat-file -e "${tag}:${path}"
done
git archive --format=tar.gz --prefix="${package}/" \
  --output="${output_directory}/${package}.tar.gz" "${tag}" -- \
  "${runtime_paths[@]}"
(
  cd "${output_directory}"
  sha256sum "${package}.tar.gz" >SHA256SUMS
)
