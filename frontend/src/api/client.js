const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : "Request failed");
    this.status = status;
    this.detail = detail;
  }
}

let authToken = null;

export function setAuthToken(token) {
  authToken = token;
}

/**
 * Core request helper. Throws ApiError on any non-2xx response so callers
 * can catch one error type regardless of whether it's a 400 validation
 * error, a 401, or a 404 -- the FastAPI backend's HTTPException detail
 * message is always surfaced as `.detail`.
 */
async function request(path, { method = "GET", body, isFormData = false } = {}) {
  const headers = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
  if (body && !isFormData) headers["Content-Type"] = "application/json";

  const resp = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
  });

  // 204 / empty body responses
  const text = await resp.text();
  const data = text ? JSON.parse(text) : null;

  if (!resp.ok) {
    throw new ApiError(resp.status, data?.detail || resp.statusText);
  }
  return data;
}

export const api = {
  // --- Auth ---
  signup: (email, password) =>
    request("/auth/signup", { method: "POST", body: { email, password } }),

  login: (email, password) => {
    // The backend's /auth/login uses OAuth2PasswordRequestForm (form-encoded
    // username/password), not JSON -- specifically so Swagger's own
    // "Authorize" button works against it. Matching that here.
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    return fetch(`${API_BASE}/auth/login`, { method: "POST", body: form }).then(async (resp) => {
      const data = await resp.json();
      if (!resp.ok) throw new ApiError(resp.status, data?.detail);
      return data;
    });
  },

  // --- User's own Gemini API key ---
  // The key itself is never returned by any of these -- only whether one
  // is currently set (has_custom_key). See PUT/GET/DELETE /auth/api-key.
  getApiKeyStatus: () => request("/auth/api-key"),
  setApiKey: (geminiApiKey) =>
    request("/auth/api-key", { method: "PUT", body: { gemini_api_key: geminiApiKey } }),
  deleteApiKey: () => request("/auth/api-key", { method: "DELETE" }),

  // --- Files ---
  listFiles: () => request("/files"),
  uploadFile: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/upload", { method: "POST", body: form, isFormData: true });
  },
  getFileHistory: (fileId) => request(`/history/${fileId}`),
  askFile: (fileId, question, includeChart) =>
    request("/ask", { method: "POST", body: { file_id: fileId, question, include_chart: includeChart } }),

  // --- Databases ---
  listDatabases: () => request("/databases"),
  connectDatabase: (connectionString, label) =>
    request("/connect-db", { method: "POST", body: { connection_string: connectionString, label } }),
  getDbHistory: (dbId) => request(`/history-db/${dbId}`),
  askDatabase: (dbId, question, includeChart) =>
    request("/ask-db", { method: "POST", body: { db_id: dbId, question, include_chart: includeChart } }),
};
