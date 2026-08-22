import { api } from "../api";

/** Normalize any thrown value into an Error with a safe, user-facing message. */
function toUploadError(context: string, cause: unknown): Error {
  // Never forward raw exception text (stack fragments, SDK internals) to the UI.
  const error = new Error(context);
  if (cause instanceof Error) {
    (error as Error & { cause?: unknown }).cause = cause;
  }
  return error;
}

/** Service layer for file uploads — keeps hooks free of direct API calls. */
export const fileUploadService = {
  async uploadImage(file: File): Promise<{ url: string; file_name: string }> {
    try {
      return await api.uploadFile(file);
    } catch (cause) {
      throw toUploadError("Image upload failed", cause);
    }
  },

  async uploadToWiki(files: File[]): Promise<{ message: string }> {
    try {
      const result = await api.uploadWikiRawFiles(files);
      const names = (result.saved || []).map((s) => s.name).join(", ");
      let message =
        `Uploaded ${result.count} document(s) to docgraph/raw` +
        (names ? ` (${names})` : "") +
        ".";
      try {
        const sync = await api.syncWiki(false);
        if (sync.status === "error") {
          message += ` DocGraph Sync failed: ${sync.error || "Unknown error"}`;
        } else if (sync.status === "unchanged") {
          message += " No files changed.";
        } else {
          message += " Starting DocGraph Sync.";
        }
      } catch (syncErr) {
        const detail =
          syncErr instanceof Error ? syncErr.message : String(syncErr);
        message += ` Failed to start DocGraph Sync: ${detail}`;
      }
      return { message };
    } catch (cause) {
      throw toUploadError("DocGraph upload failed", cause);
    }
  },
};
