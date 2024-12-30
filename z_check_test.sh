#!/usr/bin/env bash

MAGENTA='\033[0;35m'
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo_magenta() {
    echo
    echo -e "--- ${MAGENTA}$1${NC} ---"
}

check_return() {
    if [ "$1" -ne 0 ]; then
        echo -e "${RED}Failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}Passed${NC}"
}

echo_magenta "Pytest"
pytest -q --show-capture=no >/dev/null
check_return $?

echo_magenta "Vitest"
npx vitest run --coverage >/dev/null
check_return $?

echo_magenta "Ruff format"
ruff format .
check_return $?

echo_magenta "Ruff check"
ruff check . --fix
check_return $?

echo_magenta "Mypy"
mypy .
check_return $?

echo_magenta "cspell"
npx cspell .
check_return $?

echo_magenta "Markdownlint"
npx markdownlint-cli --fix *.md
check_return $?

echo_magenta "Biome format"
npx @biomejs/biome format --write .
check_return $?

echo_magenta "Biome lint"
npx @biomejs/biome lint .
check_return $?

echo_magenta "Biome check"
npx @biomejs/biome check --fix .
check_return $?
