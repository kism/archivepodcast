export function playerSetCurrentEpisode(url, type, episodeName) {
  console.log("Setting player src to:", url);
  const player = document.getElementById("podcast_player");
  const episodeTitle = document.getElementById("podcast_player_episode_name");
  episodeTitle.textContent = `Player: ${episodeName}`;
  player.src = url;
  player.type = type;
}

async function fetchAndParseXML(url) {
  try {
    const response = await fetch(url);
    const text = await response.text();
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(text, "application/xml");
    return xmlDoc;
  } catch (error) {
    console.log("Error fetching and parsing XML:", error);
  }
}

export function populateEpisodeList(url) {
  const episodeList = document.getElementById("podcast_episode_list");
  episodeList.innerHTML = "Loading...";
  episodeList.style.display = "block";

  fetchAndParseXML(url)
    .then((xmlDoc) => {
      episodeList.innerHTML = "";

      const items = xmlDoc.getElementsByTagName("item");

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        const title = item.getElementsByTagName("title")[0].textContent;
        const url = item.getElementsByTagName("enclosure")[0].getAttribute("url");
        const type = item.getElementsByTagName("enclosure")[0].getAttribute("type");
        const li = document.createElement("li");
        // const playLink = document.createElement("a");
        // li.href = "#";
        li.onclick = () => playerSetCurrentEpisode(url, type, title);
        li.textContent = `${title}`;
        // li.appendChild(playLink);
        episodeList.appendChild(li);
      }
    })
    .catch((error) => {
      console.error("Error loading episodes:", error);
      episodeList.innerHTML = `Error loading episodes: ${error}`;
    });
}

export function loadPodcast(event) {
  const selectedPodcast = event.target.value;
  populateEpisodeList(selectedPodcast);
}

export function showJSDivs() {
  const breadcrumbJSDiv = document.getElementById("podcast_select");
  if (breadcrumbJSDiv) {
    breadcrumbJSDiv.style.display = "block";
  }
}

window.loadPodcast = loadPodcast;

showJSDivs();
