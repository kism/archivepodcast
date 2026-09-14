/**
 * Clipboard interaction module for copying text
 */

/**
 * Copies the button's data-url to clipboard
 * @param {string} button_name - ID prefix of the button element
 */
export function grabToClipboard(button_name) {
  console.log(`User clicked: ${button_name}`);
  const button = document.getElementById(`${button_name}_button`);

  navigator.clipboard.writeText(button.dataset.url);

  button.innerHTML = "Copied!";
  setTimeout(resetText, 2000, button_name);
}

/**
 * Resets copy button text after delay
 * @param {string} button_name - ID of button element
 */
export function resetText(button_name) {
  document.getElementById(`${button_name}_button`).innerHTML = "Copy URL";
}

// Expose clipboard function globally
window.grabToClipboard = grabToClipboard;
