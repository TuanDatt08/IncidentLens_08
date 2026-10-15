// Only diagnose transport after playback fails; never download the full video.
export async function mediaAccessFailure(src: string, signal?: AbortSignal): Promise<string | null> {
  try {
    const response = await fetch(src, { headers: { Range: "bytes=0-0" }, credentials: "same-origin", cache: "no-store", signal });
    await response.body?.cancel();
    if (response.status === 401 || response.status === 403) return "Video access was denied. Sign in with permission to read this incident. If sign-in is unavailable, ask the administrator to align frontend and backend authentication.";
    if (response.status === 404) return "The video is unavailable on the server. Ask the administrator to restore this incident's media storage.";
    if (!response.ok) return `The video server returned HTTP ${response.status}. Retry later or contact the administrator.`;
    if (!response.headers.get("Content-Type")?.toLowerCase().startsWith("video/")) return "The server did not return video media. Ask the administrator to check the media route and sign-in configuration.";
    return null;
  } catch {
    return signal?.aborted ? null : "Video access could not be checked. Check your connection and retry.";
  }
}
