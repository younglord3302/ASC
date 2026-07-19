"use client";

// ─── Auth + API client ────────────────────────────────────────────────────
// Centralizes the JWT token (stored in localStorage) and wraps fetch so every
// request carries the Authorization header. A 401 clears the token so the app
// falls back to the login screen.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Convert a REST API base (http(s)) into a WebSocket base (ws(s)).
// The API base already includes the "/api/v1" prefix, which the WebSocket
// route also expects (e.g. /api/v1/ws/{id}), so we keep it.
export function deriveWsBase(apiBase: string): string {
  const base = apiBase.replace(/\/$/, "");
  if (base.startsWith("https://")) return "wss://" + base.slice("https://".length);
  if (base.startsWith("http://")) return "ws://" + base.slice("http://".length);
  return "ws://" + base;
}

export const WS_BASE: string = deriveWsBase(API_BASE);

export function wsUrl(path: string): string {
  return `${WS_BASE}${path}`;
}

const TOKEN_KEY = "asc_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export { ApiError };

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

async function handle(res: Response) {
  if (res.status === 401) {
    clearToken();
    // Notify listeners (the dashboard) that auth was lost.
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("asc:unauthorized"));
    }
    throw new ApiError(401, "Unauthorized");
  }
  if (!res.ok) {
    let detail = `API error: ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

export async function apiGet(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  return handle(res);
}

export async function apiPost(path: string, body?: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: body ? JSON.stringify(body) : undefined,
  });
  return handle(res);
}

// ─── Auth calls ─────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await handle(res);
  setToken(data.access_token);
  return data.access_token;
}

export async function register(
  email: string,
  password: string,
  fullName?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName || null }),
  });
  await handle(res);
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export async function fetchMe(): Promise<CurrentUser> {
  return apiGet("/auth/me");
}
