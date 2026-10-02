"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Pause, Play } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { formatSeconds } from "@/lib/format";

export type VideoPlayerHandle = { seekTo: (seconds: number) => void };

type VideoPlayerProps = {
  src?: string;
  start: number | null;
  critical: number | null;
  end: number | null;
};

function safeVideoTime(value: number, video: HTMLVideoElement): number | null {
  if (!Number.isFinite(value)) return null;
  const max = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : Infinity;
  return Math.min(Math.max(0, value), max);
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(function VideoPlayer({ src, start, critical, end }, ref) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);

  useImperativeHandle(ref, () => ({
    seekTo(seconds: number) {
      const video = videoRef.current;
      if (!video) return;
      const safeTime = safeVideoTime(seconds, video);
      if (safeTime === null) return;
      video.currentTime = safeTime;
      setCurrent(safeTime);
      void video.play().catch(() => undefined);
      setIsPlaying(true);
    },
  }), []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onTimeUpdate = () => setCurrent(video.currentTime);
    const onLoadedMetadata = () => setDuration(Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 0);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("loadedmetadata", onLoadedMetadata);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    return () => {
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("loadedmetadata", onLoadedMetadata);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
    };
  }, []);

  const hasMarkers = duration > 0 && start !== null && critical !== null && end !== null;
  const markerPosition = (value: number) => Math.min(100, Math.max(0, (value / duration) * 100));
  const incidentStart = hasMarkers ? markerPosition(start) : 0;
  const incidentEnd = hasMarkers ? markerPosition(end) : 0;
  const criticalPosition = hasMarkers ? markerPosition(critical) : 0;

  function togglePlay() {
    if (!videoRef.current) return;
    if (videoRef.current.paused) void videoRef.current.play();
    else videoRef.current.pause();
  }

  function seek(value: number) {
    const video = videoRef.current;
    if (!video) return;
    const safeTime = safeVideoTime(value, video);
    if (safeTime === null) return;
    video.currentTime = safeTime;
    setCurrent(safeTime);
  }

  return <div className="overflow-hidden rounded-2xl bg-vf-navy shadow-soft">
    <div className="relative aspect-video bg-[#080e1d]">
      <div className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/35 px-2.5 py-1.5 text-[10px] font-extrabold uppercase tracking-[0.1em] text-white backdrop-blur"><span className="h-1.5 w-1.5 rounded-full bg-red-400" /> Incident video</div>
      {src ? <video ref={videoRef} src={src} className="h-full w-full object-contain" playsInline preload="metadata" /> : <div className="flex h-full w-full items-center justify-center text-sm font-bold text-slate-500">Video preview unavailable</div>}
      {!isPlaying && src && <button type="button" aria-label="Play incident video" onClick={togglePlay} className="absolute left-1/2 top-1/2 flex h-14 w-14 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white text-vf-primary shadow-lg transition hover:scale-105"><Play className="ml-0.5 h-6 w-6" /></button>}
    </div>
    <div className="px-4 pb-3 pt-3 sm:px-5">
      <div className="relative mb-3 h-2">
        <div className="absolute top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-white/15" />
        {hasMarkers && <><div className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-vf-primary/60" style={{ left: `${incidentStart}%`, width: `${Math.max(0, incidentEnd - incidentStart)}%` }} /><div className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-amber-300" style={{ left: `${criticalPosition}%` }} /></>}
        <input aria-label="Video timeline" type="range" min={0} max={duration || 30} step={0.1} value={current} onChange={(event) => seek(Number(event.target.value))} className="absolute inset-0 h-2 w-full cursor-pointer opacity-0" />
      </div>
      <div className="flex items-center justify-between text-[10px] font-bold text-white/55"><span>{formatSeconds(current)}</span><span>{formatSeconds(duration || 30)}</span></div>
      <div className="mt-2 flex items-center justify-between"><Button variant="ghost" aria-label={isPlaying ? "Pause video" : "Play video"} onClick={togglePlay} className="min-h-8 px-1.5 text-white hover:bg-white/10 hover:text-white">{isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}<span className="text-[11px]">{isPlaying ? "Pause" : "Play"}</span></Button><span className="text-[10px] font-bold text-white/45">Click a marker or evidence timestamp to seek</span></div>
    </div>
  </div>;
});
