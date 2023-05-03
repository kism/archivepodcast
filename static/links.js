//prepend the text field with the base url
function replacetext(infield) {
    console.log(infield);
    infield.value = window.location + infield.value;
}

inputfields = document.querySelectorAll('input[type="text"]');
inputfields.forEach(replacetext);
