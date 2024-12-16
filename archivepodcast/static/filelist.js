var file_structure = new Object();
var current_path = new Array();
current_path = "/";
// current_path = "/content";

function add_file_to_structure(file_path, file_name) {
  var path_parts = file_name.split("/");
  var current = file_structure;
  for (var i = 0; i < path_parts.length; i++) {
    if (!current[path_parts[i]]) {
      current[path_parts[i]] = new Object();
    }
    current = current[path_parts[i]];
  }
  current["url"] = file_path;
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
  show_current_directory();
});

function getValue(obj, path) {
  if (!path) return obj; // If no path is provided, return the object itself.
  if (path == "/") return obj[""];
  const keys = path.split("/"); // Split the path by '/' into an array of keys.
  return keys.reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), obj);
}

function generate_current_list_html(items) {
  console.log(items);
  var html = "";

  Object.entries(items).forEach(([key, value]) => {
    console.log(`Key: ${key}, Value: ${value["url"]}`);
    if (value["url"] === undefined) {
      html += `<br>${key}`;
    } else {
      html += `<br><a href= ${value["url"]}>${key}</a>`;
    }
  });

  html += "";
  console.log(html);
  return html;
}

function show_current_directory() {
  var items = getValue(file_structure, current_path);
  var fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.innerHTML = generate_current_list_html(items);
  }
}
