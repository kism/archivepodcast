function sortLinks() {
  const container = document.getElementById("file_list");
  const lines = Array.from(container.children);

  // Sort lines based on the text content of the links
  lines.sort((a, b) => {
    const textA = a.textContent.trim().toLowerCase();
    const textB = b.textContent.trim().toLowerCase();

    // Count slashes in each line
    const slashCountA = (textA.match(/\//g) || []).length;
    const slashCountB = (textB.match(/\//g) || []).length;

    // Prioritize lines with one or fewer slashes
    if (slashCountA <= 1 && slashCountB > 1) return -1;
    if (slashCountB <= 1 && slashCountA > 1) return 1;

    // Sort alphabetically if slash counts are equal
    return textA.localeCompare(textB);
  });

  // Append sorted lines back to the container
  lines.forEach((line) => container.appendChild(line));
}
sortLinks();
