// @vitest-environment happy-dom

import { expect, test } from 'vitest'

import { generateBreadcrumbHtml } from '../archivepodcast/static/filelist.js'

test('generateBreadcrumbHtml with path', () => {
    const current_path = "/test/path"
    const expected_html = `<a href="#/">File list</a> / <a href="#/test/">test</a> / <a href="#/test/path/">path</a> / `
    expect(generateBreadcrumbHtml(current_path)).toBe(expected_html)
}   )

test('generateBreadcrumbHtml with empty path', () => {
    const current_path = ""
    const expected_html = `<a href="#/">File list</a> / `
    expect(generateBreadcrumbHtml(current_path)).toBe(expected_html)
})

test('generateBreadcrumbHtml with slash', () => {
    const current_path = "/"
    const expected_html = `<a href="#/">File list</a> / `
    expect(generateBreadcrumbHtml(current_path)).toBe(expected_html)
})
