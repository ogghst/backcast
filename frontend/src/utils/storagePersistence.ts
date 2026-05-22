export async function requestPersistentStorage(): Promise<boolean> {
  try {
    if (!navigator.storage?.persist) {
      return false;
    }
    const granted = await navigator.storage.persist();
    console.log(`[StoragePersistence] navigator.storage.persist() granted: ${granted}`);
    return granted;
  } catch (error) {
    console.warn("[StoragePersistence] navigator.storage.persist() failed:", error);
    return false;
  }
}
