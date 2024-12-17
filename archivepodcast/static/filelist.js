export const file_structure = new Object();
let current_path = new Array();

export function addFileToStructure(file_path, file_name) {
  const path_parts = file_name.split("/");
  let current = file_structure;
  for (let i = 0; i < path_parts.length; i++) {
    if (!current[path_parts[i]]) {
      current[path_parts[i]] = new Object();
    }
    current = current[path_parts[i]];
  }
  current.url = file_path;
}

export function generateBreadcrumbHtml(current_path) {
  console.log(`Current path: ${current_path}`);
  let html = "";
  let path = [""];

  if (current_path !== "/") {
    path = current_path.split("/");
  }
  path.shift();

  let current = "";
  html += `<a href="#/">File list</a> / `;
  for (let i = 0; i < path.length; i++) {
    current = `${current}/${path[i]}`;
    current = current.replace(/\/\//g, "/");
    html += `<a href="#${current}/">${path[i]}</a> / `;
  }
  return html;
}

export function generateCurrentListHTML(items) {
  let html = "";

  let current_path_nice = current_path;

  if (current_path !== "/") {
    let current_path_split = current_path_nice.split("/");
    current_path_split.pop();
    current_path_split = current_path_split.join("/");
    html += `📂 <a href="#${current_path_split}/">..</a><br>`;
  } else {
    current_path_nice = "";
  }

  if (items && typeof items === "object") {
    for (const [key, value] of Object.entries(items)) {
      if (value.url === undefined) {
        html += `📂 <a href="#${current_path_nice}/${key}/" ;>${key}/</a><br>`;
      }
    }

    for (const [key, value] of Object.entries(items)) {
      if (value.url !== undefined) {
        html += `💾 <a href="${value.url}">${key}</a><br>`;
      }
    }
  }

  html += "";
  return html;
}

export function updatePathAbsolute(path) {
  current_path = path;
  showCurrentDirectory();
}

export function updatePathRelative(directory) {
  if (directory === "..") {
    current_path = `${current_path.split("/").slice(0, -1).join("/")}/`;
  } else {
    current_path = `${current_path}/${directory}/`;
  }
  showCurrentDirectory();
}

export function getValue(obj, path) {
  if (!path) return obj; // If no path is provided, return the object itself.
  if (path === "/") return obj[""];
  const keys = path.split("/"); // Split the path by '/' into an array of keys.
  return keys.reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), obj);
}

export function showCurrentDirectory() {
  current_path = window.location.hash.replace("#", "");
  current_path = current_path.replace(/\/\//g, "/");
  if (current_path[current_path.length - 1] === "/") {
    current_path = current_path.slice(0, -1);
  }
  if (current_path === "") {
    current_path = "/";
  }

  const breadcrumbJSDiv = document.getElementById("breadcrumb_js");
  if (breadcrumbJSDiv) {
    breadcrumbJSDiv.style.display = "block";
    breadcrumbJSDiv.innerHTML = generateBreadcrumbHtml(current_path);
  }
  const items = getValue(file_structure, current_path);
  const fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.innerHTML = generateCurrentListHTML(items);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const fileListDiv = document.getElementById("file_list");
  if (fileListDiv) {
    fileListDiv.style.display = "none";
    const links = fileListDiv.querySelectorAll("a");
    for (const link of links) {
      if (link?.firstChild) {
        addFileToStructure(link.href, link.firstChild.textContent);
      }
    }
  }
  const fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.style.display = "block";
  }
  showCurrentDirectory();
});

// window.APFileList = { current_path }

window.addEventListener("hashchange", showCurrentDirectory);
showCurrentDirectory();
