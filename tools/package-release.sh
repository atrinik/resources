#!/usr/bin/env bash

set -euo pipefail

if [[ $# -eq 2 ]]; then
  revision=$1
  output_directory=$2
  if [[ ! ${revision} =~ ^v([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
    echo "invalid release tag: ${revision}" >&2
    exit 1
  fi
  version=${BASH_REMATCH[1]}
elif [[ $# -eq 5 && $1 == --version && $3 == --revision ]]; then
  version=$2
  revision=$4
  output_directory=$5
  if [[ ! ${version} =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "invalid release version: ${version}" >&2
    exit 1
  fi
else
  echo "usage: $0 TAG OUTPUT_DIRECTORY" >&2
  echo "       $0 --version MAJOR.MINOR.PATCH --revision COMMIT OUTPUT_DIRECTORY" >&2
  exit 2
fi

package=atrinik-resources-${version}
mkdir -p "${output_directory}"

git cat-file -e "${revision}^{commit}"
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
  git cat-file -e "${revision}:${path}"
done
while IFS= read -r -d '' entry; do
  mode=${entry%% *}
  path=${entry#*$'\t'}
  if [[ ${mode} != 100644 ]]; then
    echo "runtime resource must be a non-executable regular file: ${path}" >&2
    exit 1
  fi
  case ${path} in
    *.jpg|*.json|*/LICENSE) ;;
    *)
      echo "unsupported runtime resource type: ${path}" >&2
      exit 1
      ;;
  esac
done < <(git ls-tree -r -z "${revision}" -- "${runtime_paths[@]}")
git archive --format=tar.gz --prefix="${package}/" \
  --output="${output_directory}/${package}.tar.gz" "${revision}" -- \
  "${runtime_paths[@]}"
(
  cd "${output_directory}"
  sha256sum "${package}.tar.gz" >SHA256SUMS
)
