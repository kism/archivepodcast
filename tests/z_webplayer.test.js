// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, test, vi } from "vitest";

import { playerSetCurrentEpisode, populateEpisodeList, loadPodcast, showJSDivs } from "../archivepodcast/static/webplayer";

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
            <p id="podcast_player_episode_name"></p>
            <audio id="podcast_player"></audio>
        `;

  global.fetch = vi.fn().mockResolvedValue({
    text: () => `
            <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
                <channel>
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

  expect(player.src).toBe("http://example.com/test2.mp3");
  expect(player.type).toBe("audio/mpeg");
  expect(episodeTitle.textContent).toBe("Player: Test Episode 2");
});

test("Fail to fetch podcast, 404", async () => {
  document.body.innerHTML = `
            <select id="podcast_select">
                <option value="http://example.com/rss.xml">Test Podcast</option>
            </select><ul id="podcast_episode_list"></ul>
        `;

  global.fetch = vi.fn().mockResolvedValue({
    status: 404,
  });

  const select = document.getElementById("podcast_select");
  select.value = "http://example.com/rss.xml";
  select.onchange = loadPodcast;

  select.dispatchEvent(new Event("change"));

  const episodeList = document.getElementById("podcast_episode_list");

  expect(episodeList.innerHTML).toBe("Loading...");
} );

test("showJSDivs shows the podcast_select div", () => {
  document.body.innerHTML = `
        <div id="podcast_select"></div>
    `;

  showJSDivs();

  const breadcrumbJSDiv = document.getElementById("podcast_select");

  expect(breadcrumbJSDiv.style.display).toBe("block");
} );
