import { createContext, useContext, useState, useCallback } from "react";

const AuthContext = createContext(null);

const STORAGE_KEY = "ethara_auth";

// Same BASE logic as api.js — in dev this is "/api" (proxied by Vite to
// localhost:8000); in production, VITE_API_URL points at the deployed
// backend directly. This file used to hardcode "/api/auth/login" here,
// bypassing that logic entirely — that was the actual bug behind login
// always 404ing in production even once everything else worked correctly.
const BASE = import.meta.env.VITE_API_URL || "/api";

function loadStoredAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(loadStoredAuth);

  const login = useCallback(async (username, password) => {
    const res = await fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data?.detail || "Login failed");
    }
    const session = {
      token: data.access_token,
      username: data.username,
      role: data.role,
      employeeId: data.employee_id,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    setAuth(session);
    return session;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setAuth(null);
  }, []);

  const canWrite = auth?.role === "admin";

  return (
    <AuthContext.Provider value={{ auth, login, logout, canWrite }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function getToken() {
  const stored = loadStoredAuth();
  return stored?.token || null;
}

export function clearStoredAuth() {
  localStorage.removeItem(STORAGE_KEY);
}
