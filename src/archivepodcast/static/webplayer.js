/**
 * Web player module for handling podcast playback and metadata
 */

// Base64 encoded 1x1 transparent PNG for placeholder images
const placeholder_image =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACXBIWXMAAC4jAAAuIwF4pT92AAAADUlEQVQI12M4ceLEfwAIDANY5PrZiQAAAABJRU5ErkJggg==";

// Current podcast cover image URL, defaults to placeholder
let current_podcast_cover_image = placeholder_image;

/**
 * Updates the audio player with new episode details and metadata
 * @param {string} url - Audio file URL
 * @param {string} type - Audio MIME type
 * @param {string} episodeName - Episode title
 * @param {string} podcastName - Podcast name
 */
export function playerSetCurrentEpisode(url, type, episodeName, podcastName) {
  console.log("Setting player src to:", url);
  const player = document.getElementById("podcast-audio-player");
  const podcastTitle = document.getElementById("podcast_player_podcast_name");
  const episodeTitle = document.getElementById("podcast_player_episode_name");
  podcastTitle.textContent = `${podcastName}`;
  episodeTitle.textContent = `${episodeName}`;

  player.src = url;
  player.type = type;

  try {
    const cover_image_element = document.getElementById("podcast-player-cover");
    cover_image_element.src = current_podcast_cover_image;
  } catch (_error) {}

  if ("mediaSession" in navigator && "MediaMetadata" in window) {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: episodeName,
      artist: podcastName,
      artwork: [
        { src: current_podcast_cover_image, sizes: "96x96", type: "image/png" },
        { src: current_podcast_cover_image, sizes: "128x128", type: "image/png" },
        { src: current_podcast_cover_image, sizes: "192x192", type: "image/png" },
        { src: current_podcast_cover_image, sizes: "256x256", type: "image/png" },
        { src: current_podcast_cover_image, sizes: "384x384", type: "image/png" },
        { src: current_podcast_cover_image, sizes: "512x512", type: "image/png" },
      ],
    });
  }
}

/**
 * Fetches and parses an XML podcast feed
 * @param {string} url - Feed URL
 * @returns {Promise<Document>} Parsed XML document
 */
async function fetchAndParseXML(url) {
  console.log("Fetching and parsing XML from:", url);

  const response = await fetch(url, {
    cache: "no-cache",
    headers: {
      "Cache-Control": "no-cache, no-store, must-revalidate",
      Pragma: "no-cache",
      Expires: "0",
    },
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const text = await response.text();
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(text, "application/xml");
  return xmlDoc;
}

/**
 * Populates the episode list from a podcast feed
 * @param {string} url - Feed URL
 */
export function populateEpisodeList(url) {
  const episodeList = document.getElementById("podcast-episode-list");

  if (!url || url === "") {
    console.log("No podcast selected");
    episodeList.innerHTML = "";
    episodeList.style.display = "none";
    return;
  }

  episodeList.innerHTML = "Loading...";
  episodeList.style.display = "block";

  fetchAndParseXML(url)
    .then((xmlDoc) => {
      try {
        current_podcast_cover_image = xmlDoc
          .getElementsByTagName("image")[0]
          .getElementsByTagName("url")[0].textContent;
      } catch (error) {
        console.error("Error loading cover image:", error);
      }

      let podcastName = "-";
      try {
        podcastName = xmlDoc.getElementsByTagName("title")[0].textContent;
      } catch (error) {
        console.error("Error loading podcast name:", error);
      }

      episodeList.innerHTML = "";

      const items = xmlDoc.getElementsByTagName("item");

      if (items.length === 0) {
        console.log("No episodes found in feed");
        throw new Error("No episodes found in feed");
      }

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        const title = item.getElementsByTagName("title")[0].textContent;
        const url = item.getElementsByTagName("enclosure")[0].getAttribute("url");
        const type = item.getElementsByTagName("enclosure")[0].getAttribute("type");
        const li = document.createElement("li");
        li.onclick = () => playerSetCurrentEpisode(url, type, title, podcastName);
        li.textContent = `${title}`;
        episodeList.appendChild(li);
      }
    })
    .catch((error) => {
      console.error("Error loading episodes:", error);
      episodeList.innerHTML = `<li>${error}</li>`;
    });
}

// Event handler for podcast selection
export function loadPodcast(event) {
  const selectedPodcast = event.target.value;
  populateEpisodeList(selectedPodcast);
}

/**
 * Initializes player UI elements
 */
export function showJSDivs() {
  try {
    const cover_image_element = document.getElementById("podcast-player-cover");
    cover_image_element.src = placeholder_image;
    cover_image_element.style.display = "block";
  } catch (_error) {}

  const breadcrumbJSDiv = document.getElementById("podcast_select");
  if (breadcrumbJSDiv) {
    breadcrumbJSDiv.style.display = "block";
  }
}

window.loadPodcast = loadPodcast;

showJSDivs();
