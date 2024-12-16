var file_structure = new Object();
var current_path = new Array();
current_path = "/";

function addFileToStructure(file_path, file_name) {
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
  let fileListDiv = document.getElementById("file_list");
  if (fileListDiv) {
    fileListDiv.style.display = "none";
    const links = fileListDiv.querySelectorAll("a");
    links.forEach((link) => {
      if (link && link.firstChild) {
        addFileToStructure(link.href, link.firstChild.textContent);
      }
    });
  }
  var fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.style.display = "block";
  }
  showCurrentDirectory();
});


function generateBreadcrumbHtml() {
  let html = "";
  let path = [];
  if (current_path === "/") {
    path = [""];
  } else {
    path = current_path.split("/");
  }
  let current = "";
  console.log("generateBreadcrumbHtml", path);
  html += `<a href=# onclick=updatePathAbsolute("/");>File list home</a>`;
  for (let i = 0; i < path.length; i++) {
    if (path[i] === "") {
      continue;
    }
    current = `${current}/${path[i]}`;
    html += ` / <a href=# onclick=updatePathAbsolute("${current}");>${path[i]}</a>`;
  }
  return html;
}

function generateCurrentListHTML(items) {
  let html = "";

  if (current_path !== "/") {
    html += `<br><a href=# onclick=updatePathRelative("..");>..</a>`;
  }

  Object.entries(items).forEach(([key, value]) => {
    if (value["url"] === undefined) {
      html += `<br><a href=# onclick=updatePathRelative("${key}");>${key}</a>`;
    } else {
      html += `<br><a href=${value["url"]}>${key}</a>`;
    }
  });

  html += "";
  return html;
}

function updatePathAbsolute(path) {
  current_path = path;
  showCurrentDirectory();
}

function updatePathRelative(directory) {
  if (current_path === "/") { // Remove the leading slash to avoid double slash at the beginning of the path.
    current_path = "";
  }
  if (directory === "..") {
    current_path = current_path.split("/").slice(0, -1).join("/");
  } else {
    current_path = `${current_path}/${directory}`;
  }
  showCurrentDirectory();
}

function getValue(obj, path) {
  if (!path) return obj; // If no path is provided, return the object itself.
  if (path == "/") return obj[""];
  const keys = path.split("/"); // Split the path by '/' into an array of keys.
  return keys.reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), obj);
}

function showCurrentDirectory() {
  console.log("showCurrentDirectory", current_path);
  if (current_path === "") { // Add the leading slash if the path is empty.
    current_path = "/";
  }
  let breadcrumbJSDiv = document.getElementById("breadcrumb_js");
  if (breadcrumbJSDiv) {
    breadcrumbJSDiv.style.display = "block";
    breadcrumbJSDiv.innerHTML = generateBreadcrumbHtml();
  }
  let items = getValue(file_structure, current_path);
  let fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.innerHTML = generateCurrentListHTML(items);
  }
}
