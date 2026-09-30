export function toVideoTime(
  relativeTime: number,
  collisionOffset: number | null | undefined,
  duration?: number | null,
): number | null {
  if (!Number.isFinite(relativeTime) || collisionOffset == null || !Number.isFinite(collisionOffset) || collisionOffset < 0) {
    return null;
  }
  const videoTime = collisionOffset + relativeTime;
  if (!Number.isFinite(videoTime)) return null;
  const max = duration != null && Number.isFinite(duration) && duration > 0 ? duration : Infinity;
  return Math.min(Math.max(0, videoTime), max);
}
