import { describe, it, expect, vi, beforeEach } from "vitest";
import { requestPersistentStorage } from "../storagePersistence";

describe("requestPersistentStorage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls navigator.storage.persist and returns true when granted", async () => {
    Object.defineProperty(navigator, "storage", {
      value: { persist: vi.fn().mockResolvedValue(true) },
      writable: true,
      configurable: true,
    });

    const result = await requestPersistentStorage();
    expect(navigator.storage.persist).toHaveBeenCalledOnce();
    expect(result).toBe(true);
  });

  it("returns false when persistence is denied", async () => {
    Object.defineProperty(navigator, "storage", {
      value: { persist: vi.fn().mockResolvedValue(false) },
      writable: true,
      configurable: true,
    });

    const result = await requestPersistentStorage();
    expect(result).toBe(false);
  });

  it("returns false when navigator.storage is not available", async () => {
    Object.defineProperty(navigator, "storage", {
      value: undefined,
      writable: true,
      configurable: true,
    });

    const result = await requestPersistentStorage();
    expect(result).toBe(false);
  });

  it("returns false when persist throws an error", async () => {
    Object.defineProperty(navigator, "storage", {
      value: { persist: vi.fn().mockRejectedValue(new Error("not allowed")) },
      writable: true,
      configurable: true,
    });

    const result = await requestPersistentStorage();
    expect(result).toBe(false);
  });
});
