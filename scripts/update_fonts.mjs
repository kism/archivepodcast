#!/usr/bin/env bun
// Copies the latin-subset woff2 files this project uses out of the installed
// @fontsource packages into src/archivepodcast/static/fonts, keeping fontsource's
// own filenames. Run `bun install` first, then `bun run update_fonts` to pick
// up new font versions, weights, or styles.

import { copyFileSync, existsSync, mkdirSync, readdirSync, unlinkSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const FONTS_DIR = join(ROOT, "src", "archivepodcast", "static", "fonts");

// Add an entry here for any weight/style this project's CSS needs.
const FONTS = [
  { package: "fira-code", weight: 500, style: "normal" },
  { package: "fira-code", weight: 600, style: "normal" },
  { package: "fira-code", weight: 700, style: "normal" },
  { package: "noto-sans-display", weight: 500, style: "normal" },
  { package: "noto-sans-display", weight: 500, style: "italic" },
];

mkdirSync(FONTS_DIR, { recursive: true });

const wanted = new Set();

for (const { package: pkg, weight, style } of FONTS) {
  const filename = `${pkg}-latin-${weight}-${style}.woff2`;
  const source = join(ROOT, "node_modules", "@fontsource", pkg, "files", filename);

  if (!existsSync(source)) {
    throw new Error(`Missing ${source} -- is @fontsource/${pkg} installed? Run 'bun install' first.`);
  }

  copyFileSync(source, join(FONTS_DIR, filename));
  wanted.add(filename);
  console.log(`Updated ${filename}`);
}

for (const existing of readdirSync(FONTS_DIR)) {
  if (!wanted.has(existing)) {
    unlinkSync(join(FONTS_DIR, existing));
    console.log(`Removed stale font: ${existing}`);
  }
}
