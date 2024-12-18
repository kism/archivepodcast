# Dev Guide

## Python Setup

```bash
uv venv
source .venv/bin/activate
uv sync
flask --app archivepodcast run --port 5000
```

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

## Frontend

Frontend tools are all handled by npm

```bash
nvm use 22
npm install
```

### Spellcheck

```bash
npx cspell link add @cspell/dict-en-au
```

### Biome (JS Lint, Format)

```bash
npx @biomejs/biome format --write .
npx @biomejs/biome lint .
npx @biomejs/biome ci .
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
