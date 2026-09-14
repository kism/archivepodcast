#!/usr/bin/env bash

MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo_magenta() {
    echo
    echo -e "--- ${MAGENTA}$1${NC} ---"
}

echo_magenta "Running pytest with coverage"
coverage run

echo_magenta "Coverage report"
coverage report

echo_magenta "Coverage HTML report"
coverage html

echo 'python -m http.server -d htmlcov'
