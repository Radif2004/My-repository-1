// src/api.js
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;
const API_KEY = process.env.REACT_APP_COPILOT_API_KEY;

// Default headers
const defaultHeaders = {
  "X-API-Key": API_KEY,
  "Content-Type": "application/json"
};

// POST JSON
export async function postJSON(endpoint, data) {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(data)
  });
  return res.json();
}

// GET
export async function getJSON(endpoint) {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers: { "X-API-Key": API_KEY }
  });
  return res.json();
}

// POST File (for PDF upload)
export async function postFile(endpoint, file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY }, // no Content-Type for FormData
    body: formData
  });
  return res.json();
}
