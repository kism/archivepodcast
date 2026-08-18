/**
 * File list module for managing directory structure and navigation
 */

// Root object for file system structure
export const file_structure = new Object();

/**
 * Shows file navigation UI elements
 */
export function showJSDivs() {
  const breadcrumbJSDiv = document.getElementById("breadcrumb_js");
  if (breadcrumbJSDiv) {
    breadcrumbJSDiv.style.display = "block";
  }
  const fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.style.display = "block";
  }
}

/**
 * Adds a file to the virtual file system structure
 * @param {string} url - File URL
 * @param {string} file_path - File path in structure
 */
export function addFileToStructure(url, file_path) {
  const path_parts = file_path.split("/");
  let current = file_structure;
  for (let i = 0; i < path_parts.length; i++) {
    if (!current[path_parts[i]]) {
      current[path_parts[i]] = new Object();
    }
    current = current[path_parts[i]];
  }
  current.url = url;
}

/**
 * Generates breadcrumb navigation HTML
 * @param {string} in_current_path - Current directory path
 * @returns {string} HTML string
 */
export function generateBreadcrumbHtml(in_current_path) {
  let html = "";
  let path = [""];

  if (in_current_path !== "/") {
    path = in_current_path.split("/");
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

export function generateCurrentListHTML(in_current_path, items) {
  let html = "";

  let current_path_nice = in_current_path;

  if (in_current_path !== "/") {
    let current_path_split = current_path_nice.split("/");
    current_path_split.pop();
    current_path_split = current_path_split.join("/");
    html += `<li>📂 <a href="#${current_path_split}/">..</a></li>`;
  } else {
    current_path_nice = "";
  }

  if (items && typeof items === "object") {
    for (const [key, value] of Object.entries(items)) {
      if (value.url === undefined) {
        html += `<li>📂 <a href="#${current_path_nice}/${key}/" ;>${key}/</a></li>`;
      }
    }

    for (const [key, value] of Object.entries(items)) {
      if (value.url !== undefined) {
        html += `<li>💾 <a href="${value.url}">${key}</a></li>`;
      }
    }
  }

  html += "";
  return html;
}

export function getValue(obj, path) {
  if (path === "/") return obj[""];
  const keys = path.split("/"); // Split the path by '/' into an array of keys.
  return keys.reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), obj);
}

export function checkValidPath(path) {
  if (path === "" || path === "/") {
    return true;
  }
  const path_parts = path.split("/");
  let current = file_structure;
  for (let i = 0; i < path_parts.length; i++) {
    if (!current[path_parts[i]]) {
      console.log("Invalid path: ", path);
      return false;
    }
    current = current[path_parts[i]];
  }
  return true;
}

export function getNicePathStr() {
  let path = window.location.hash;

  path = path.replace("#", ""); // Remove the hash

  if (path === "" || path === "/") {
    // If the path is empty or just a slash, return a single slash
    return "/";
  }
  path = path.replace(/\/\//g, "/"); // Replace double slashes with a single slash
  if (path[path.length - 1] === "/") {
    // Remove trailing slash
    path = path.slice(0, -1);
  }
  return path;
}

export function showCurrentDirectory() {
  let current_path = getNicePathStr();

  // Handle invalid paths
  if (!checkValidPath(current_path)) {
    const breadcrumbJSDiv = document.getElementById("breadcrumb_js");
    breadcrumbJSDiv.innerHTML = generateBreadcrumbHtml("/");
    const fileListJSDiv = document.getElementById("file_list_js");
    fileListJSDiv.innerHTML = `<li>Invalid path: ${current_path}</li>`;
    return;
  }

  // Normalize the current path
  current_path = current_path.replace(/\/\//g, "/");
  if (current_path[current_path.length - 1] === "/") {
    current_path = current_path.slice(0, -1);
  }
  if (current_path === "") {
    current_path = "/";
  }

  // Update breadcrumb
  const breadcrumbJSDiv = document.getElementById("breadcrumb_js");
  if (breadcrumbJSDiv) {
    breadcrumbJSDiv.innerHTML = generateBreadcrumbHtml(current_path);
  }

  //File List
  const items = getValue(file_structure, current_path);
  const fileListJSDiv = document.getElementById("file_list_js");
  if (fileListJSDiv) {
    fileListJSDiv.innerHTML = generateCurrentListHTML(current_path, items);
  }
}

// Initialize file list
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
  showJSDivs();
  showCurrentDirectory();
});

// Handle navigation
window.addEventListener("hashchange", showCurrentDirectory);
showCurrentDirectory();
