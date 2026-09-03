// @vitest-environment happy-dom
import { beforeEach, describe, expect, test, vi } from "vitest";
import { populateHealth, populateProfile } from "../src/archivepodcast/static/health";

beforeEach(() => {
  document.body.innerHTML = '<div id="health" style="display: block;"></div><div id="profile"></div>';
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

const profileData = {
  times: {
    "grab_podcasts/Update file cache": 0.01,
    "grab_podcasts/Scrape/_render_files": 0.03,
    "grab_podcasts/Scrape/silver": 78.65,
    "grab_podcasts/Scrape": 78.65,
    grab_podcasts: 78.67,
    root: 78.68,
  },
};

describe("Health API", () => {
  test("fetches health data on page load", () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...healthData }),
    });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...profileData }),
    });

    document.dispatchEvent(new Event("DOMContentLoaded"));
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(global.fetch).toHaveBeenCalledWith("/api/health");
  });

  test("populates health information from API response", () => {
    populateHealth(healthData);
    const healthDiv = document.getElementById("health");
    expect(healthDiv.children.length).greaterThan(0);
  });

  test("nests profile timers under their parent event", () => {
    populateProfile(profileData);
    const text = document.getElementById("profile").textContent;
    expect(text).toContain(
      [
        "root: 78.68s",
        "  grab_podcasts: 78.67s",
        "    Update file cache: 0.01s",
        "    Scrape: 78.65s",
        "      _render_files: 0.03s",
        "      silver: 78.65s",
      ].join("\n"),
    );
    expect(text).not.toContain("Unknown Event");
  });

  test("correctly formats all date fields in health display", () => {
    populateHealth(healthData);
    const healthDiv = document.getElementById("health");
    const dateFields = healthDiv.querySelectorAll("[id*='date'], [id*='last']");

    for (const field of dateFields) {
      const dateValue = new Date(field.textContent);
      expect(dateValue.toString()).not.toBe("Invalid Date");
    }
  });
});
