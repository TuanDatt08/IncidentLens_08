"use client";

import GalaxyCanvas from "./galaxy-canvas";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Film, FileText, Gauge } from "@/components/icons";

export function LensMark() {
  return <svg viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M20 3 35 11.5v17L20 37 5 28.5v-17L20 3Z" stroke="currentColor" strokeWidth="1.5" /><circle cx="20" cy="20" r="9" stroke="currentColor" strokeWidth="1.5" /><path d="M20 7v6m0 14v6M7 20h6m14 0h6" stroke="currentColor" /><circle cx="20" cy="20" r="3" fill="currentColor" /></svg>;
}

/** AI-generated illustrative still, never real incident footage. */
export function RoadIllustration({ selected = 0 }: { selected?: number }) {
  return <div className="lp-road lp-dashcam" role="img" aria-label="Ảnh dashcam tổng hợp bằng AI: xe phía trước trên đường. Minh họa, không phải footage sự cố thật." data-moment={selected}>
    {/* Local generated asset; a fixed illustration across all demo moments. */}
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src="/landing/dashcam-demo-v2.webp" alt="" width="1280" height="720" decoding="async" />
    <svg className="lp-dashcam-overlay" viewBox="0 0 600 338" fill="none" aria-hidden="true"><path d="M262 159v-9h14m76 0h13v9m0 64v10h-13m-76 0h-14v-10" stroke="#78edff" strokeWidth="1.5" /><path d="M255 145h117v94H255Z" stroke="#78edff" strokeDasharray="3 5" opacity=".35" /><path d="M20 20h18m-18 0v18m560-18h-18m18 0v18M20 318h18m-18 0v-18m560 18h-18m18 0v-18" stroke="#d6e7f5" opacity=".5" /></svg>
  </div>;
}


function GalaxyFallback() {
  const id = useId().replace(/:/g, "");
  return <div className="lp-galaxy-fallback" aria-hidden="true"><svg className="lp-galaxy-rings" viewBox="0 0 720 680" fill="none">
    <defs><radialGradient id={`${id}-celestial`} cx=".3" cy=".25"><stop className="lp-celestial-highlight" stopColor="#edf0f5" /><stop className="lp-celestial-mid" offset=".55" stopColor="#a5adbb" /><stop className="lp-celestial-edge" offset="1" stopColor="#3d4658" /></radialGradient><radialGradient id={`${id}-core`} cx=".3" cy=".25"><stop stopColor="#f4dfff" /><stop offset=".12" stopColor="#c4a2ff" /><stop offset=".38" stopColor="#8b5cf6" /><stop offset=".7" stopColor="#213673" /><stop offset=".92" stopColor="#102444" /><stop offset="1" stopColor="#22d3ee" /></radialGradient><radialGradient id={`${id}-halo`}><stop stopColor="#8b5cf6" stopOpacity=".5" /><stop offset=".6" stopColor="#8b5cf6" stopOpacity=".08" /><stop offset="1" stopColor="#8b5cf6" stopOpacity="0" /></radialGradient></defs>
    <circle cx="375" cy="340" r="230" fill={`url(#${id}-halo)`} />
    <g className="lp-galaxy-orbit"><ellipse cx="375" cy="340" rx="240" ry="82" transform="rotate(-24 375 340)" stroke="#22d3ee" strokeWidth="1.3" strokeOpacity=".7" /><ellipse cx="375" cy="340" rx="258" ry="108" transform="rotate(27 375 340)" stroke="#a684ff" strokeWidth="1.4" strokeOpacity=".65" /><ellipse cx="375" cy="340" rx="188" ry="77" transform="rotate(-68 375 340)" stroke="#e879f9" strokeOpacity=".45" /><circle cx="565" cy="255" r="4" fill="#a4f8ff" /><circle cx="148" cy="265" r="3" fill="#e879f9" /><circle cx="434" cy="470" r="4" fill="#c6acff" /></g>
    <g transform="translate(375 340) scale(1.35) translate(-375 -340)"><circle className="lp-celestial-body" cx="375" cy="340" r="91" fill={`url(#${id}-celestial)`} stroke="#91e9ff" strokeOpacity=".55" />
    <g className="lp-lunar-craters" fill="#646b78" stroke="#cbd0d9" strokeWidth="1.5" opacity=".6">
      <circle cx="344" cy="307" r="17" /><circle cx="399" cy="362" r="24" /><circle cx="350" cy="381" r="11" /><circle cx="411" cy="298" r="9" /><circle cx="381" cy="323" r="7" />
    </g>    </g>{[0, 1, 2, 3, 4, 5, 6, 7].map(n => <circle key={n} cx={90 + n * 77} cy={150 + (n * 83) % 390} r={n % 3 === 0 ? 2 : 1} fill={n % 2 ? "#22d3ee" : "#c6b2ff"} opacity=".7" />)}
  </svg></div>;
}

export function HeroScene() {
  const scene = useRef<HTMLDivElement>(null);
  const frame = useRef<number>();
  const pointerEnabled = useRef(false);
  const [loadCanvas, setLoadCanvas] = useState(true);
  const [canvasState, setCanvasState] = useState("static");
  const ready = useCallback(() => setCanvasState("ready"), []);
  const unavailable = useCallback(() => setCanvasState("fallback"), []);
  useEffect(() => {
    const element = scene.current;
    if (!element) return;
    const panels = Array.from(element.querySelectorAll<HTMLElement>(".lp-source"));
    const satellites = Array.from(element.querySelectorAll<HTMLElement>(".lp-space-satellite"));
    const motion = window.matchMedia("(prefers-reduced-motion: no-preference)");
    let visible = false;
    let animation: number | undefined;
    let previous = 0;
    let elapsed = 0;
    let width = element.clientWidth;
    let height = element.clientHeight;
    const paint = () => {
      const mobile = width < 450;
      panels.forEach((panel, index) => {
        const angle = elapsed / 48000 * Math.PI * 2 + [-2.45, -.35, 1.72][index];
        const depth = Math.sin(angle);
        const scale = .87 + (depth + 1) * .085;
        const radiusX = width * (mobile ? .235 : .32);
        const radiusY = height * (mobile ? .305 : .285);
        // A camera-facing ellipse leaves the core readable at both crossings.
        const x = Math.cos(angle) * radiusX;
        const y = Math.sin(angle) * radiusY;
        panel.style.setProperty("--orbit-x", `${x.toFixed(2)}px`);
        panel.style.setProperty("--orbit-y", `${y.toFixed(2)}px`);
        panel.style.setProperty("--orbit-scale", scale.toFixed(3));
        panel.style.setProperty("--orbit-tilt", `${(Math.cos(angle) * 4).toFixed(2)}deg`);
        panel.style.setProperty("--orbit-opacity", (.78 + (depth + 1) * .11).toFixed(3));
        panel.style.zIndex = depth > 0 ? "4" : "0";
      });
      satellites.forEach((satellite, index) => {
        // One shared period and evenly spaced phases keep satellites apart.
        const angle = elapsed / 48000 * Math.PI * 2 + Math.PI / 6 + index * Math.PI / 3;
        const inclination = 0;
        const a = Math.cos(angle) * width * .44;
        const b = Math.sin(angle) * height * .43;
        const depth = Math.sin(angle);
        satellite.style.setProperty("--sat-x", `${(a * Math.cos(inclination) - b * Math.sin(inclination)).toFixed(2)}px`);
        satellite.style.setProperty("--sat-y", `${(a * Math.sin(inclination) + b * Math.cos(inclination)).toFixed(2)}px`);
        satellite.style.setProperty("--sat-scale", (.7 + (depth + 1) * .18).toFixed(3));
        satellite.style.setProperty("--sat-tilt", `${(elapsed / 180 + index * 60).toFixed(1)}deg`);
        satellite.style.opacity = String(.55 + (depth + 1) * .2);
        satellite.style.zIndex = depth > 0 ? "3" : "0";
      });
    };
    const tick = (time: number) => {
      if (previous === 0) previous = time;
      if (time - previous >= 1000 / 30) {
        elapsed += Math.min(time - previous, 80);
        previous = time;
        paint();
      }
      animation = requestAnimationFrame(tick);
    };
    const sync = () => {
      if (animation !== undefined) cancelAnimationFrame(animation);
      animation = undefined;
      previous = 0;
      const active = visible && !document.hidden && motion.matches;
      element.dataset.orbiting = String(motion.matches);
      paint();
      if (active) animation = requestAnimationFrame(tick);
      if (!motion.matches) panels.forEach(panel => { panel.style.removeProperty("z-index"); });
    };
    const resize = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => { width = element.clientWidth; height = element.clientHeight; if (motion.matches) paint(); }) : undefined;
    resize?.observe(element);
    const observer = typeof IntersectionObserver !== "undefined" ? new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); }, { threshold: .02 }) : undefined;
    if (observer) observer.observe(element); else visible = true;
    motion.addEventListener("change", sync);
    document.addEventListener("visibilitychange", sync);
    sync();
    return () => { observer?.disconnect(); resize?.disconnect(); motion.removeEventListener("change", sync); document.removeEventListener("visibilitychange", sync); if (animation !== undefined) cancelAnimationFrame(animation); };
  }, []);
  useEffect(() => {
    const element = scene.current;
    if (!element) return;
    const fine = window.matchMedia("(pointer: fine)");
    const motion = window.matchMedia("(prefers-reduced-motion: no-preference)");
    const lowPower = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection?.saveData || (navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency < 4);
    let visible = false;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const sync = () => {
      pointerEnabled.current = fine.matches && motion.matches && visible && !document.hidden;
      element.dataset.active = String(visible && !document.hidden && motion.matches);
      if (!motion.matches) {
        if (frame.current) cancelAnimationFrame(frame.current);
        element.style.setProperty("--scene-x", "0deg"); element.style.setProperty("--scene-y", "0deg");
        setLoadCanvas(false); setCanvasState("static");
      }
      if (timeout) clearTimeout(timeout);
      if (visible && !document.hidden && motion.matches && !lowPower) setLoadCanvas(true);
    };
    const observer = typeof IntersectionObserver !== "undefined" ? new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); }, { rootMargin: "40px", threshold: .02 }) : undefined;
    if (observer) observer.observe(element); else { visible = true; sync(); }
    fine.addEventListener("change", sync); motion.addEventListener("change", sync); document.addEventListener("visibilitychange", sync);
    return () => { observer?.disconnect(); fine.removeEventListener("change", sync); motion.removeEventListener("change", sync); document.removeEventListener("visibilitychange", sync); if (timeout) clearTimeout(timeout); if (frame.current) cancelAnimationFrame(frame.current); };
  }, []);
  return <div ref={scene} className="lp-scene lp-galaxy-scene" data-active="false" data-canvas-state={canvasState} role="img" aria-label="Incident Analysis Core minh họa: video, telemetry và evidence hội tụ vào lõi sáng giữa các quỹ đạo dữ liệu. Kỹ sư kiểm tra và review." onPointerMove={event => {
    if (!pointerEnabled.current || event.pointerType === "touch") return;
    const element = event.currentTarget, rect = element.getBoundingClientRect();
    const x = Math.max(-1, Math.min(1, (event.clientX - rect.left) / rect.width * 2 - 1));
    const y = Math.max(-1, Math.min(1, (event.clientY - rect.top) / rect.height * 2 - 1));
    if (frame.current) cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => { element.style.setProperty("--scene-x", `${-y * 2}deg`); element.style.setProperty("--scene-y", `${x * 2.5}deg`); });
  }} onPointerLeave={() => { if (frame.current) cancelAnimationFrame(frame.current); scene.current?.style.setProperty("--scene-x", "0deg"); scene.current?.style.setProperty("--scene-y", "0deg"); }}>
    <div className="lp-galaxy-atmosphere"><GalaxyFallback />{loadCanvas && <GalaxyCanvas onReady={ready} onUnavailable={unavailable} />}</div>
    <div className="lp-space-satellite lp-space-crystal" data-kind="rock" aria-hidden="true"><i /><i /></div>
    <div className="lp-space-satellite lp-space-cube" aria-hidden="true"><i /></div>
    <div className="lp-space-satellite lp-space-probe" aria-hidden="true"><i /><b /><i /></div>
    <div className="lp-space-satellite lp-space-moon" aria-hidden="true" />
    <div className="lp-space-satellite lp-space-crystal lp-space-small" data-kind="rock" aria-hidden="true"><i /><i /></div>
    <div className="lp-space-satellite lp-space-cube lp-space-small" aria-hidden="true"><i /></div>
    <div className="lp-galaxy-core-label"><span className="lp-dot" /> INCIDENT ANALYSIS CORE<small>AI ASSISTED / HUMAN REVIEWED</small></div>
    <div className="lp-source lp-source-video"><div className="lp-source-title"><Film className="lp-icon" /><span>VIDEO</span><span className="lp-source-live">01</span></div><RoadIllustration /><div className="lp-source-foot"><span>FRAME / 06.8 s</span><span>DEMO MINH HỌA</span></div></div>
    <div className="lp-source lp-source-telemetry"><div className="lp-source-title"><Gauge className="lp-icon" /><span>TELEMETRY</span><span className="lp-source-live">02</span></div><svg viewBox="0 0 240 60" fill="none" aria-hidden="true"><path d="M0 15h240M0 30h240M0 45h240" stroke="#39436a" /><path d="m0 36 25-4 19 5 27-9 28 6 18-18 16 34 15-26 15 11 27-3 24 4 26-3" stroke="#22d3ee" strokeWidth="2" /><path d="M125 0v60" stroke="#c084fc" strokeDasharray="3 4" /></svg><div className="lp-source-foot"><span>CSV · TÙY CHỌN</span><span>DEMO</span></div></div>
    <div className="lp-source lp-source-evidence"><div className="lp-source-title"><FileText className="lp-icon" /><span>EVIDENCE</span><span className="lp-source-live">03</span></div><div className="lp-evidence-line"><i /><span>Frame · 06.8 s</span><span>↗</span></div><div className="lp-evidence-line"><i /><span>Clip · 04–09 s</span><span>↗</span></div><div className="lp-evidence-review"><span className="lp-dot" /> Cần kỹ sư review</div></div>
    <div className="lp-scene-caption"><span>INCIDENTLENS / DATA OBSERVATORY</span><span>CẢNH MINH HỌA</span></div>
  </div>;
}
