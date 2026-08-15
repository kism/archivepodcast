#!/usr/bin/env bun
// Confirms every @font-face declared in main.css actually loads in a real browser.
// Usage: bun scripts/check_fonts.mjs [baseUrl]  (baseUrl defaults to http://localhost:5100)
// Requires a running webserver and: bunx playwright install --with-deps chromium

import { chromium } from "playwright";

// Keep in sync with the @font-face rules in archivepodcast/static/main.css
const FONT_SPECS = [
  '500 16px "Fira Code"',
  '600 16px "Fira Code"',
  '700 16px "Fira Code"',
  '500 16px "Noto Sans Display"',
  'italic 500 16px "Noto Sans Display"',
];

const baseUrl = process.argv[2] || "http://localhost:5100";

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.goto(`${baseUrl}/index.html`, { waitUntil: "load" });

  const results = await page.evaluate(async (specs) => {
    await document.fonts.ready;
    const out = [];
    for (const spec of specs) {
      try {
        await document.fonts.load(spec);
        out.push({ spec, checked: document.fonts.check(spec) });
      } catch (error) {
        out.push({ spec, checked: false, error: String(error) });
      }
    }
    return out;
  }, FONT_SPECS);

  const failures = results.filter((result) => !result.checked);

  for (const result of results) {
    const status = result.checked ? "OK" : "FAILED";
    console.log(`[${status}] ${result.spec}${result.error ? ` -- ${result.error}` : ""}`);
  }

  if (failures.length > 0) {
    console.error(`${failures.length}/${FONT_SPECS.length} font(s) failed to load`);
    process.exit(1);
  }

  console.log(`All ${FONT_SPECS.length} fonts loaded successfully`);
} finally {
  await browser.close();
}
