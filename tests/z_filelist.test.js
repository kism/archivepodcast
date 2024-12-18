// @vitest-environment happy-dom
import { expect, test, describe, beforeEach } from 'vitest'
import { showCurrentDirectory, addFileToStructure, showJSDivs } from '../archivepodcast/static/filelist.js'

beforeEach(() => {
  document.body.innerHTML = `
    <div id="file_list">
      <a href="/test/path">test/path</a>
    </div>
    <div id="file_list_js"></div>
    <div id="breadcrumb_js"></div>
  `;
  addFileToStructure('https://cdn.vitest.internal/content/vitest/test.mp3', '/content/vitest/test.mp3');
  showJSDivs();
});

describe.each([
  {in_hash: '#/content/vitest', expected_html: `📂 <a href="#/content/">..</a><br>💾 <a href="https://cdn.vitest.internal/content/vitest/test.mp3">test.mp3</a><br>`},
  {in_hash: "#/content", expected_html: `📂 <a href="#/">..</a><br>📂 <a href="#/content/vitest/">vitest/</a><br>`},
  {in_hash: "#/content/", expected_html: `📂 <a href="#/">..</a><br>📂 <a href="#/content/vitest/">vitest/</a><br>`},
])('fileListJSDiv is displayed and populated on hash', ({in_hash, expected_html}) => {
    test(`fileListJSDiv on hash: ${in_hash}`, () => {
    window.location.hash = in_hash;
    const fileListJSDiv = document.getElementById('file_list_js');
    expect(fileListJSDiv.style.display).toBe('block');
    showCurrentDirectory();
    expect(fileListJSDiv.innerHTML).toBe(expected_html);
    })
});

test.each([
  ["#"],
  ["#/"],
  [""],
])('fileListJSDiv initial', (in_hash) => {
  window.location.hash = in_hash;
  const fileListJSDiv = document.getElementById('file_list_js');
  showCurrentDirectory();
  expect(fileListJSDiv.innerHTML).toBe(`📂 <a href="#/content/">content/</a><br>`);
});

test('DOMContentLoaded event', () => {
  document.dispatchEvent(new Event('DOMContentLoaded'));
  const fileListDiv = document.getElementById('file_list');
  expect(fileListDiv.style.display).toBe('none');
  const fileListJSDiv = document.getElementById('file_list_js');
  expect(fileListJSDiv.innerHTML).toBe(`📂 <a href="#/content/">content/</a><br>`);
})

test('fileListJSDiv invalid path', () => {
  window.location.hash = '#/content/vitest/bananas';
  const fileListJSDiv = document.getElementById('file_list_js');
  expect(fileListJSDiv.style.display).toBe('block');
  showCurrentDirectory();
  expect(fileListJSDiv.innerHTML).toBe("<li>Invalid path: /content/vitest/bananas</li>");
});
