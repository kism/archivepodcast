#!/usr/bin/env bash

MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo_magenta() {
    echo
    echo -e "--- ${MAGENTA}$1${NC} ---"
}

# curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin v0.74.0

echo_magenta "Trivy config scan"
trivy config --ignorefile ./.trivyignore.yaml .
