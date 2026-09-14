/**
 * File list module for managing directory structure and navigation
 */

// Root object for file system structure
export const file_structure = {};

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
      current[path_parts[i]] = {};
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

  return html;
}

export function getValue(obj, path) {
  if (path === "/") return obj[""];
  const keys = path.split("/"); // Split the path by '/' into an array of keys.
  return keys.reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), obj);
}

export function getNicePathStr() {
  // Strip the hash, collapse repeated slashes, drop the trailing slash
  const path = window.location.hash.replace("#", "").replace(/\/+/g, "/").replace(/\/$/, "");
  return path || "/";
}

export function showCurrentDirectory() {
  const current_path = getNicePathStr();
  const items = getValue(file_structure, current_path);
  const breadcrumbJSDiv = document.getElementById("breadcrumb_js");
  const fileListJSDiv = document.getElementById("file_list_js");

  // Handle invalid paths
  if (current_path !== "/" && items === undefined) {
    breadcrumbJSDiv.innerHTML = generateBreadcrumbHtml("/");
    fileListJSDiv.innerHTML = `<li>Invalid path: ${current_path}</li>`;
    return;
  }

  if (breadcrumbJSDiv) {
    breadcrumbJSDiv.innerHTML = generateBreadcrumbHtml(current_path);
  }
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
