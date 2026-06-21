#!/usr/bin/env bash

set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="${1:-}"

if [[ ! "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Usage: $0 <version>" >&2
  echo "Example: $0 3.20.0" >&2
  exit 2
fi

tag="v${version}"
base_url="https://raw.githubusercontent.com/andrewgioia/keyrune/${tag}"
temp_dir="$(mktemp -d)"
trap 'rm -rf "${temp_dir}"' EXIT

echo "Downloading Keyrune ${version}..."
curl --fail --silent --show-error --location --retry 3 \
  --connect-timeout 10 --max-time 60 \
  "${base_url}/css/keyrune.css" -o "${temp_dir}/keyrune.css"
curl --fail --silent --show-error --location --retry 3 \
  --connect-timeout 10 --max-time 60 \
  "${base_url}/fonts/keyrune.woff2" -o "${temp_dir}/keyrune.woff2"
curl --fail --silent --show-error --location --retry 3 \
  --connect-timeout 10 --max-time 60 \
  "${base_url}/LICENSE.md" -o "${temp_dir}/LICENSE.md"

# The module only ships WOFF2, so remove references to the other font formats
# from Keyrune's stylesheet and let text render while the font is loading.
awk -v version="${version}" '
  /^  src: .+keyrune\.woff2/ {
    print "  src: url(\047../fonts/keyrune.woff2?v=" version "\047) format(\047woff2\047);"
    next
  }
  /^  src: url\(.+keyrune\.eot/ { next }
  /^  font-style: normal;/ {
    print
    print "  font-display: swap;"
    next
  }
  { print }
' "${temp_dir}/keyrune.css" > "${temp_dir}/keyrune.processed.css"

install -m 0644 "${temp_dir}/keyrune.processed.css" \
  "${root_dir}/static/keyrune/css/keyrune.css"
install -m 0644 "${temp_dir}/keyrune.woff2" \
  "${root_dir}/static/keyrune/fonts/keyrune.woff2"
install -m 0644 "${temp_dir}/LICENSE.md" \
  "${root_dir}/static/keyrune/LICENSE.md"
printf '%s\n' "${version}" > "${root_dir}/KEYRUNE_VERSION"

echo "Updated vendored Keyrune assets to ${version}."
