function grab_to_clipboard(button_name) {
	console.log(`User clicked: ${button_name}`);
	// Get the text field
	const copyText = document.getElementById(button_name);

	// Select the text field
	copyText.select();
	copyText.setSelectionRange(0, 99999); // For mobile devices

	// Copy the text inside the text field
	navigator.clipboard.writeText(copyText.value);

	// Alert the copied text
	console.log(`Copied the text: ${copyText.value} to clipboard`);

	document.getElementById(`${button_name}_button`).innerHTML = "Copied!";
	setTimeout(reset_text, 2000, button_name);
}

function reset_text(button_name) {
	document.getElementById(`${button_name}_button`).innerHTML = "Copy URL";
}
