#!/usr/bin/env bash

set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version_file="${KEYRUNE_VERSION_FILE:-${root_dir}/KEYRUNE_VERSION}"
github_release_url="${KEYRUNE_GITHUB_RELEASE_URL:-https://api.github.com/repos/andrewgioia/keyrune/releases/latest}"
npm_release_url="${KEYRUNE_NPM_RELEASE_URL:-https://registry.npmjs.org/keyrune/latest}"
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

fetch_github_version() {
  local release_json
  release_json="$(curl --fail --silent --location --retry 2 --retry-all-errors \
    --retry-delay 1 --retry-max-time 30 --connect-timeout 5 --max-time 20 \
    --header 'Accept: application/vnd.github+json' \
    --header 'X-GitHub-Api-Version: 2022-11-28' \
    "${github_release_url}")" || return 1
  printf '%s\n' "${release_json}" | sed -nE 's/.*"tag_name":[[:space:]]*"v?([^"]+)".*/\1/p' | head -n 1
}

fetch_npm_version() {
  local release_json
  release_json="$(curl --fail --silent --location --retry 2 --retry-all-errors \
    --retry-delay 1 --retry-max-time 30 --connect-timeout 5 --max-time 20 \
    "${npm_release_url}")" || return 1
  printf '%s\n' "${release_json}" | sed -nE 's/.*"version":[[:space:]]*"v?([^"]+)".*/\1/p' | head -n 1
}

latest_version=""
release_source=""
if latest_version="$(fetch_npm_version)" && [[ -n "${latest_version}" ]]; then
  release_source="npm"
elif latest_version="$(fetch_github_version)" && [[ -n "${latest_version}" ]]; then
  release_source="GitHub"
fi

if [[ -z "${latest_version}" ]]; then
  echo "Keyrune check: could not reach npm or GitHub; skipping the version check." >&2
  exit 0
fi

if [[ "${pinned_version}" == "${latest_version}" ]]; then
  echo "Keyrune ${pinned_version} is current (${release_source})."
  exit 0
fi

echo "Keyrune ${latest_version} is available; this module vendors ${pinned_version}." >&2
echo "Run scripts/update-keyrune.sh ${latest_version} and commit the generated changes." >&2

if [[ "${strict}" == true ]]; then
  exit 1
fi
