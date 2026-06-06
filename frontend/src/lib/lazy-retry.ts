import { lazy, ComponentType } from "react";

async function loadWithRetry<T>(
  importFn: () => Promise<T>,
  retriesLeft: number,
  interval: number
): Promise<T> {
  try {
    return await importFn();
  } catch (error: any) {
    // Check if it's a "Failed to fetch" error common with chunk loading
    const isChunkError =
      error.message?.includes("Failed to fetch dynamically imported module") ||
      error.message?.includes("Importing a module script failed");

    if (isChunkError) {
      // If it's a chunk error and we have retries, try again after interval
      if (retriesLeft > 0) {
        await new Promise((resolve) => setTimeout(resolve, interval));
        return loadWithRetry(importFn, retriesLeft - 1, interval * 2);
      }

      // If no retries left, force a full page reload to get the new index.html
      // and avoid a permanent crash. Use session storage to avoid infinite loop.
      const reloadKey = "vit_chunk_reload_count";
      const reloadCount = parseInt(sessionStorage.getItem(reloadKey) || "0", 10);

      if (reloadCount < 1) {
        sessionStorage.setItem(reloadKey, (reloadCount + 1).toString());
        window.location.reload();
        return new Promise(() => {}); // Never resolves, page is reloading
      }
    }

    throw error;
  }
}

/**
 * Enhanced lazy loader that retries imports when they fail (usually due to
 * new deployments where old asset hashes are no longer available).
 */
export function lazyRetry(
  importFn: () => Promise<{ default: ComponentType<any> }>,
  retriesLeft = 2,
  interval = 1000
): ReturnType<typeof lazy> {
  return lazy(() => loadWithRetry(importFn, retriesLeft, interval));
}
