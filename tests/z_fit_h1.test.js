// @vitest-environment happy-dom
import { beforeEach, describe, expect, test } from "vitest";
import { fitTextToContainer } from "../archivepodcast/static/fit_h1.js";

beforeEach(() => {
    document.body.innerHTML = `
        <h1>Test</h1>
    `;
    });


describe("fitTextToContainer", () => {
    test("fitTextToContainer", () => {
        const h1 = document.querySelector("h1");
        fitTextToContainer();

    });
} );
