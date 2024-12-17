export function grabToClipboard(button_name) {
  console.log(`User clicked: ${button_name}`);
  const copyText = document.getElementById(button_name);

  // Select the text field
  copyText.select();
  copyText.setSelectionRange(0, 99999); // For mobile devices

  // Copy the text inside the text field
  navigator.clipboard.writeText(copyText.value);

  document.getElementById(`${button_name}_button`).innerHTML = "Copied!";
  setTimeout(resetText, 2000, button_name);
}

function resetText(button_name) {
  document.getElementById(`${button_name}_button`).innerHTML = "Copy URL";
}
