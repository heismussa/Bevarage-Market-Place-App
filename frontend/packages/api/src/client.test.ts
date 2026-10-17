import { afterEach, describe, expect, it, vi } from "vitest";

import { createApiClient } from "./client";
import { ApiError } from "./errors";
import { createMemoryTokenStore, setTokenStore } from "./tokens";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("createApiClient refresh", () => {
  it("refreshes once on TOKEN_INVALID and retries the request", async () => {
    const store = createMemoryTokenStore({
      access: "old-access",
      refresh: "refresh-token",
    });
    setTokenStore(store);

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = input instanceof Request ? input : new Request(String(input), init);
      const url = request.url;

      if (url.includes("/auth/refresh/")) {
        return new Response(
          JSON.stringify({ access: "new-access", refresh: "refresh-token" }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (url.includes("/stores/")) {
        const auth = request.headers.get("Authorization");
        if (auth === "Bearer old-access") {
          return new Response(
            JSON.stringify({
              error: {
                code: "TOKEN_INVALID",
                message: "Token is invalid or expired.",
                details: {},
              },
            }),
            { status: 401, headers: { "Content-Type": "application/json" } },
          );
        }
        if (auth === "Bearer new-access") {
          return new Response(
            JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
      }

      return new Response("not found", { status: 404 });
    });

    vi.stubGlobal("fetch", fetchMock);

    const client = createApiClient({
      baseUrl: "http://localhost:8000/api/v1",
    });

    const { data, error } = await client.GET("/api/v1/stores/");
    expect(error).toBeUndefined();
    expect(data).toMatchObject({ results: [] });
    expect(await store.getAccess()).toBe("new-access");
    expect(
      fetchMock.mock.calls.some((call) => String(call[0]).includes("/auth/refresh/")),
    ).toBe(true);
  });

  it("clears tokens and calls onSessionExpired when refresh fails", async () => {
    const store = createMemoryTokenStore({
      access: "old-access",
      refresh: "bad-refresh",
    });
    setTokenStore(store);
    const onSessionExpired = vi.fn();

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = input instanceof Request ? input : new Request(String(input), init);
        if (request.url.includes("/auth/refresh/")) {
          return new Response(
            JSON.stringify({
              error: {
                code: "TOKEN_INVALID",
                message: "Token is invalid or expired.",
                details: {},
              },
            }),
            { status: 401, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            error: {
              code: "TOKEN_INVALID",
              message: "Token is invalid or expired.",
              details: {},
            },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        );
      }),
    );

    const client = createApiClient({
      baseUrl: "http://localhost:8000/api/v1",
      onSessionExpired,
    });

    await expect(client.GET("/api/v1/stores/")).rejects.toBeInstanceOf(ApiError);
    expect(onSessionExpired).toHaveBeenCalled();
    expect(await store.getAccess()).toBeNull();
  });
});
