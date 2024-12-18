/// <reference types="vitest" />
import { defineConfig } from "vite";

export default defineConfig({
  test: {
    include: ["tests/*.js"],
    coverage: {
      provider: "v8",
      include: ["archivepodcast/static/*.js"],
      reportsDirectory: "htmlcov_js",
    },
  },
});
