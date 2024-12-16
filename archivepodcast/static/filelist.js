var file_structure = new Object();

function add_file_to_structure(file_path, file_name) {
  var path_parts = file_path.split("/");
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
    const link = fileListDiv.querySelector("a");
    if (link && link.firstChild) {
      console.log(link.href);
      console.log(link.firstChild.textContent);
      add_file_to_structure(link.href, link.firstChild.textContent);
    }
  }
  var fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.style.display = "block";
    fileListJSDiv.textContent = JSON.stringify(file_structure);
  }
});
