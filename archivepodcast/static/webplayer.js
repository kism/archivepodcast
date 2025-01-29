const placeholder_image =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACXBIWXMAAC4jAAAuIwF4pT92AAAADUlEQVQI12M4ceLEfwAIDANY5PrZiQAAAABJRU5ErkJggg==";

let current_podcast_cover_image = placeholder_image;

export function playerSetCurrentEpisode(url, type, episodeName) {
  console.log("Setting player src to:", url);
  const player = document.getElementById("podcast_player");
  const episodeTitle = document.getElementById("podcast_player_episode_name");
  episodeTitle.textContent = `Player: ${episodeName}`;
  player.src = url;
  player.type = type;

  try {
    const cover_image_element = document.getElementById("podcast_player_cover");
    cover_image_element.src = current_podcast_cover_image;
  } catch (error) {}
}

async function fetchAndParseXML(url) {
  console.log("Fetching and parsing XML from:", url);

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const text = await response.text();
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(text, "application/xml");
  return xmlDoc;
}

export function populateEpisodeList(url) {
  const episodeList = document.getElementById("podcast_episode_list");

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
        li.onclick = () => playerSetCurrentEpisode(url, type, title);
        li.textContent = `${title}`;
        episodeList.appendChild(li);
      }
    })
    .catch((error) => {
      console.error("Error loading episodes:", error);
      episodeList.innerHTML = `<li>${error}</li>`;
    });
}

export function loadPodcast(event) {
  const selectedPodcast = event.target.value;
  populateEpisodeList(selectedPodcast);
}

export function showJSDivs() {
  try {
    const cover_image_element = document.getElementById("podcast_player_cover");
    cover_image_element.src = placeholder_image;
    cover_image_element.style.display = "block";
  } catch (error) {}

  const breadcrumbJSDiv = document.getElementById("podcast_select");
  if (breadcrumbJSDiv) {
    breadcrumbJSDiv.style.display = "block";
  }
}

window.loadPodcast = loadPodcast;

showJSDivs();
