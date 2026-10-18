"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Check, Film, FileText, Gauge, ArrowRight } from "@/components/icons";
import { LensMark, RoadIllustration } from "./landing-visuals";

export function GalaxyHandoff() {
  const section = useRef<HTMLElement>(null);
  useEffect(() => {
    const element = section.current;
    if (!element) return;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame: number | undefined;
    const paint = () => {
      frame = undefined;
      if (document.hidden) return;
      const rect = element.getBoundingClientRect();
      const progress = motion.matches ? .5 : Math.max(0, Math.min(1, (innerHeight * .82 - rect.top) / (rect.height + innerHeight * .15)));
      element.style.setProperty("--handoff-progress", progress.toFixed(3));
      element.dataset.phase = String(Math.min(2, Math.floor(progress * 3)));
    };
    const queue = () => { if (frame === undefined && !document.hidden) frame = requestAnimationFrame(paint); };
    const visibility = () => { if (document.hidden && frame !== undefined) { cancelAnimationFrame(frame); frame = undefined; } else queue(); };
    window.addEventListener("scroll", queue, { passive: true }); window.addEventListener("resize", queue); motion.addEventListener("change", queue); document.addEventListener("visibilitychange", visibility); paint();
    return () => { window.removeEventListener("scroll", queue); window.removeEventListener("resize", queue); motion.removeEventListener("change", queue); document.removeEventListener("visibilitychange", visibility); if (frame !== undefined) cancelAnimationFrame(frame); };
  }, []);
  return <section ref={section} className="lp-handoff" data-phase="0" aria-labelledby="handoff-title"><div className="lp-container lp-handoff-inner">
    <div className="lp-handoff-core" aria-hidden="true"><LensMark /><i /><i /></div>
    <div><p className="lp-eyebrow">TỪ LÕI PHÂN TÍCH ĐẾN GÓC NHÌN CỦA KỸ SƯ</p><h2 id="handoff-title">Ánh sáng dẫn đường.<br /><span>Bằng chứng giữ ngữ cảnh.</span></h2><p>Đi sâu vào từng mốc. Xem lại những gì dữ liệu thực sự cho thấy.</p><div className="lp-handoff-tags"><span>01 / TÍN HIỆU</span><ArrowRight className="lp-icon" /><span>02 / EVIDENCE</span><ArrowRight className="lp-icon" /><span>03 / REVIEW</span></div></div>
  </div></section>;
}

const stages = [
  { title: "Upload", tag: "VIDEO + OPTIONAL CSV", label: "01 / INPUT", text: "Đưa video MP4 vào workspace. CSV telemetry là tùy chọn; bổ sung thông tin đồng bộ khi có để đối chiếu đúng ngữ cảnh.", note: "Bắt đầu từ dữ liệu bạn có.", icon: Film },
  { title: "Phân tích", tag: "AI-ASSISTED DRAFT", label: "02 / ANALYSIS", text: "Bắt đầu phân tích và theo dõi tiến trình xử lý. AI hỗ trợ tạo bản nháp; các giới hạn và điểm chưa xác nhận cần được kiểm tra.", note: "Một bản nháp, không phải kết luận cuối cùng.", icon: Gauge },
  { title: "Kiểm tra evidence", tag: "CONTEXT BEFORE CONCLUSION", label: "03 / EVIDENCE", text: "Mở video, frame, clip và telemetry khi có. Đối chiếu các mốc và quan sát trong cùng bối cảnh trước khi chỉnh sửa báo cáo.", note: "Đọc bằng chứng trước khi đưa ra kết luận.", icon: FileText },
  { title: "Review", tag: "HUMAN-LED DECISION", label: "04 / HUMAN REVIEW", text: "Lưu bản nháp, gửi review và ghi nhận phê duyệt hoặc phản hồi từ chối. Kỹ sư kiểm tra; người review đưa ra quyết định.", note: "Con người giữ quyền kiểm tra và review.", icon: Check },
] as const;

function WorkflowIllustration({ stage }: { stage: number }) {
  if (stage === 1) return <div className="lp-analysis-scene" role="img" aria-label="Minh họa quét khung hình, liên kết quan sát và tạo bản nháp; không phải phân tích trực tiếp">
    <div className="lp-analysis-grid" />
    <div className="lp-analysis-frame lp-analysis-frame-back"><RoadIllustration selected={0} /></div>
    <div className="lp-analysis-frame lp-analysis-frame-front"><RoadIllustration selected={1} /><div className="lp-analysis-scan" /><span className="lp-analysis-frame-caption">FRAME 0068 <span>DEMO</span></span></div>
    <div className="lp-analysis-target"><i /><span>QUAN SÁT / 01</span></div>
    <div className="lp-analysis-readout"><span><i /> VISION PIPELINE</span><strong>Đọc khung hình.</strong><div><b /><b /><b /><b /><b /><b /><b /><b /></div><small>VIDEO → OBSERVATION → DRAFT</small></div>
    <span className="lp-analysis-coordinate">06.8 s / KHUNG HÌNH MINH HỌA</span>
  </div>;
  if (stage === 0) return <div className="lp-workflow-input-art"><div className="lp-workflow-input-video"><RoadIllustration /><span>VIDEO.MP4</span></div><div className="lp-workflow-input-csv"><Gauge className="lp-icon" /><span>TELEMETRY.CSV<small>Tùy chọn</small></span><svg viewBox="0 0 160 40" aria-hidden="true"><path d="M0 28h20l12-8 18 4 13-12 12 23 15-14 20 4 17-8 13 7h20" fill="none" stroke="currentColor" strokeWidth="2" /></svg></div></div>;
  if (stage === 2) return <div className="lp-workflow-evidence-art"><div><RoadIllustration selected={1} /><span>FRAME / DEMO</span></div><div><FileText className="lp-icon" /><span>EV-01</span><small>Minh họa · cần kiểm tra</small></div><div><span>00:04.2</span><i /><span>00:06.8</span><i /><span>00:08.4</span></div></div>;
  return <div className="lp-workflow-report-art"><div><FileText className="lp-icon" /><span>REPORT / DEMO</span><small>BẢN NHÁP</small></div><i /><i /><i /><div><span><Check className="lp-icon" /> Kỹ sư kiểm tra</span><ArrowRight className="lp-icon" /><span>Review</span></div></div>;
}

export function GalaxyWorkflow() {
  const [selected, setSelected] = useState(0);
  const stage = stages[selected];
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  return <div className="lp-workflow-console" style={{ "--step-progress": `${selected / 3 * 100}%` } as CSSProperties}>
    <ol className="lp-workflow-track" aria-label="Các giai đoạn trong quy trình">{stages.map((item, index) => <li key={item.title}><button ref={element => { buttons.current[index] = element; }} type="button" className="lp-workflow-button" aria-pressed={selected === index} onClick={() => setSelected(index)} onKeyDown={event => {
      let next: number | undefined;
      if (event.key === "ArrowRight") next = (index + 1) % stages.length;
      if (event.key === "ArrowLeft") next = (index + stages.length - 1) % stages.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = stages.length - 1;
      if (next !== undefined) { event.preventDefault(); setSelected(next); buttons.current[next]?.focus(); }
    }}><span>0{index + 1}</span><strong>{item.title}</strong><small>{item.tag}</small></button></li>)}</ol>
    <div className="lp-workflow-stage" data-stage={selected}>
      <div className="lp-workflow-illustration" data-stage={selected}><div key={selected} className="lp-workflow-art-enter"><WorkflowIllustration stage={selected} /></div></div>
      <div className="lp-workflow-copy" aria-live="polite" aria-atomic="true"><p className="lp-workflow-stage-label"><span className="lp-dot" /> {stage.label}</p><h3>{stage.title}</h3><p>{stage.text}</p><div className="lp-workflow-stage-tags"><Check className="lp-icon" /><span>{stage.note}</span></div></div>
    </div>
  </div>;
}
