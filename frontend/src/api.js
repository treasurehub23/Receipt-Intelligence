// Same-origin API: works when FastAPI serves the built React frontend.
export const API_BASE_URL = "";

export function getToken() {
  return localStorage.getItem("access_token");
}

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  // Do not set Content-Type for FormData; the browser supplies its boundary.
  if (options.body && !(options.body instanceof FormData) &&
      !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = typeof data === "object" && data?.detail
      ? data.detail
      : (typeof data === "string" ? data.slice(0, 180) : "Request failed");
    throw new Error(message);
  }
  if (typeof data === "string" && data.trimStart().startsWith("<!doctype")) {
    throw new Error(`API route ${path} returned HTML instead of JSON. Check the FastAPI route path.`);
  }
  return data;
}