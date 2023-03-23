function grabtoclipboard(buttonname) {
    console.log("User clicked: " + buttonname);
    // Get the text field
    var copyText = document.getElementById(buttonname);

    // Select the text field
    copyText.select();
    copyText.setSelectionRange(0, 99999); // For mobile devices

     // Copy the text inside the text field
    navigator.clipboard.writeText(copyText.value);

    // Alert the copied text
    console.log("Copied the text: " + copyText.value + " to clipboard");
  }