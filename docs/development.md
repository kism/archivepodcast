# Dev Guide

## Setup

### Python Setup

```bash
uv venv
source .venv/bin/activate
uv sync
flask --app archivepodcast run --port 5100
```

If you wish to upgrade packages

```bash
uv sync --upgrade
```

### Javascript/Spellcheck/Frontend Setup

Frontend tools are all handled by npm

```bash
nvm use 22
npm install
```

If you wish to upgrade packages

```bash
npm upgrade
```

Extra setup dictionaries for spellcheck

```bash
npx cspell link add @cspell/dict-en-au
```

## Lint, Format, Type Check, Test

### Ruff (Python Lint, Format)

```bash
ruff format .
ruff check .
ruff check . --fix
```

### MyPy (Python Type Check)

```bash
mypy .
```

### Pytest (Python Test)

```bash
pytest
```

To get coverage report, open the `htmlcov` folder in a browser or the vscode live server.

### Spellcheck

Run

```bash
npx cspell .
```

### Markdown lint

Run

```bash
npx markdownlint-cli --fix *.md
```

### Biome (JS Lint, Format)

```bash
npx @biomejs/biome format --write .
npx @biomejs/biome lint .
npx @biomejs/biome check --fix .
```

### Vitest (JS Test)

Run persistent test watcher

```bash
npx vitest --disable-console-intercept
npx vitest --coverage --disable-console-intercept
npx vitest --ui --coverage
```

To get coverage report, open the `htmlcov_js` folder in a browser or the vscode live server, or run vitest in ui mode.

Run once

```bash
npx vitest run
npx vitest run --coverage
```
