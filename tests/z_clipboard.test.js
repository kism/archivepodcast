// @vitest-environment happy-dom

import { describe, expect, test } from "vitest";

import { grabToClipboard, resetText } from "../archivepodcast/static/clipboard.js";

describe("Clipboard Operations", () => {
  test("throws error when copying from non-existent element", () => {
    const button_name = "non_existent_button";
    expect(() => grabToClipboard(button_name)).toThrow();
  });

  test("copies URL to clipboard and updates button text", () => {
    const rss_url = "http://localhost:5100/rss/test";
    const button_name = "button_name";
    const copyText = document.createElement("input");
    copyText.id = button_name;
    copyText.value = rss_url;
    document.body.appendChild(copyText);

    const button = document.createElement("button");
    button.id = `${button_name}_button`;
    document.body.appendChild(button);

    grabToClipboard(button_name);

    expect(copyText.value).toBe(rss_url);
    expect(document.getElementById(`${button_name}_button`).innerHTML).toBe("Copied!");
  });

  test("resets button text after copying", () => {
    const button_name = "button_name";
    const button = document.createElement("button");
    button.id = `${button_name}_button`;
    document.body.appendChild(button);

    document.getElementById(`${button_name}_button`).innerHTML = "Copied!";
    resetText(button_name);
    expect(document.getElementById(`${button_name}_button`).innerHTML).toBe("Copy URL");
  });
});
