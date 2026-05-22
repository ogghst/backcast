import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  shouldDehydrateQuery,
  createIDBPersister,
} from "../queryPersister";
import type { Query } from "@tanstack/react-query";
import type { PersistedClient } from "@tanstack/react-query-persist-client";

vi.mock("idb-keyval", () => ({
  get: vi.fn().mockResolvedValue(undefined),
  set: vi.fn().mockResolvedValue(undefined),
  del: vi.fn().mockResolvedValue(undefined),
}));

function makeQuery(key: unknown[], status: string = "success"): Query {
  return {
    queryKey: key,
    state: { status } as Query["state"],
  } as unknown as Query;
}

describe("shouldDehydrateQuery", () => {
  it("excludes AI chat keys", () => {
    const query = makeQuery(["ai", "chat", "sessions"]);
    expect(shouldDehydrateQuery(query)).toBe(false);
  });

  it("excludes AI chat nested keys", () => {
    const query = makeQuery(["ai", "chat", "sessions", "paginated", 0, 10]);
    expect(shouldDehydrateQuery(query)).toBe(false);
  });

  it("allows AI provider keys (non-chat)", () => {
    const query = makeQuery(["ai", "providers", "list"]);
    expect(shouldDehydrateQuery(query)).toBe(true);
  });

  it("excludes users.me key", () => {
    const query = makeQuery(["users", "me"]);
    expect(shouldDehydrateQuery(query)).toBe(false);
  });

  it("allows other user keys", () => {
    const query = makeQuery(["users", "detail", "123"]);
    expect(shouldDehydrateQuery(query)).toBe(true);
  });

  it("excludes adminRbac keys", () => {
    const query = makeQuery(["admin-rbac", "roles", "list"]);
    expect(shouldDehydrateQuery(query)).toBe(false);
  });

  it("excludes roleAssignments keys", () => {
    const query = makeQuery(["role-assignments", "list", { userId: "u1" }]);
    expect(shouldDehydrateQuery(query)).toBe(false);
  });

  it("allows project keys", () => {
    const query = makeQuery(["projects", "detail", "p1"]);
    expect(shouldDehydrateQuery(query)).toBe(true);
  });

  it("allows WBE keys", () => {
    const query = makeQuery(["wbes", "detail", "w1"]);
    expect(shouldDehydrateQuery(query)).toBe(true);
  });

  it("allows cost element keys", () => {
    const query = makeQuery(["cost-elements", "detail", "ce1"]);
    expect(shouldDehydrateQuery(query)).toBe(true);
  });

  it("allows dashboard keys", () => {
    const query = makeQuery(["dashboard", "recent-activity", {}]);
    expect(shouldDehydrateQuery(query)).toBe(true);
  });

  it("allows forecast keys", () => {
    const query = makeQuery(["forecasts", "list", "ce1", {}]);
    expect(shouldDehydrateQuery(query)).toBe(true);
  });

  it("excludes queries with non-success status", () => {
    const query = makeQuery(["projects", "list", {}], "error");
    expect(shouldDehydrateQuery(query)).toBe(false);
  });

  it("excludes pending queries", () => {
    const query = makeQuery(["projects", "list", {}], "pending");
    expect(shouldDehydrateQuery(query)).toBe(false);
  });

  it("allows success queries with allowed keys", () => {
    const query = makeQuery(["projects", "list", {}], "success");
    expect(shouldDehydrateQuery(query)).toBe(true);
  });
});

describe("createIDBPersister", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns a persister with persistClient, restoreClient, and removeClient methods", () => {
    const persister = createIDBPersister();

    expect(typeof persister.persistClient).toBe("function");
    expect(typeof persister.restoreClient).toBe("function");
    expect(typeof persister.removeClient).toBe("function");
  });

  it("persistClient calls idb-keyval set with the given key and client data", async () => {
    const { set } = await import("idb-keyval");
    const persister = createIDBPersister("testKey");
    const clientData = {
      clientState: { queries: [], mutations: [] },
    } as unknown as PersistedClient;

    await persister.persistClient(clientData);

    expect(set).toHaveBeenCalledWith("testKey", clientData);
  });

  it("persistClient uses default key 'reactQuery' when no key provided", async () => {
    const { set } = await import("idb-keyval");
    const persister = createIDBPersister();
    const clientData = {
      clientState: { queries: [], mutations: [] },
    } as unknown as PersistedClient;

    await persister.persistClient(clientData);

    expect(set).toHaveBeenCalledWith("reactQuery", clientData);
  });

  it("restoreClient calls idb-keyval get with the given key", async () => {
    const { get } = await import("idb-keyval");
    const persister = createIDBPersister("myCache");

    await persister.restoreClient();

    expect(get).toHaveBeenCalledWith("myCache");
  });

  it("restoreClient returns the result from idb-keyval get", async () => {
    const { get } = await import("idb-keyval");
    const cachedData = { clientState: { queries: [] } };
    (get as ReturnType<typeof vi.fn>).mockResolvedValueOnce(cachedData);

    const persister = createIDBPersister("myCache");
    const result = await persister.restoreClient();

    expect(result).toEqual(cachedData);
  });

  it("removeClient calls idb-keyval del with the given key", async () => {
    const { del } = await import("idb-keyval");
    const persister = createIDBPersister("testKey");

    await persister.removeClient();

    expect(del).toHaveBeenCalledWith("testKey");
  });
});

describe("persister registry (setAppPersister/getAppPersister)", () => {
  it("getAppPersister returns null on a freshly loaded module", async () => {
    vi.resetModules();
    const { getAppPersister: freshGet } = await import("../queryPersister");
    expect(freshGet()).toBeNull();
  });

  it("getAppPersister returns the persister set by setAppPersister", async () => {
    vi.resetModules();
    const { setAppPersister: freshSet, getAppPersister: freshGet } =
      await import("../queryPersister");

    const mockPersister = {
      persistClient: async () => {},
      restoreClient: async () => undefined,
      removeClient: async () => {},
    };

    freshSet(mockPersister);
    expect(freshGet()).toBe(mockPersister);
  });

  it("setAppPersister overwrites a previously set persister", async () => {
    vi.resetModules();
    const { setAppPersister: freshSet, getAppPersister: freshGet } =
      await import("../queryPersister");

    const first = {
      persistClient: async () => {},
      restoreClient: async () => undefined,
      removeClient: async () => {},
    };
    const second = {
      persistClient: async () => {},
      restoreClient: async () => undefined,
      removeClient: async () => {},
    };

    freshSet(first);
    expect(freshGet()).toBe(first);

    freshSet(second);
    expect(freshGet()).toBe(second);
  });
});
