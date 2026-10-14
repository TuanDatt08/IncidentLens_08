"use client";

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState, type KeyboardEvent } from "react";
import { Maximize, Minimize, Pause, Play, Volume, VolumeOff } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { formatSeconds } from "@/lib/format";

export type VideoPlayerHandle = { seekTo: (seconds: number, autoplay?: boolean) => void; pause: () => void };
export type VideoPlaybackState = { currentTime: number; duration: number; ready: boolean };

type VideoPlayerProps = {
  src?: string;
  ariaLabel?: string;
  start: number | null;
  critical: number | null;
  end: number | null;
  onPlaybackChange?: (state: VideoPlaybackState) => void;
};

export function mediaFailureMessage(code?: number): string {
  if (code === 3 || code === 4) return "This browser could not decode the video, or its format is unsupported. Try a compatible browser or ask for an H.264/AAC MP4 copy. Retrying may not resolve a codec issue.";
  if (code === 2) return "Video could not be downloaded. Check your connection and access, then retry.";
  return "Video could not be loaded. Check access and connection, then retry.";
}

function safeVideoTime(value: number, video: HTMLVideoElement): number | null {
  if (!Number.isFinite(value)) return null;
  const max = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : Infinity;
  return Math.min(Math.max(0, value), max);
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(function VideoPlayer({ src, start, critical, end, ariaLabel = "Incident video", onPlaybackChange }, ref) {
  const overlayRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [fullscreen, setFullscreen] = useState(false);
  const [buffered, setBuffered] = useState<{ start: number; end: number }[]>([]);
  const [controlError, setControlError] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [metadataReady, setMetadataReady] = useState(false);
  const [mediaError, setMediaError] = useState("");
  const [playError, setPlayError] = useState("");
  const pendingSeek = useRef<{ seconds: number; play: boolean }>();
  const playbackAttempt = useRef(0);
  const playInFlight = useRef(false);

  useEffect(() => {
    onPlaybackChange?.({ currentTime: current, duration, ready: metadataReady && !mediaError });
  }, [current, duration, metadataReady, mediaError, onPlaybackChange]);

  const stopPlaybackState = useCallback(() => {
    playbackAttempt.current++;
    playInFlight.current = false;
    setIsPlaying(false);

  }, []);

  const requestPlay = useCallback(async () => {
    const video = videoRef.current;
    if (!video || video.error || playInFlight.current) return;
    const attempt = ++playbackAttempt.current;
    playInFlight.current = true;
    setPlayError("");
    try {
      await video.play();
    } catch (cause) {
      if (attempt !== playbackAttempt.current) return;
      setIsPlaying(false);
      setPlayError(cause instanceof Error && cause.name === "NotAllowedError" ? "Playback was blocked. Press Play to try again." : "Video could not start playing. Press Play to try again.");
    } finally {
      if (attempt === playbackAttempt.current) playInFlight.current = false;
    }
  }, []);

  const applyPendingSeek = useCallback(() => {
    const video = videoRef.current;
    const target = pendingSeek.current;
    if (!video || !target || video.readyState < 1 || video.error) return;
    const safeTime = safeVideoTime(target.seconds, video);
    if (safeTime === null) { pendingSeek.current = undefined; return; }
    try {
      video.currentTime = safeTime;
      pendingSeek.current = undefined;
      setCurrent(safeTime);
      if (target.play) void requestPlay();
    } catch {
      setMediaError("The video could not seek. Retry the video to load the selected timestamp.");
    }
  }, [requestPlay]);

  useImperativeHandle(ref, () => ({
    pause() {
      pendingSeek.current = undefined;
      videoRef.current?.pause();
      stopPlaybackState();
    },
    seekTo(seconds: number, autoplay = true) {
      if (!src || !Number.isFinite(seconds)) return;
      pendingSeek.current = { seconds, play: autoplay };
      applyPendingSeek();
    },
  }), [src, applyPendingSeek, stopPlaybackState]);

  useEffect(() => {
    const attemptRef = playbackAttempt;
    stopPlaybackState();
    pendingSeek.current = undefined;
    setBuffered([]); setControlError("");
    setCurrent(0); setDuration(0); setMetadataReady(false); setMediaError(""); setPlayError("");
    return () => {
      attemptRef.current++;
      playInFlight.current = false;
      pendingSeek.current = undefined;
    };
  }, [src, stopPlaybackState]);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const changed = () => setFullscreen(document.fullscreenElement === containerRef.current);
    document.addEventListener("fullscreenchange", changed);
    return () => document.removeEventListener("fullscreenchange", changed);
  }, []);

  function updateBuffered() {
    const video = videoRef.current;
    if (!video) return;
    const ranges: { start: number; end: number }[] = [];
    for (let index = 0; index < (video.buffered?.length ?? 0); index++) ranges.push({ start: video.buffered.start(index), end: video.buffered.end(index) });
    setBuffered(ranges);
  }

  function setAudio(next: number) {
    const video = videoRef.current;
    if (!video) return;
    video.volume = Math.min(1, Math.max(0, next));
    video.muted = video.volume === 0;
    setVolume(video.volume); setMuted(video.muted);
  }

  function toggleMute() {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    if (!video.muted && video.volume === 0) video.volume = 0.5;
    setMuted(video.muted); setVolume(video.volume);
  }

  async function toggleFullscreen() {
    const container = containerRef.current;
    if (!container || typeof document === "undefined") return;
    setControlError("");
    try {
      if (document.fullscreenElement === container) await document.exitFullscreen();
      else if (container.requestFullscreen) await container.requestFullscreen();
      else setControlError("Fullscreen is unavailable in this browser.");
    } catch { setControlError("Fullscreen could not open. Try again using the fullscreen button."); }
  }

  function shortcuts(event: KeyboardEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (event.altKey || event.ctrlKey || event.metaKey || target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT", "BUTTON", "A"].includes(target.tagName)) return;
    const video = videoRef.current;
    if (!src || !video || mediaError) return;
    switch (event.key.toLowerCase()) {
      case " ": case "k": togglePlay(); break;
      case "j": seek(video.currentTime - 10); break;
      case "l": seek(video.currentTime + 10); break;
      case "arrowleft": seek(video.currentTime - 5); break;
      case "arrowright": seek(video.currentTime + 5); break;
      case "arrowup": setAudio(video.volume + 0.1); break;
      case "arrowdown": setAudio(video.volume - 0.1); break;
      case "m": toggleMute(); break;
      case "f": void toggleFullscreen(); break;
      default: return;
    }
    event.preventDefault();
  }

  function loadedMetadata() {
    const video = videoRef.current;
    if (!video || video.readyState < 1) return;
    setDuration(Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 0);
    setMetadataReady(true);
    video.volume = volume; video.muted = muted; video.playbackRate = speed;
    updateBuffered();
    applyPendingSeek();
  }

  function retryVideo() {
    const video = videoRef.current;
    if (!video) return;
    stopPlaybackState();
    setMediaError(""); setPlayError(""); setMetadataReady(false); setDuration(0);
    try { video.load(); }
    catch {  setMediaError("Video could not be loaded. Check your connection and retry."); }
  }

  const hasMarkers = duration > 0 && start !== null && critical !== null && end !== null;
  const markerPosition = (value: number) => Math.min(100, Math.max(0, (value / duration) * 100));
  const incidentStart = hasMarkers ? markerPosition(start) : 0;
  const incidentEnd = hasMarkers ? markerPosition(end) : 0;
  const criticalPosition = hasMarkers ? markerPosition(critical) : 0;

  function togglePlay() {
    if (!videoRef.current) return;
    if (videoRef.current.paused) void requestPlay();
    else { videoRef.current.pause(); stopPlaybackState(); }
  }

  function seek(value: number) {
    const video = videoRef.current;
    if (!video || video.readyState < 1 || video.error) return;
    const safeTime = safeVideoTime(value, video);
    if (safeTime === null) return;
    pendingSeek.current = { seconds: safeTime, play: false };
    applyPendingSeek();
  }

  const controlsDisabled = !src || !!mediaError;
  const progress = duration > 0 ? markerPosition(current) : 0;
  const controlClass = "video-player-control inline-flex min-h-8 min-w-8 items-center justify-center rounded-lg text-white transition hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-300 disabled:opacity-40";

  return <div ref={containerRef} role="region" aria-label="Video player" data-playing={isPlaying} data-control-error={Boolean(mediaError || playError || controlError)} aria-keyshortcuts="Space K J L ArrowLeft ArrowRight ArrowUp ArrowDown M F" tabIndex={0} onKeyDown={shortcuts} className="video-player overflow-hidden rounded-2xl bg-[#101d2b] text-white shadow-soft outline-none focus-visible:ring-2 focus-visible:ring-teal-400">
    <div className="video-player-stage relative aspect-video bg-[#080e1d]">
      <div className="absolute left-4 top-4 z-10 hidden sm:flex items-center gap-2 rounded-full bg-black/35 px-2.5 py-1.5 text-[10px] font-medium text-white backdrop-blur"><span className="h-1.5 w-1.5 rounded-full bg-teal-400" /> Incident video</div>
      {src ? <video ref={videoRef} src={src} aria-label={ariaLabel} onClick={togglePlay} className="h-full w-full object-cover object-center" playsInline preload="metadata"
        onProgress={updateBuffered}
        onVolumeChange={() => { if (videoRef.current) { setVolume(videoRef.current.volume); setMuted(videoRef.current.muted); } }}
        onRateChange={() => { if (videoRef.current) setSpeed(videoRef.current.playbackRate); }}
        onTimeUpdate={() => { if (videoRef.current) setCurrent(videoRef.current.currentTime); }}
        onLoadedMetadata={loadedMetadata} onDurationChange={loadedMetadata}
        onPlay={() => {
          if (typeof document !== "undefined" && overlayRef.current && document.activeElement === overlayRef.current) containerRef.current?.focus({ preventScroll: true });
          setIsPlaying(true);
        }}
        onPlaying={() => { setIsPlaying(true);  setPlayError(""); }}
        onPause={stopPlaybackState} onEnded={stopPlaybackState}
        onCanPlay={() => {  applyPendingSeek(); }}
        onEmptied={() => { stopPlaybackState(); setMetadataReady(false); setDuration(0); setCurrent(0); }}
        onError={(event) => { stopPlaybackState(); setMetadataReady(false); setMediaError(mediaFailureMessage(event.currentTarget.error?.code)); }}
      /> : <div className="flex h-full w-full items-center justify-center text-sm font-medium text-slate-500">Video preview unavailable</div>}
      {src && !mediaError && !metadataReady && <p role="status" className="pointer-events-none absolute right-4 top-4 rounded-lg bg-black/35 px-2.5 py-1.5 text-xs text-white/80">Loading video...</p>}
      {!isPlaying && src && !mediaError && <button ref={overlayRef} type="button" aria-label="Play incident video" onClick={togglePlay} className="absolute left-1/2 top-1/2 flex h-12 w-12 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-teal-400 text-[#08232b] shadow-lg transition-colors hover:bg-teal-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-200 disabled:opacity-50"><Play className="ml-0.5 h-6 w-6" /></button>}
    </div>
    <div className="video-player-controls px-3 pb-2 pt-1 sm:px-4">
      {mediaError && <div className="mb-3 flex flex-wrap items-center gap-3"><p role="alert" className="text-xs font-semibold text-red-200">{mediaError}</p><Button variant="ghost" onClick={retryVideo} className="text-white hover:bg-white/10 hover:text-white">Retry video</Button></div>}
      {playError && !mediaError && <p role="alert" className="mb-3 text-xs font-semibold text-red-200">{playError}</p>}
      {controlError && <p role="alert" className="mb-3 text-xs text-amber-200">{controlError}</p>}
      <div className="video-player-timeline relative flex h-6 items-center">
        <div className="pointer-events-none absolute h-[3px] w-full overflow-hidden rounded-full bg-white/15">
          {duration > 0 && buffered.map((range, index) => <span key={index} className="absolute h-full bg-white/25" style={{ left: `${markerPosition(range.start)}%`, width: `${Math.max(0, markerPosition(range.end) - markerPosition(range.start))}%` }} />)}
          {hasMarkers && <span className="absolute h-full bg-teal-600/60" style={{ left: `${incidentStart}%`, width: `${Math.max(0, incidentEnd - incidentStart)}%` }} />}
          <span className="absolute h-full bg-teal-400" style={{ width: `${progress}%` }} />
        </div>
        {hasMarkers && <span className="pointer-events-none absolute h-2 w-px bg-amber-200/70" style={{ left: `${criticalPosition}%` }} title="Critical incident timestamp" />}
        <input aria-label="Video timeline" aria-valuetext={`${formatSeconds(current)} of ${duration > 0 ? formatSeconds(duration) : "duration unavailable"}`} disabled={controlsDisabled || !metadataReady || !duration} type="range" min={0} max={duration || 0} step={0.1} value={Math.min(current, duration)} onChange={(event) => seek(Number(event.target.value))} className="video-player-seek relative h-6 w-full cursor-pointer accent-teal-400" />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
        <div className="flex min-w-0 flex-wrap items-center gap-1">
          <Button variant="ghost" disabled={controlsDisabled} aria-label={isPlaying ? "Pause video" : "Play video"} onClick={togglePlay} className={controlClass}>{isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}<span className="sr-only">{isPlaying ? "Pause" : "Play"}</span></Button>
          <button type="button" disabled={controlsDisabled} onClick={toggleMute} aria-label={muted || volume === 0 ? "Unmute video" : "Mute video"} className={controlClass}>{muted || volume === 0 ? <VolumeOff className="h-5 w-5" /> : <Volume className="h-5 w-5" />}</button>
          <input aria-label="Video volume" type="range" min={0} max={1} step={0.05} disabled={controlsDisabled} value={muted ? 0 : volume} onChange={(event) => setAudio(Number(event.target.value))} className="video-player-volume h-8 w-16 cursor-pointer accent-teal-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-300 sm:w-20" />
          <span className="whitespace-nowrap px-1 text-xs font-medium tabular-nums text-white/75">{formatSeconds(current)} / {duration > 0 ? formatSeconds(duration) : "--:--"}</span>
        </div>
        <div className="flex items-center gap-1">
          <select aria-label="Playback speed" disabled={controlsDisabled} value={speed} onChange={(event) => { const next = Number(event.target.value); if (videoRef.current) videoRef.current.playbackRate = next; setSpeed(next); }} className="video-player-control min-h-8 rounded-lg border border-white/15 bg-[#101d2b] px-2 text-xs font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-300">{[0.25, 0.5, 0.75, 1, 1.25, 1.5, 2].map((value) => <option key={value} value={value}>{value === 1 ? "Normal" : `${value}x`}</option>)}</select>
          <button type="button" disabled={controlsDisabled} aria-label={fullscreen ? "Exit fullscreen" : "Enter fullscreen"} onClick={() => void toggleFullscreen()} className={controlClass}>{fullscreen ? <Minimize className="h-5 w-5" /> : <Maximize className="h-5 w-5" />}</button>
        </div>
      </div>
      <p className="sr-only">Focus player: K play/pause / J L seek / M mute / F fullscreen</p>
    </div>
  </div>;
});
