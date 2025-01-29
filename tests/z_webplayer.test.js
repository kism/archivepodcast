// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, test, vi } from "vitest";

import {
  loadPodcast,
  playerSetCurrentEpisode,
  populateEpisodeList,
  showJSDivs,
} from "../archivepodcast/static/webplayer";

test("playerSetCurrentEpisode sets player src and episode title", () => {
  document.body.innerHTML = `
    <audio id="podcast_player"></audio>
    <div id="podcast_player_episode_name"></div>
  `;

  playerSetCurrentEpisode("http://example.com/test.mp3", "audio/mpeg", "Test Episode");

  const player = document.getElementById("podcast_player");
  const episodeTitle = document.getElementById("podcast_player_episode_name");

  expect(player.src).toBe("http://example.com/test.mp3");
  expect(player.type).toBe("audio/mpeg");
  expect(episodeTitle.textContent).toBe("Player: Test Episode");
});

test("loadPodcast calls populateEpisodeList with selected podcast", async () => {
  document.body.innerHTML = `
            <select id="podcast_select">
                <option value="http://example.com/rss.xml">Test Podcast</option>
            </select><ul id="podcast_episode_list"></ul>
            <img id="podcast_player_cover" />
            <p id="podcast_player_episode_name"></p>
            <audio id="podcast_player"></audio>
        `;

  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    text: () => `
            <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
                <channel>
                <image>
                    <url>http://example.com/cover.jpg</url>
                </image>
                <item>
                    <title>Test Episode 1</title>
                    <enclosure url="http://example.com/test1.mp3" type="audio/mpeg" />
                </item>
                <item>
                    <title>Test Episode 2</title>
                    <enclosure url="http://example.com/test2.mp3" type="audio/mpeg" />
                </item>
                </channel>
            </rss>
            `,
  });

  const select = document.getElementById("podcast_select");
  select.value = "http://example.com/rss.xml";
  select.onchange = loadPodcast;

  select.dispatchEvent(new Event("change"));

  expect(global.fetch).toHaveBeenCalledWith("http://example.com/rss.xml");

  const element = await vi.waitUntil(() => document.querySelector("#podcast_episode_list li:nth-child(2)"));

  expect(element.innerHTML).toContain("Test Episode 2");

  // Now we try play an episode
  element.click();

  const player = document.getElementById("podcast_player");
  const episodeTitle = document.getElementById("podcast_player_episode_name");
  const coverImage = document.getElementById("podcast_player_cover");

  expect(player.src).toBe("http://example.com/test2.mp3");
  expect(player.type).toBe("audio/mpeg");
  expect(episodeTitle.textContent).toBe("Player: Test Episode 2");
  expect(coverImage.src).toBe("http://example.com/cover.jpg");
});

test("no podcast episodes", async () => {
  document.body.innerHTML = `
            <select id="podcast_select">
                <option value="http://example.com/rss.xml">Test Podcast</option>
            </select><ul id="podcast_episode_list"></ul>
            <img id="podcast_player_cover" />
            <p id="podcast_player_episode_name"></p>
            <audio id="podcast_player"></audio>
        `;

  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    text: () => `
            <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
                <channel>
                <image>
                    <url>http://example.com/cover.jpg</url>
                </image>
                </channel>
            </rss>
            `,
  });

  const select = document.getElementById("podcast_select");
  select.value = "http://example.com/rss.xml";
  select.onchange = loadPodcast;

  select.dispatchEvent(new Event("change"));

  expect(global.fetch).toHaveBeenCalledWith("http://example.com/rss.xml");

  const element = await vi.waitUntil(() => document.querySelector("#podcast_episode_list li:nth-child(1)"));

  expect(element.innerHTML).toContain("Error: No episodes found in feed");
});

test("no podcast image", async () => {
  document.body.innerHTML = `
            <select id="podcast_select">
                <option value="http://example.com/rss.xml">Test Podcast</option>
            </select><ul id="podcast_episode_list"></ul>
            <img id="podcast_player_cover" />
            <p id="podcast_player_episode_name"></p>
            <audio id="podcast_player"></audio>
        `;

  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    text: () => `
            <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
                <channel>
                </channel>
            </rss>
            `,
  });

  const select = document.getElementById("podcast_select");
  select.value = "http://example.com/rss.xml";
  select.onchange = loadPodcast;

  select.dispatchEvent(new Event("change"));

  expect(global.fetch).toHaveBeenCalledWith("http://example.com/rss.xml");

  const element = await vi.waitUntil(() => document.querySelector("#podcast_player_cover"));

  expect(element.src).toBe("");
});

test("Fail to fetch podcast, 404", async () => {
  document.body.innerHTML = `
            <select id="podcast_select">
                <option value="http://example.com/rss.xml">Test Podcast</option>
            </select><ul id="podcast_episode_list"></ul>
            <img id="podcast_player_cover" />
        `;

  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 404,
  });

  const select = document.getElementById("podcast_select");
  select.value = "http://example.com/rss.xml";
  select.onchange = loadPodcast;

  select.dispatchEvent(new Event("change"));

  const element = await vi.waitUntil(() => document.querySelector("#podcast_episode_list li"));

  expect(element.innerHTML).toContain("Error: HTTP error! status: 404");
});

test("Reset page if no url selected", async () => {
  document.body.innerHTML = `
            <select id="podcast_select">
                <option value="">Test Podcast</option>
            </select><ul id="podcast_episode_list"></ul>
            <img id="podcast_player_cover" />
        `;

  const select = document.getElementById("podcast_select");
  select.value = "";
  select.onchange = loadPodcast;

  select.dispatchEvent(new Event("change"));

  const episodeList = document.getElementById("podcast_episode_list");

  expect(episodeList.innerHTML).toBe("");
  expect(episodeList.style.display).toBe("none");
});

test("showJSDivs shows the podcast_select div", () => {
  document.body.innerHTML = `
        <div id="podcast_select"></div>
        <img id="podcast_player_cover" />
    `;

  showJSDivs();

  const breadcrumbJSDiv = document.getElementById("podcast_select");
  const coverImage = document.getElementById("podcast_player_cover");

  expect(breadcrumbJSDiv.style.display).toBe("block");
  expect(coverImage.style.display).toBe("block");
});
