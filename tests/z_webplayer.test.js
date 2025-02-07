// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, test, vi } from "vitest";

import {
  loadPodcast,
  playerSetCurrentEpisode,
  populateEpisodeList,
  showJSDivs,
} from "../archivepodcast/static/webplayer";

// region: media mock
class MockMediaMetadata {
  constructor(init) {
    this.title = init.title || "";
    this.artist = init.artist || "";
    this.album = init.album || "";
    this.artwork = init.artwork || [];
  }
}

class MockMediaSession {
  constructor() {
    this.metadata = null;
    this.playbackState = "none";
    this.actions = {};
  }

  setActionHandler(action, handler) {
    this.actions[action] = handler;
  }
}

navigator.mediaSession = new MockMediaSession();
window.MediaMetadata = MockMediaMetadata;

// endregion

describe("playerSetCurrentEpisode", () => {
  test("sets audio source and updates episode information", () => {
    document.body.innerHTML = `
      <audio id="podcast_player"></audio>
      <div id="podcast_player_podcast_name"></div>
      <div id="podcast_player_episode_name"></div>
    `;

    playerSetCurrentEpisode("http://example.com/test.mp3", "audio/mpeg", "Test Episode", "Test Podcast");

    const player = document.getElementById("podcast_player");
    const episodeTitle = document.getElementById("podcast_player_episode_name");

    expect(player.src).toBe("http://example.com/test.mp3");
    expect(player.type).toBe("audio/mpeg");
    expect(episodeTitle.textContent).toBe("Test Episode");
  });
});

describe("loadPodcast", () => {
  test("successfully loads and displays podcast with episodes", async () => {
    document.body.innerHTML = `
              <select id="podcast_select">
                  <option value="http://example.com/rss.xml">Test Podcast</option>
              </select><ul id="podcast_episode_list"></ul>
              <img id="podcast_player_cover" />
              <p id="podcast_player_podcast_name"></p>
              <p id="podcast_player_episode_name"></p>
              <audio id="podcast_player"></audio>
          `;

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => `
              <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
                  <channel>
                  <title>Test Podcast</title>
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
    expect(episodeTitle.textContent).toBe("Test Episode 2");
    expect(coverImage.src).toBe("http://example.com/cover.jpg");

    expect(navigator.mediaSession.metadata.title).toBe("Test Episode 2");
    expect(navigator.mediaSession.metadata.artist).toBe("Test Podcast");
    expect(navigator.mediaSession.metadata.album).toBe("");
  });

  test("handles empty podcast feed with no episodes", async () => {
    document.body.innerHTML = `
              <select id="podcast_select">
                  <option value="http://example.com/rss.xml">Test Podcast</option>
              </select><ul id="podcast_episode_list"></ul>
              <img id="podcast_player_cover" />
              <p id="podcast_player_podcast_name"></p>
              <p id="podcast_player_episode_name"></p>
              <audio id="podcast_player"></audio>
          `;

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => `
              <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
                  <channel>
                  <title>Test Podcast</title>
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

  test("handles podcast feed without cover image", async () => {
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

  test("handles 404 error when fetching podcast", async () => {
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

  test("clears display when no podcast URL is selected", async () => {
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
});

describe("showJSDivs", () => {
  test("shows podcast select and cover image elements", () => {
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
});
