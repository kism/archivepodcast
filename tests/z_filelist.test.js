// @vitest-environment happy-dom
import { beforeEach, describe, expect, test } from "vitest";
import { addFileToStructure, showCurrentDirectory, showJSDivs } from "../archivepodcast/static/filelist.js";

beforeEach(() => {
  document.body.innerHTML = `
    <div id="file_list">
      <a href="/test/path">test/path</a>
    </div>
    <div id="file_list_js"></div>
    <div id="breadcrumb_js"></div>
  `;
  addFileToStructure("https://cdn.vitest.internal/content/vitest/test.mp3", "/content/vitest/test.mp3");
  showJSDivs();
});

describe("Directory Navigation", () => {
  describe("directory content display", () => {
    test.each([
      {
        in_hash: "#/content/vitest",
        expected_html: `<li>📂 <a href="#/content/">..</a></li><li>💾 <a href="https://cdn.vitest.internal/content/vitest/test.mp3">test.mp3</a></li>`,
      },
      {
        in_hash: "#/content",
        expected_html: `<li>📂 <a href="#/">..</a></li><li>📂 <a href="#/content/vitest/">vitest/</a></li>`,
      },
      {
        in_hash: "#/content/",
        expected_html: `<li>📂 <a href="#/">..</a></li><li>📂 <a href="#/content/vitest/">vitest/</a></li>`,
      },
    ])("displays correct content for path: $in_hash", ({ in_hash, expected_html }) => {
      window.location.hash = in_hash;
      const fileListJSDiv = document.getElementById("file_list_js");
      expect(fileListJSDiv.style.display).toBe("block");
      showCurrentDirectory();
      expect(fileListJSDiv.innerHTML).toBe(expected_html);
    });
  });

  test.each([["#"], ["#/"], [""]])("displays root directory content for path: %s", (in_hash) => {
    window.location.hash = in_hash;
    const fileListJSDiv = document.getElementById("file_list_js");
    showCurrentDirectory();
    expect(fileListJSDiv.innerHTML).toBe(`<li>📂 <a href="#/content/">content/</a></li>`);
  });

  test("initializes file list on page load", () => {
    document.dispatchEvent(new Event("DOMContentLoaded"));
    const fileListDiv = document.getElementById("file_list");
    expect(fileListDiv.style.display).toBe("none");
    const fileListJSDiv = document.getElementById("file_list_js");
    expect(fileListJSDiv.innerHTML).toBe(`<li>📂 <a href="#/content/">content/</a></li>`);
  });

  test("displays error for invalid directory path", () => {
    window.location.hash = "#/content/vitest/bananas";
    const fileListJSDiv = document.getElementById("file_list_js");
    expect(fileListJSDiv.style.display).toBe("block");
    showCurrentDirectory();
    expect(fileListJSDiv.innerHTML).toBe("<li>Invalid path: /content/vitest/bananas</li>");
  });
});
