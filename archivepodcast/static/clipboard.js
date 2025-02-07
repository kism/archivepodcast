/**
 * Clipboard interaction module for copying text
 */

/**
 * Copies text from an input element to clipboard
 * @param {string} button_name - ID of button/input element
 */
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

/**
 * Resets copy button text after delay
 * @param {string} button_name - ID of button element
 */
export function resetText(button_name) {
  document.getElementById(`${button_name}_button`).innerHTML = "Copy URL";
}

// Expose clipboard function globally
window.grabToClipboard = grabToClipboard;
