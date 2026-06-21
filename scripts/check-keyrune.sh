#!/usr/bin/env bash

set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version_file="${root_dir}/KEYRUNE_VERSION"
strict=false

usage() {
  echo "Usage: $0 [--strict]" >&2
}

case "${1:-}" in
  "") ;;
  --strict) strict=true ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage
    exit 2
    ;;
esac

if [[ ! -f "${version_file}" ]]; then
  echo "Keyrune check: missing ${version_file}" >&2
  exit 1
fi

pinned_version="$(tr -d '[:space:]' < "${version_file}")"
release_json="$(curl --fail --silent --show-error --location --retry 3 \
  --connect-timeout 10 --max-time 60 \
  --header 'Accept: application/vnd.github+json' \
  --header 'X-GitHub-Api-Version: 2022-11-28' \
  'https://api.github.com/repos/andrewgioia/keyrune/releases/latest')"
latest_version="$(printf '%s\n' "${release_json}" | sed -nE 's/.*"tag_name":[[:space:]]*"v?([^"]+)".*/\1/p' | head -n 1)"

if [[ -z "${latest_version}" ]]; then
  echo "Keyrune check: could not determine the latest release" >&2
  exit 1
fi

if [[ "${pinned_version}" == "${latest_version}" ]]; then
  echo "Keyrune ${pinned_version} is current."
  exit 0
fi

echo "Keyrune ${latest_version} is available; this module vendors ${pinned_version}." >&2
echo "Run scripts/update-keyrune.sh ${latest_version} and commit the generated changes." >&2

if [[ "${strict}" == true ]]; then
  exit 1
fi
