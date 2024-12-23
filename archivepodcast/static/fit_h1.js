export function fitTextToContainer() {
  const h1Divs = document.querySelectorAll(".h1-div"); // Ensure you are selecting the correct elements

  for (const h1Div of h1Divs) {
    console.log(h1Div);
    h1Div.style.display = "flex";
    h1Div.style.marginTop = "20px";
  }

  const h1Elements = document.querySelectorAll("h1"); // Ensure you are selecting the correct elements

  for (const h1 of h1Elements) {
    h1.style.margin = "0";
    h1.style.whiteSpace = "nowrap";
    h1.style.display = "inline !important";
    h1.style.textAlign = "left";
  }

  for (const h1 of h1Elements) {
    // Reset font size to ensure accurate measurements
    let fontSize = 10; // Start small
    const maxHeight = 48; // Max height of h1 element
    const container = h1.parentElement;

    h1.style.fontSize = `${fontSize}px`;
    h1.style.height = "auto";

    // Increase font size until text overflows container width or exceeds max height
    while (
      h1.offsetWidth < container.offsetWidth &&
      h1.offsetHeight < maxHeight &&
      fontSize < 1000 // Safety limit to prevent infinite loop
    ) {
      fontSize = fontSize + 0.1;
      h1.style.fontSize = `${fontSize}px`;
    }
    h1.style.marginTop = `${maxHeight / 2 - h1.offsetHeight / 2}px`;
    h1.style.marginBottom = `${maxHeight / 2 - h1.offsetHeight / 2}px`;
  }
}

window.addEventListener("load", fitTextToContainer);
window.addEventListener("resize", fitTextToContainer);
