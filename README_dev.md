# Dev Guide

## Python

```bash
uv venv
source .venv/bin/activate
uv sync
flask --app archivepodcast run --port 5000
```

## Frontend

Frontend tools are all handled by npm

```bash
npm install
```

### Spellcheck

```bash
npx cspell link add @cspell/dict-en-au
```

### Biome

```bash
npx @biomejs/biome format --write .
npx @biomejs/biome lint .
npx @biomejs/biome ci .
```
