"use client";

type RecordValue = Record<string, unknown>;
export const asRecord = (value: unknown): RecordValue => value !== null && typeof value === "object" && !Array.isArray(value) ? value as RecordValue : {};
const labels: Record<string, string> = {
  road_environment: "Bối cảnh đường", road_condition: "Mặt đường", weather_visibility: "Thời tiết và tầm nhìn", traffic_conditions: "Giao thông", ego_vehicle_motion: "Chuyển động xe", other_participants: "Phương tiện và người xung quanh",
  before: "Trước sự kiện", onset: "Khởi phát", escalation: "Diễn biến", critical: "Thời điểm trọng yếu", response: "Phản ứng", after: "Sau sự kiện",
  what_happened: "Sự việc", participants: "Các bên liên quan", trigger: "Tình huống khởi phát", relative_motion: "Chuyển động tương đối", ego_vehicle_response: "Phản ứng của xe", other_responses: "Phản ứng khác",
  supported_immediate_cause: "Nguyên nhân trực tiếp có bằng chứng", root_cause: "Nguyên nhân gốc", contributing_factors: "Yếu tố góp phần", hypotheses: "Giả thuyết cần kiểm chứng", causal_uncertainty: "Giới hạn kết luận nguyên nhân",
  immediate_result: "Kết quả tức thời", collision_occurred: "Có va chạm", near_miss_occurred: "Có tình huống suýt va chạm", incident_resolved: "Sự việc đã kết thúc", observed_damage: "Thiệt hại quan sát được", observed_injury: "Thương tích quan sát được", consequences: "Hậu quả có bằng chứng", potential_risks: "Rủi ro tiềm ẩn",
  video_coverage: "Độ bao phủ video", telemetry_available: "Có telemetry", time_sync_reliable: "Đồng bộ thời gian đáng tin cậy", sensor_disagreements: "Bất đồng giữa tín hiệu", limitations: "Giới hạn dữ liệu",
  claim_status: "Mức bằng chứng", category: "Nhóm yếu tố", label: "Yếu tố", description: "Mô tả", claim: "Nhận định", evidence_ids: "Bằng chứng", certainty: "Mức bằng chứng", observation: "Quan sát", supports: "Nhận định được hỗ trợ", evidence_id: "Mã bằng chứng", source: "Nguồn", time_s: "Giây video", phase: "Giai đoạn",
};
const enums: Record<string, string> = { UNKNOWN: "Chưa xác định", OBSERVED: "Quan sát trực tiếp", SUPPORTED_INFERENCE: "Suy luận có bằng chứng", HYPOTHESIS: "Giả thuyết", COMPLETE: "Đầy đủ", PARTIAL: "Một phần", CONFIRMED: "Đã xác nhận", INCONCLUSIVE: "Chưa đủ kết luận", LOW: "Thấp", MEDIUM: "Trung bình", HIGH: "Cao", CRITICAL: "Nghiêm trọng", BEFORE: "Trước sự kiện", ONSET: "Khởi phát", ESCALATION: "Diễn biến", RESPONSE: "Phản ứng", AFTER: "Sau sự kiện" };

function Value({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined || value === "" || value === "UNKNOWN") return <span className="text-slate-500">Chưa xác định</span>;
  if (typeof value === "boolean") return <>{value ? "Có" : "Không"}</>;
  if (typeof value === "string" || typeof value === "number") return <>{enums[String(value)] || String(value)}</>;
  if (depth > 5) return <span className="text-slate-500">Xem dữ liệu chi tiết bên dưới</span>;
  if (Array.isArray(value)) return value.length ? <ul className="space-y-2">{value.map((item, i) => <li key={i} className="border-l border-slate-200 pl-3"><Value value={item} depth={depth + 1} /></li>)}</ul> : <span className="text-slate-500">Chưa có dữ liệu</span>;
  return <dl className="space-y-2">{Object.entries(asRecord(value)).map(([key, item]) => <div key={key}><dt className="text-xs text-slate-500">{labels[key] || key.replace(/_/g, " ")}</dt><dd className="mt-1"><Value value={item} depth={depth + 1} /></dd></div>)}</dl>;
}

function Fields({ value }: { value: unknown }) {
  const entries = Object.entries(asRecord(value));
  return entries.length ? <dl className="grid gap-x-5 gap-y-4 sm:grid-cols-2">{entries.map(([key, item]) => <div key={key}><dt className="text-xs font-semibold text-slate-500">{labels[key] || key.replace(/_/g, " ")}</dt><dd className="mt-1.5 whitespace-pre-line text-sm leading-6 text-slate-700"><Value value={item} /></dd></div>)}</dl> : <p className="text-sm text-slate-500">Chưa có phân tích cho nhóm này.</p>;
}

export function StructuredAnalysis({ analysis, onSeek, seekEnabled = true }: { analysis: RecordValue; onSeek: (time: number) => void; seekEnabled?: boolean }) {
  const timeline = Array.isArray(analysis.timeline) ? analysis.timeline : [];
  return <div className="structured-analysis mt-5 space-y-5">
    <dl className="flex flex-wrap gap-5 rounded-lg border border-slate-200 p-4">{[["Trạng thái phân tích", analysis.analysis_status], ["Mức độ", analysis.severity], ["Độ tin cậy do mô hình tự báo", typeof analysis.confidence === "number" ? `${Math.round(analysis.confidence * 100)}%` : null]].map(([label, value]) => <div key={String(label)}><dt className="text-xs text-slate-500">{String(label)}</dt><dd className="mt-1 text-sm"><Value value={value} /></dd></div>)}</dl>
    {analysis.summary !== undefined && <div className="rounded-xl border border-slate-200 p-4 text-sm leading-7 text-slate-700"><Value value={analysis.summary} /></div>}
    <Group title="Điều kiện"><Fields value={analysis.scene_context} /></Group>
    <Group title="Diễn biến"><Fields value={analysis.phase_summary} />{timeline.length > 0 && <ol className="mt-5 space-y-3">{timeline.map((item, i) => {
      const event = asRecord(item), time = typeof event.time_s === "number" && Number.isFinite(event.time_s) && event.time_s >= 0 ? event.time_s : null;
      return <li key={i} className="rounded-lg border border-slate-200 p-3"><div className="mb-2 flex flex-wrap items-center gap-2 text-xs"><button type="button" disabled={!seekEnabled || time === null} onClick={() => { if (time !== null) onSeek(time); }} className="rounded-md border border-slate-300 px-2 py-1 font-semibold text-vf-primary disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2">{time === null ? "Chưa rõ thời điểm" : `${time.toFixed(2)}s · Xem video`}</button><span className="text-slate-500"><Value value={event.phase === "CRITICAL" ? "Thời điểm trọng yếu" : event.phase} /> · <Value value={event.certainty} /></span></div><p className="text-sm leading-6 text-slate-700"><Value value={event.description ?? event.observation} /></p>{Array.isArray(event.evidence_ids) && event.evidence_ids.length > 0 && <p className="mt-2 text-xs text-slate-500">Bằng chứng: {event.evidence_ids.filter(id => typeof id === "string").join(" · ")}</p>}</li>;
    })}</ol>}</Group>
    <Group title="Yếu tố & nguyên nhân"><Fields value={analysis.event_details} /><div className="mt-5 border-t border-slate-200 pt-4"><Fields value={analysis.causal_analysis ?? (analysis.factors ? { contributing_factors: analysis.factors } : undefined)} /></div></Group>
    <Group title="Kết quả"><Fields value={analysis.outcome} /></Group>
    {Array.isArray(analysis.evidence) && analysis.evidence.length > 0 && <Group title="Bằng chứng cho nhận định"><ol className="space-y-3">{analysis.evidence.map((item, index) => {
      const evidence = asRecord(item);
      const time = typeof evidence.time_s === "number" && Number.isFinite(evidence.time_s) && evidence.time_s >= 0 ? evidence.time_s : null;
      return <li key={index} className="border-l-2 border-slate-200 pl-4"><div className="mb-2 flex flex-wrap items-center gap-3"><span className="text-xs text-slate-500"><Value value={evidence.evidence_id} /> · <Value value={evidence.source} /></span><button type="button" disabled={!seekEnabled || time === null} onClick={() => { if (time !== null) onSeek(time); }} className="text-xs font-semibold text-vf-primary disabled:opacity-50">{time === null ? "Chưa rõ thời điểm" : `${time.toFixed(2)}s · Xem video`}</button></div><p className="text-sm leading-7"><Value value={evidence.observation} /></p><p className="mt-2 text-xs text-slate-500"><Value value={evidence.certainty} /></p></li>;
    })}</ol></Group>}
    <Group title="Chất lượng & giới hạn"><Fields value={analysis.data_quality} /><div className="mt-4 text-sm leading-6 text-slate-700"><h4 className="mb-2 text-xs font-semibold text-slate-500">Những điểm chưa xác định</h4><Value value={analysis.unknowns} /></div></Group>
  </div>;
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-xl border border-slate-200 p-4"><h3 className="mb-4 text-sm font-bold text-vf-navy">{title}</h3>{children}</section>;
}
