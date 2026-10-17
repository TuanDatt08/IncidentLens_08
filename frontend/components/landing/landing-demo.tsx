"use client";

import { useState } from "react";
import { Film, Check, FileText, ArrowRight } from "@/components/icons";
import { RoadIllustration } from "./landing-visuals";

const moments = [
  { time: 4.2, label: "Tiếp cận", title: "Đặt sự kiện vào bối cảnh.", text: "Đọc video trước mốc cần kiểm tra. Một frame riêng lẻ chưa đủ để kết luận sự cố.", speed: 48, brake: 0, evidence: "Frame minh họa · EV-01" },
  { time: 6.8, label: "Giảm tốc", title: "Đối chiếu hình ảnh và tín hiệu.", text: "Ví dụ minh họa một thay đổi tốc độ cùng tín hiệu phanh. Kỹ sư cần kiểm tra chất lượng và đồng bộ dữ liệu.", speed: 31, brake: 72, evidence: "Frame minh họa · EV-02" },
  { time: 8.4, label: "Kiểm tra", title: "Giữ bằng chứng. Kiểm tra kết luận.", text: "Xem lại clip và evidence trước khi chỉnh sửa báo cáo. AI hỗ trợ phân tích; quyết định review thuộc về con người.", speed: 22, brake: 34, evidence: "Frame minh họa · EV-03" },
] as const;

export function LandingDemo() {
  const [selected, setSelected] = useState(1);
  const moment = moments[selected];
  const position = moment.time / 10 * 100;
  return <div className="lp-demo" data-selected={selected}>
    <div className="lp-demo-bar"><div className="lp-demo-window-dots" aria-hidden="true"><i /><i /><i /></div><span>INCIDENTLENS / REVIEW WORKSPACE</span><span className="lp-demo-badge">Demo minh họa</span></div>
    <div className="lp-demo-content">
      <div className="lp-demo-media">
        <div className="lp-demo-depth"><div className="lp-demo-depth-grid" aria-hidden="true" /><div className="lp-demo-video"><RoadIllustration selected={selected} /><div className="lp-demo-video-label"><Film className="lp-icon" /><span>VIDEO TỔNG HỢP</span></div><div className="lp-demo-time">00:{moment.time.toFixed(1).padStart(4, "0")}<span> / 00:10.0</span></div><div className="lp-demo-detection" aria-hidden="true"><span>EV-0{selected + 1}</span><i /></div></div><div className="lp-demo-depth-label"><span className="lp-dot" /> EVIDENCE LAYER <strong>{moment.evidence}</strong></div></div>
        <div className="lp-demo-timeline"><span>00:00</span><div className="lp-demo-track"><div style={{ width: `${position}%` }} /><i style={{ left: `${position}%` }} /></div><span>00:10</span></div>
        <div className="lp-demo-signal-heading"><span>TELEMETRY / DỮ LIỆU TỔNG HỢP</span><span><i /> Tốc độ <i /> Phanh</span></div>
        <svg className="lp-demo-chart" viewBox="0 0 640 108" fill="none" role="img" aria-label={`Giá trị demo tại ${moment.time} giây: tốc độ ${moment.speed} km/h, phanh ${moment.brake} phần trăm. Dữ liệu tổng hợp, không phải phân tích thực tế.`}>
          <path d="M0 20h640M0 50h640M0 80h640m80-80v108M240 0v108M400 0v108M560 0v108" stroke="#223049" />
          <path d="M0 29.3 128 28 268.8 34 352 38 435.2 53.83 537.6 64.33 640 66.67" stroke="#78edff" strokeWidth="2" />
          <path d="M0 90h268.8l48-8 60-20 58.4-22.4 102.4 26.6L640 83" stroke="#ad99ff" strokeWidth="2" />
          <path d={`M${moment.time * 64} 0v108`} stroke="#edf3ff" strokeDasharray="3 5" opacity=".7" />
          <circle cx={moment.time * 64} cy={90 - moment.speed / 60 * 70} r="4" fill="#78edff" />
          <circle cx={moment.time * 64} cy={90 - moment.brake / 100 * 70} r="4" fill="#ad99ff" />
        </svg>
        <div className="lp-demo-event-buttons" role="group" aria-label="Chọn mốc evidence minh họa">{moments.map((item, index) => <button type="button" key={item.time} aria-pressed={selected === index} onClick={() => setSelected(index)}><span>0{index + 1}</span><strong>{item.time.toFixed(1)} s</strong><small>{item.label}</small></button>)}</div>
        <p className="lp-demo-clock-note">Mốc demo tính bằng giây từ đầu video. Cảnh xe là ảnh AI tĩnh; các giá trị và evidence đều là minh họa.</p>
      </div>
      <div className="lp-demo-inspector">
        <div className="lp-demo-inspector-label"><span className="lp-dot" /> EVIDENCE INSPECTOR <span>0{selected + 1} / 03</span></div>
        <div key={selected} className="lp-demo-inspector-copy" aria-live="polite" aria-atomic="true"><span className="lp-demo-moment">{moment.time.toFixed(1)}<small>giây từ đầu video</small></span><h3>{moment.title}</h3><p>{moment.text}</p></div>
        <div className="lp-demo-metrics"><div><span>Tốc độ demo</span><strong>{moment.speed}<small> km/h</small></strong></div><div><span>Phanh demo</span><strong>{moment.brake}<small> %</small></strong></div></div>
        <div className="lp-demo-evidence"><FileText className="lp-icon" /><span>{moment.evidence}</span><Check className="lp-icon" /></div>
        <div className="lp-demo-review"><span className="lp-dot" /> Bản nháp · cần kỹ sư review</div>
        <a className="lp-text-link" href="/incidents">Mở workspace thật <ArrowRight className="lp-icon" /></a>
      </div>
    </div>
  </div>;
}
