// @vitest-environment happy-dom

import { expect, test } from "vitest";

import { grabToClipboard, resetText } from "../archivepodcast/static/clipboard.js";

test("grabToClipboard with non-existent element", () => {
  const button_name = "non_existent_button";
  expect(() => grabToClipboard(button_name)).toThrow();
});

test("grabToClipboard with value", () => {
  const rss_url = "http://localhost:5000/rss/test";
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

test("resetText", () => {
  const button_name = "button_name";
  const button = document.createElement("button");
  button.id = `${button_name}_button`;
  document.body.appendChild(button);

  document.getElementById(`${button_name}_button`).innerHTML = "Copied!";
  resetText(button_name);
  expect(document.getElementById(`${button_name}_button`).innerHTML).toBe("Copy URL");
});
