# Prompt gửi Qwen hiện tại

Worker GPU dùng Ollama `qwen2.5vl:7b`, xử lý tuần tự. Khi bật `QWEN_VIDEO_SUMMARY=true`, hai nhánh đều có lượt kết luận toàn video.

## Video-only

Prompt Stage A/B ở [promt.txt](../data/promt.txt), request được dựng trong [prompt_pipeline.py](../services/prompt_pipeline.py).

- Stage A `SUPPLIED_SEQUENCE`: quan sát các ảnh liên tiếp theo thứ tự.
- Stage A `FINAL_WINDOW`: tổng hợp những chuỗi thuộc một cửa sổ.
- Stage B `FINAL_CANDIDATE`: kết luận một sự kiện nghi vấn, có ảnh overview và ghi chú các chuỗi.
- Metadata, schema và prompt gửi model đều được đổi sang `frame_seq` toàn cục. Không đánh lại số theo batch. Backend giữ bảng ánh xạ về giây để cắt clip và phục vụ API.
- Mỗi ảnh có nhãn JSON ngay trước ảnh JPEG base64. Worker gửi toàn bộ mẫu 4 FPS trong các batch 6 ảnh chồng 2 ảnh theo cấu hình GPU.
- Biên kết thúc loại trừ có thể là `total_frames+1`; đây không phải ảnh. Hai biên clip Stage B được khóa trong schema để model không thay đổi.

## Video + log đồng bộ

Prompt ở [ollama_incident.txt](../prompts/ollama_incident.txt), request được dựng trong [vlm_provider.py](../services/vlm_provider.py).

Mỗi ảnh có `evidence_id` và `t_video_s` tính từ đầu video. JSON bổ sung gồm `candidate_window`, `candidate_observations`, `decision_scope`, `flags`, `telemetry`, `telemetry_findings`, `telemetry_units`, `evidence`, `output_schema` và duration. Output nội bộ vẫn dùng `time_s` cùng cơ sở giây video để giữ tương thích API.

`SUPPLIED_SEQUENCE` đọc chuỗi chuyển động; `FINAL_CANDIDATE` xem lại các ghi chú và ảnh đại diện để kết luận một candidate. Log chỉ chọn vùng nghi vấn. Phanh mạnh, xung đột quỹ đạo và tiếp xúc thực tế phải được đánh giá riêng. Không thấy va chạm không đủ để phủ nhận phanh khẩn cấp hoặc near miss.

## Tổng hợp toàn video

Prompt chung ở [video_summary.txt](../prompts/video_summary.txt), được gọi bởi [video_summary.py](../services/video_summary.py).

Backend truyền lại mọi ghi chú chuỗi/candidate, bằng chứng, ảnh then chốt và giới hạn coverage; Qwen không tự nhớ những request trước. Nhiều ghi chú được tổng hợp theo nhóm `SUMMARY_GROUP` trước `FINAL_VIDEO`. Giữ liên kết candidate gốc qua các cấp.

Đầu ra gồm `overall_status`, `summary`, `events`, `unknowns`, `review_status=DRAFT`. Trạng thái là `CONFIRMED`, `INCONCLUSIVE` hoặc `NO_INCIDENT_IN_OBSERVED_COVERAGE`. Chỉ được xác nhận bằng evidence thuộc candidate đã được xác nhận cho cùng loại sự kiện. Các nghi vấn sơ bộ và candidate lỗi vẫn phải được xét, không được âm thầm bỏ qua.

Các request có `temperature=0` và schema-constrained JSON. Raw request/response và hash prompt được lưu. Prompt là chỉ dẫn; schema/ID/tọa độ được kiểm tra bằng code, còn chất lượng phát hiện cần đánh giá trên video có nhãn.

Thiết kế chi tiết: [qwen-temporal-prompt-design.md](qwen-temporal-prompt-design.md). Cấu hình và giới hạn vận hành: [vast-worker.md](vast-worker.md).
