#!/usr/bin/env bash
# Build ragops:v1 without any network access, from the WSL virtualenv that the tests were run with.
#   bash scripts/build-image-local.sh
set -euo pipefail
cd "$(dirname "$0")/.."
CTX=$HOME/ragops-ctx
rm -rf "$CTX" && mkdir -p "$CTX/api" "$CTX/indexer"
cp -r "$HOME/rahbar-venv/lib/python3.12/site-packages" "$CTX/site-packages"
# test-only packages and caches are not needed at run time
rm -rf "$CTX"/site-packages/{pytest*,_pytest,pytest_cov*,coverage*,pip,pip-*,setuptools*,pkg_resources,_distutils_hack}
find "$CTX/site-packages" -name __pycache__ -type d -prune -exec rm -rf {} +
cp -r api/app "$CTX/api/app"
cp -r indexer/pipeline "$CTX/indexer/pipeline"
cp -r ragops config eval experiments "$CTX"/
cp Dockerfile.local "$CTX/Dockerfile"
find "$CTX" -name __pycache__ -type d -prune -exec rm -rf {} +
docker build -t ragops:v1 "$CTX"
