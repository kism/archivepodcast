# Development Tools

## Python Lint and Format

```bash
ruff format .
ruff check .
ruff check . --fix
```

### Python Type Checking

```bash
ty check .
```

## Frontend Code Quality

For frontend code quality check, we use some npm packages, installed via [pnpm](https://pnpm.io/).

```bash
pnpm install
```

If you wish to upgrade packages

```bash
pnpm update
```

## Run

See the scripts in `package.json` for various commands, run via `pnpm run <script>`.
