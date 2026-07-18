import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  getToken,
  setToken,
  clearToken,
  isAuthenticated,
  apiGet,
  apiPost,
  login,
  register,
  fetchMe,
  API_BASE,
  ApiError,
} from "@/lib/auth";

// jsdom provides window/localStorage. We stub fetch per-test.
function mockFetch(body: unknown, status = 200, ok = status >= 200 && status < 300) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  });
}

describe("auth token storage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("round-trips a token", () => {
    expect(getToken()).toBeNull();
    expect(isAuthenticated()).toBe(false);
    setToken("abc");
    expect(getToken()).toBe("abc");
    expect(isAuthenticated()).toBe(true);
    clearToken();
    expect(getToken()).toBeNull();
  });

  it("validates the ApiError carries its status", () => {
    const err = new ApiError(401, "nope");
    expect(err.status).toBe(401);
    expect(err.message).toBe("nope");
  });
});

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("attaches the bearer token when present", async () => {
    setToken("tok-123");
    const fetchMock = mockFetch({ hello: "world" });
    vi.stubGlobal("fetch", fetchMock);
    const data = await apiGet("/thing");
    expect(data).toEqual({ hello: "world" });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer tok-123");
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/thing`);
  });

  it("posts JSON with content-type and auth", async () => {
    setToken("tok-123");
    const fetchMock = mockFetch({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    await apiPost("/thing", { a: 1 });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ a: 1 }));
  });

  it("clears the token and throws on 401", async () => {
    setToken("tok-123");
    const fetchMock = mockFetch({ detail: "expired" }, 401, false);
    vi.stubGlobal("fetch", fetchMock);
    await expect(apiGet("/protected")).rejects.toMatchObject({
      status: 401,
    });
    expect(getToken()).toBeNull();
  });

  it("surfaces non-401 API error details", async () => {
    const fetchMock = mockFetch({ detail: "bad input" }, 422, false);
    vi.stubGlobal("fetch", fetchMock);
    await expect(apiPost("/x")).rejects.toThrow("bad input");
  });
});

describe("auth flows", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("login stores the returned access token", async () => {
    const fetchMock = mockFetch({ access_token: "jwt-token" });
    vi.stubGlobal("fetch", fetchMock);
    const tok = await login("u@e.com", "pw");
    expect(tok).toBe("jwt-token");
    expect(getToken()).toBe("jwt-token");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE}/auth/login`);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ email: "u@e.com", password: "pw" });
  });

  it("register posts the expected payload", async () => {
    const fetchMock = mockFetch({ id: "1" });
    vi.stubGlobal("fetch", fetchMock);
    await register("u@e.com", "pw", "Bugsy");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE}/auth/register`);
    expect(JSON.parse(init.body)).toEqual({
      email: "u@e.com",
      password: "pw",
      full_name: "Bugsy",
    });
  });

  it("fetchMe calls the protected /auth/me endpoint", async () => {
    setToken("tok");
    const user = { id: "1", email: "u@e.com", full_name: "Bugsy", is_active: true };
    const fetchMock = mockFetch(user);
    vi.stubGlobal("fetch", fetchMock);
    const me = await fetchMe();
    expect(me).toEqual(user);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE}/auth/me`);
    expect(init.headers.Authorization).toBe("Bearer tok");
  });
});
