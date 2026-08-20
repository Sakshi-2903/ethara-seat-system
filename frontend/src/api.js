import { getToken, clearStoredAuth } from "./auth.jsx";

// In local dev, requests go to "/api" and Vite's proxy forwards them to
// localhost:8000. In production, VITE_API_URL points at the deployed backend.
const BASE = import.meta.env.VITE_API_URL || "/api";

async function request(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (res.status === 401) {
    // Session expired or missing — clear it and force back to the login screen.
    clearStoredAuth();
    window.location.reload();
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const message = data?.detail
      ? Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg).join(", ")
        : data.detail
      : `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

export const api = {
  // Dashboard
  dashboardSummary: () => request("/dashboard/summary"),
  projectUtilization: () => request("/dashboard/project-utilization"),
  floorUtilization: () => request("/dashboard/floor-utilization"),

  // Employees
  listEmployees: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/employees${qs ? `?${qs}` : ""}`);
  },
  getEmployee: (id) => request(`/employees/${id}`),
  createEmployee: (payload) =>
    request("/employees", { method: "POST", body: JSON.stringify(payload) }),
  updateEmployee: (id, payload) =>
    request(`/employees/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deactivateEmployee: (id) => request(`/employees/${id}`, { method: "DELETE" }),

  // Projects
  listProjects: () => request("/projects"),
  createProject: (payload) =>
    request("/projects", { method: "POST", body: JSON.stringify(payload) }),
  projectEmployees: (id) => request(`/projects/${id}/employees`),

  // Seats
  listSeats: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/seats${qs ? `?${qs}` : ""}`);
  },
  availableSeats: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/seats/available${qs ? `?${qs}` : ""}`);
  },
  allocateSeat: (payload) =>
    request("/seats/allocate", { method: "POST", body: JSON.stringify(payload) }),
  releaseSeat: (payload) =>
    request("/seats/release", { method: "POST", body: JSON.stringify(payload) }),

  // AI Assistant
  aiQuery: (payload) =>
    request("/ai/query", { method: "POST", body: JSON.stringify(payload) }),
};
