"use client";

import Link from "next/link";
import { WorkspaceTheme } from "@/components/layout/workspace-theme";
import { useEffect, useRef } from "react";
import { ArrowRight, Check, Film, FileText, Gauge, Lock } from "@/components/icons";
import { HeroScene, LensMark } from "./landing-visuals";
import { LandingDemo } from "./landing-demo";
import { GalaxyHandoff, GalaxyWorkflow } from "./galaxy-story";

function scrollToSection(event: React.MouseEvent<HTMLAnchorElement>) {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const hash = event.currentTarget.hash;
  const target = hash ? document.getElementById(hash.slice(1)) : undefined;
  if (!target) return;
  event.preventDefault();
  history.replaceState(history.state, "", hash);
  target.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start" });
  target.focus({ preventScroll: true });
}

function LandingNav() {
  const header = useRef<HTMLElement>(null);
  const menu = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const sync = () => { if (header.current) header.current.dataset.scrolled = String(window.scrollY > 24); };
    const outside = (event: PointerEvent) => { if (menu.current?.open && !menu.current.contains(event.target as Node)) menu.current.open = false; };
    window.addEventListener("scroll", sync, { passive: true });
    document.addEventListener("pointerdown", outside);
    sync();
    return () => { window.removeEventListener("scroll", sync); document.removeEventListener("pointerdown", outside); };
  }, []);
  const closeAndScroll = (event: React.MouseEvent<HTMLAnchorElement>) => { if (menu.current) menu.current.open = false; scrollToSection(event); };
  return <header ref={header} className="lp-nav" data-scrolled="false"><div className="lp-nav-inner">
    <a href="#dau-trang" className="lp-brand" onClick={scrollToSection} aria-label="IncidentLens — đầu trang"><LensMark /><span>Incident<span>Lens</span><small>INTELLIGENCE IN CONTEXT</small></span></a>
    <nav className="lp-nav-desktop" aria-label="Điều hướng landing page"><a href="#trai-nghiem" onClick={scrollToSection}>Trải nghiệm</a><a href="#quy-trinh" onClick={scrollToSection}>Quy trình</a><a href="#nang-luc" onClick={scrollToSection}>Năng lực</a></nav>
    <WorkspaceTheme />
    <Link href="/incidents" className="lp-nav-cta">Mở workspace <ArrowRight className="lp-icon" /></Link>
    <details ref={menu} className="lp-mobile-menu" onKeyDown={event => { if (event.key === "Escape" && menu.current?.open) { menu.current.open = false; menu.current.querySelector("summary")?.focus(); event.stopPropagation(); } }}><summary aria-label="Menu điều hướng"><span /><span /></summary><nav aria-label="Điều hướng mobile"><a href="#trai-nghiem" onClick={closeAndScroll}>Trải nghiệm</a><a href="#quy-trinh" onClick={closeAndScroll}>Quy trình</a><a href="#nang-luc" onClick={closeAndScroll}>Năng lực</a><Link href="/incidents" onClick={() => { if (menu.current) menu.current.open = false; }}>Mở workspace <ArrowRight className="lp-icon" /></Link></nav></details>
  </div></header>;
}

export function LandingPage() {
  const page = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = page.current;
    if (!root) return;
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)");
    const motion = window.matchMedia("(prefers-reduced-motion: no-preference)");
    const surfaces = ".lp-demo,.lp-workflow-console,.lp-feature-primary,.lp-feature-secondary,.lp-final-layout";
    let active: HTMLElement | null = null;
    let frame: number | undefined;
    const clear = () => { active?.style.setProperty("--glow-strength", "0"); active = null; if (frame !== undefined) cancelAnimationFrame(frame); frame = undefined; };
    const move = (event: PointerEvent) => {
      if (!fine.matches || !motion.matches || event.pointerType === "touch") return;
      const target = (event.target as Element).closest<HTMLElement>(surfaces);
      if (!target || !root.contains(target)) { clear(); return; }
      if (active !== target) { clear(); active = target; }
      if (frame !== undefined) cancelAnimationFrame(frame);
      const x = event.clientX, y = event.clientY;
      frame = requestAnimationFrame(() => {
        frame = undefined;
        const bounds = target.getBoundingClientRect();
        target.style.setProperty("--glow-x", `${x - bounds.left}px`);
        target.style.setProperty("--glow-y", `${y - bounds.top}px`);
        target.style.setProperty("--glow-strength", "1");
      });
    };
    const visibility = () => { if (document.hidden) clear(); };
    root.addEventListener("pointermove", move);
    root.addEventListener("pointerleave", clear);
    fine.addEventListener("change", clear);
    motion.addEventListener("change", clear);
    document.addEventListener("visibilitychange", visibility);
    return () => { clear(); root.removeEventListener("pointermove", move); root.removeEventListener("pointerleave", clear); fine.removeEventListener("change", clear); motion.removeEventListener("change", clear); document.removeEventListener("visibilitychange", visibility); };
  }, []);
  useEffect(() => {
    const visibility = () => { if (page.current) page.current.dataset.pageActive = String(!document.hidden); };
    document.addEventListener("visibilitychange", visibility);
    visibility();
    const spaceSurfaces = page.current?.querySelectorAll<HTMLElement>(".lp-demo, .lp-workflow-console, .lp-feature-layout, .lp-handoff, .lp-final");
    const spaceObserver = typeof IntersectionObserver !== "undefined" ? new IntersectionObserver(entries => entries.forEach(entry => { (entry.target as HTMLElement).dataset.spaceActive = String(entry.isIntersecting); }), { rootMargin: "40px" }) : undefined;
    spaceSurfaces?.forEach(element => { element.dataset.spaceActive = "false"; spaceObserver?.observe(element); });
    const elements = page.current?.querySelectorAll<HTMLElement>("[data-reveal]");
    if (!elements || typeof IntersectionObserver === "undefined") return () => { spaceObserver?.disconnect(); document.removeEventListener("visibilitychange", visibility); };
    const observer = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) { (entry.target as HTMLElement).dataset.revealed = "true"; observer.unobserve(entry.target); } }), { threshold: .12 });
    elements.forEach(element => observer.observe(element));
    return () => { observer.disconnect(); spaceObserver?.disconnect(); document.removeEventListener("visibilitychange", visibility); };
  }, []);
  return <div ref={page} className="landing landing-galaxy" data-page-active="true" lang="vi" id="dau-trang" tabIndex={-1}>
    <div className="lp-space-backdrop" aria-hidden="true"><div className="lp-stars-far" /><div className="lp-stars-near" /><div className="lp-nebula-page" /></div>
    <a className="lp-skip" href="#noi-dung">Đến nội dung chính</a>
    <LandingNav />
    <main id="noi-dung" tabIndex={-1}>
      <section className="lp-hero" aria-labelledby="lp-title">
        <div className="lp-hero-grid" aria-hidden="true" />
        <div className="lp-container lp-hero-layout">
          <div className="lp-hero-copy"><div className="lp-eyebrow lp-hero-eyebrow"><span className="lp-dot" /> INCIDENTLENS / DATA OBSERVATORY <span className="lp-eyebrow-line" /></div>
            <h1 id="lp-title">Một sự cố.<br /><span>Nhiều góc nhìn.</span></h1>
            <p className="lp-hero-description">Phân tích video, đối chiếu telemetry khi có và tập hợp bằng chứng. AI tạo bản nháp báo cáo để kỹ sư kiểm tra, chỉnh sửa và review.</p>
            <div className="lp-hero-actions"><Link href="/incidents" className="lp-button lp-button-primary">Khám phá hệ thống <ArrowRight className="lp-icon" /></Link><a href="#quy-trinh" onClick={scrollToSection} className="lp-button lp-button-secondary"><span className="lp-play-icon" aria-hidden="true">▷</span> Xem quy trình</a></div>
            <div className="lp-hero-note"><span className="lp-note-mark"><Check className="lp-icon" /></span><span>AI hỗ trợ phân tích.<br /><strong>Con người kiểm tra và quyết định.</strong></span></div>
          </div>
          <HeroScene />
        </div>
        <div className="lp-container lp-hero-baseline"><span>VIDEO <i>+</i> TELEMETRY <i>→</i> EVIDENCE <i>→</i> HUMAN REVIEW</span><a href="#trai-nghiem" onClick={scrollToSection}>Cuộn để khám phá <span aria-hidden="true">↓</span></a></div>
      </section>

      <GalaxyHandoff />

      <section className="lp-section lp-demo-section" id="trai-nghiem" tabIndex={-1} aria-labelledby="lp-demo-title"><div className="lp-container">
        <div className="lp-section-heading" data-reveal><div><p className="lp-eyebrow"><span>01</span> / MỘT GÓC NHÌN, ĐỦ NGỮ CẢNH</p><h2 id="lp-demo-title">Đi sâu vào từng mốc.<br /><span>Đọc rõ từng bằng chứng.</span></h2></div><p>Chọn một mốc để xem video, tín hiệu và evidence trong cùng bối cảnh. Đây là demo tổng hợp, không phải kết quả phân tích thực tế.</p></div>
        <div data-reveal><LandingDemo /></div>
        <div className="lp-demo-under"><span><span className="lp-dot" /> DEMO MINH HỌA · KHÔNG DÙNG DỮ LIỆU THẬT</span><span>Từ quan sát đến review, luôn có bước kiểm tra.</span></div>
      </div></section>

      <section className="lp-section lp-workflow" id="quy-trinh" tabIndex={-1} aria-labelledby="lp-workflow-title"><div className="lp-container">
        <div className="lp-section-heading" data-reveal><div><p className="lp-eyebrow"><span>02</span> / TỪ ĐẦU VÀO ĐẾN REVIEW</p><h2 id="lp-workflow-title">Một luồng rõ ràng.<br /><span>Không bỏ qua con người.</span></h2></div><p>AI giúp tập hợp thông tin. Kỹ sư giữ quyền kiểm tra bằng chứng, chỉnh sửa báo cáo và đưa ra quyết định review.</p></div>
        <GalaxyWorkflow />
        <div className="lp-workflow-note"><Lock className="lp-icon" /><p>Bản nháp AI là điểm bắt đầu, không phải kết luận cuối cùng về sự cố.</p></div>
      </div></section>

      <section className="lp-section lp-capabilities" id="nang-luc" tabIndex={-1} aria-labelledby="lp-capabilities-title"><div className="lp-container">
        <div className="lp-section-heading" data-reveal><div><p className="lp-eyebrow"><span>03</span> / WORKSPACE CHO KỸ SƯ</p><h2 id="lp-capabilities-title">Dữ liệu thành ngữ cảnh.<br /><span>Ngữ cảnh thành góc nhìn.</span></h2></div><p>Tập trung vào những thao tác cần thiết để đi từ dữ liệu đầu vào đến một báo cáo đã được kiểm tra.</p></div>
        <div className="lp-feature-layout">
          <article className="lp-feature-primary" data-reveal><div className="lp-feature-icon"><Film className="lp-icon" /></div><p className="lp-eyebrow">INCIDENT MANAGEMENT</p><h3>Mỗi sự cố.<br />Một workspace.</h3><p>Quản lý danh sách sự cố, theo dõi tiến trình phân tích và mở lại dữ liệu để tiếp tục kiểm tra.</p><div className="lp-mini-list" aria-label="Danh sách sự cố minh họa"><div><span className="lp-mini-list-id">INC-DEMO-01</span><span className="lp-mini-status">Bản nháp</span></div><div><span className="lp-mini-list-id">INC-DEMO-02</span><span className="lp-mini-status lp-mini-status-review">Đang review</span></div><div><span className="lp-mini-list-id">INC-DEMO-03</span><span className="lp-mini-status lp-mini-status-done">Đã phê duyệt</span></div><small>DEMO MINH HỌA</small></div><Link href="/incidents" className="lp-text-link">Khám phá workspace <ArrowRight className="lp-icon" /></Link></article>
          <div className="lp-feature-stack"><article className="lp-feature-secondary" data-reveal><div className="lp-feature-title"><Gauge className="lp-icon" /><span>CONNECTED EVIDENCE</span><span>01</span></div><h3>Kiểm tra trong cùng ngữ cảnh.</h3><p>Video, evidence và tín hiệu telemetry khi có giúp kỹ sư đối chiếu các quan sát, thay vì đọc một kết luận đơn lẻ.</p><div className="lp-feature-chain"><span>VIDEO</span><i /><span>EVIDENCE</span><i /><span>REPORT</span></div></article>
          <article className="lp-feature-secondary" data-reveal><div className="lp-feature-title"><FileText className="lp-icon" /><span>REVIEWABLE REPORTS</span><span>02</span></div><h3>Báo cáo có thể kiểm tra và chỉnh sửa.</h3><p>Chỉnh sửa bản nháp, xử lý xung đột phiên bản và đưa báo cáo qua luồng gửi review, phê duyệt hoặc từ chối.</p><div className="lp-feature-report"><span><Check className="lp-icon" /> Lưu bản nháp</span><ArrowRight className="lp-icon" /><span>Gửi review</span><ArrowRight className="lp-icon" /><span>Quyết định</span></div></article></div>
        </div>
      </div></section>

      <section className="lp-final" aria-labelledby="lp-final-title"><div className="lp-container lp-final-layout" data-reveal><div><p className="lp-eyebrow"><span className="lp-dot" /> EVIDENCE FIRST. HUMAN ALWAYS.</p><h2 id="lp-final-title">Khám phá dữ liệu.<br /><span>Giữ vững ngữ cảnh.</span></h2><p>Mở workspace để quản lý sự cố và kiểm tra bằng chứng.</p></div><Link href="/incidents" className="lp-button lp-button-primary">Khám phá hệ thống <ArrowRight className="lp-icon" /></Link><div className="lp-final-orbit" aria-hidden="true"><LensMark /></div></div></section>
    </main>
    <footer className="lp-footer"><div className="lp-container lp-footer-top"><a href="#dau-trang" onClick={scrollToSection} className="lp-brand"><LensMark /><span>Incident<span>Lens</span></span></a><p>Phân tích có ngữ cảnh.<br />Review có con người.</p><nav aria-label="Liên kết cuối trang"><a href="#quy-trinh" onClick={scrollToSection}>Quy trình</a><Link href="/incidents">Workspace <ArrowRight className="lp-icon" /></Link></nav></div><div className="lp-container lp-footer-bottom"><span>INCIDENTLENS / ADAS INCIDENT ANALYSIS</span><span>AI hỗ trợ phân tích · Kỹ sư kiểm tra & review</span><a href="#dau-trang" onClick={scrollToSection} aria-label="Về đầu trang">Về đầu trang ↑</a></div></footer>
  </div>;
}
