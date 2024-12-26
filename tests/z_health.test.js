// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, test, vi } from "vitest";
import { populateHealth } from "../archivepodcast/static/health";

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
});

test("populateHealth generates", () => {
  populateHealth(healthData);
  const healthDiv = document.getElementById("health");
  expect(healthDiv.children.length).greaterThan(0);
});

test("check date fields in health div", () => {
  populateHealth(healthData);
  const healthDiv = document.getElementById("health");
  const dateFields = healthDiv.querySelectorAll("[id*='date'], [id*='last']");

  for (const field of dateFields) {
    const dateValue = new Date(field.textContent);
    expect(dateValue.toString()).not.toBe("Invalid Date");
  }
});
