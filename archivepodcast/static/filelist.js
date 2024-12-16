var file_structure = new Object();
var current_path = new Array();
current_path = [""];

function add_file_to_structure(file_path, file_name) {
  var path_parts = file_name.split("/");
  var current = file_structure;
  for (var i = 0; i < path_parts.length; i++) {
    if (!current[path_parts[i]]) {
      current[path_parts[i]] = new Object();
    }
    current = current[path_parts[i]];
  }
  current["__name__"] = file_name;
}

document.addEventListener("DOMContentLoaded", function () {
  var fileListDiv = document.getElementById("file_list");
  if (fileListDiv) {
    fileListDiv.style.display = "none";
    const links = fileListDiv.querySelectorAll("a");
    links.forEach((link) => {
      if (link && link.firstChild) {
        console.log(link.href);
        console.log(link.firstChild.textContent);
        add_file_to_structure(link.href, link.firstChild.textContent);
      }
    });
  }
  var fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.style.display = "block";
  }
});

function show_current_directory() {
  var items = Object.keys(file_structure[""]).filter(key => key !== "__name__");
  console.log(items);
  var fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.innerHTML = JSON.stringify(items);
  }
}

show_current_directory()
