#!/usr/bin/env bash

MAGENTA='\033[0;35m'
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo_magenta() {
    echo
    echo -e "--- ${MAGENTA}$1${NC} ---"
}

if [ "$(dirname "$0")" == "." ]; then
    echo "Changing directory to the project directory"
    cd ..
fi

check_return() {
    if [ "$1" -ne 0 ]; then
        echo -e "${RED}Failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}Passed${NC}"
}

echo "Running code checks locally"

# Prerequisites
uv sync --all-extras

echo "Npm version: $(npm --version), Expected: 11"
npm install

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
mypy
check_return $?

echo_magenta "ty"
ty check .
check_return $?

echo_magenta "cspell"
npm run spell
check_return $?

echo_magenta "Markdownlint"
npm run check_markdown
check_return $?

echo_magenta "Biome format"
npm run format
check_return $?

echo_magenta "Biome lint"
npm run lint
check_return $?

echo_magenta "Biome check"
npm run check
check_return $?

echo_magenta "html-validate"
mkdir -p instance/web/rss/
cp -f scripts/config/rss-ci.rss instance/web/rss/test
.venv/bin/python -m archivepodcast --config scripts/config/config-ci.json >/dev/null 2>&1
npx html-validate instance/web/*.html
check_return $?
