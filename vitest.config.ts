/// <reference types="vitest" />
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/*.js"],
    coverage: {
      provider: "v8",
      include: ["src/archivepodcast/static/*.js"],
      reportsDirectory: "htmlcov_js",
    },
  },
});
