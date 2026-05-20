import { get, set, del } from "idb-keyval";
import type { PersistedClient, Persister } from "@tanstack/react-query-persist-client";
import type { Query } from "@tanstack/react-query";

const EXCLUDED_PREFIXES: string[][] = [
  ["ai", "chat"],
  ["users", "me"],
  ["admin-rbac"],
  ["role-assignments"],
];

function isExcludedKey(queryKey: unknown[]): boolean {
  return EXCLUDED_PREFIXES.some((prefix) => {
    if (queryKey.length < prefix.length) return false;
    return prefix.every((segment, i) => queryKey[i] === segment);
  });
}

export function shouldDehydrateQuery(query: Query): boolean {
  if (query.state.status !== "success") return false;
  if (isExcludedKey(query.queryKey as unknown[])) return false;
  return true;
}

export function createIDBPersister(idbValidKey: IDBValidKey = "reactQuery"): Persister {
  return {
    persistClient: async (client: PersistedClient) => {
      await set(idbValidKey, client);
    },
    restoreClient: async () => {
      return await get<PersistedClient>(idbValidKey);
    },
    removeClient: async () => {
      await del(idbValidKey);
    },
  };
}

let appPersister: Persister | null = null;

export function setAppPersister(p: Persister): void {
  appPersister = p;
}

export function getAppPersister(): Persister | null {
  return appPersister;
}
