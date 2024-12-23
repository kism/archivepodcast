// // @vitest-environment happy-dom
import { describe, it, expect, vi, beforeEach, test } from "vitest";
import { APHealthListener } from "../archivepodcast/static/health";

beforeEach(() => {
  document.body.innerHTML = '<div id="health" style="display: block;"></div>';
  global.fetch = vi.fn();
});

const healthData = {
  core: {
    about_page_exists: true,
    alive: true,
    currently_loading_config: false,
    currently_rendering: true,
    last_run: 1734919334,
    last_startup: 1734919332,
    memory_mb: 77.515625,
  },
  podcasts: {
    test_healthy: {
      episode_count: 9,
      healthy: true,
      last_fetched: 1734919339,
      latest_episode: {
        pubdate: 1726512256,
        title: "Trailer - Question Everything",
      },
      rss_available: true,
      rss_fetching_live: true,
    },
    test_unhealthy: {
      episode_count: 9,
      healthy: false,
      last_fetched: 1734919339,
      latest_episode: {
        pubdate: 1726512256,
        title: "Trailer - Question Everything",
      },
      rss_available: true,
      rss_fetching_live: true,
    },
  },
  templates: {
    "filelist.html": {
      last_rendered: 1734919340,
    },
    "guide.html": {
      last_rendered: 1734919334,
    },
    "health.html": {
      last_rendered: 1734919334,
    },
    "index.html": {
      last_rendered: 1734919334,
    },
  },
  version: "1.2.2",
};

test("DOMContentLoaded event", () => {
  global.fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ...healthData }),
  });

  document.dispatchEvent(new Event("DOMContentLoaded"));
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(global.fetch).toHaveBeenCalledWith("/api/health");

  const healthDiv = document.getElementById("health");
  // expect(document.children.length).toBe(6);

  // const table = healthDiv.querySelector("table");
  // expect(table).not.toBeNull();
});
