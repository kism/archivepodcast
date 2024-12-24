function playerSetCurrentEpisode(url, type, episodeName) {
  const player = document.getElementById("podcast_player");
  // const source = document.getElementById("podcast_player_source");
  const episodeTitle = document.getElementById("podcast_player_episode_name");
  episodeTitle.textContent = `Episode: ${episodeName}`;
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
    console.error("Error fetching and parsing XML:", error);
  }
}

function populateEpisodeList(url) {
  fetchAndParseXML(url).then((xmlDoc) => {
    const episodeList = document.getElementById("podcast_episode_list");
    episodeList.style.display = "block";

    const items = xmlDoc.getElementsByTagName("item");

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      const title = item.getElementsByTagName("title")[0].textContent;
      const url = item.getElementsByTagName("enclosure")[0].getAttribute("url");
      const type = item.getElementsByTagName("enclosure")[0].getAttribute("type");
      const li = document.createElement("li");
      const playLink = document.createElement("a");
      playLink.href = "#";
      playLink.onclick = () => playerSetCurrentEpisode(url, type, title);
      playLink.textContent = title;
      li.appendChild(playLink);
      episodeList.appendChild(li);
    }
  });
}

// Example usage:
const url = "http://localhost:5100/rss/stown";
populateEpisodeList(url);
