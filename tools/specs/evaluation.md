# Evaluation protocol

Software test pass không chứng minh chất lượng AI. Dataset dự kiến 50–100 case chuyên gia; số thực có manifest/version/hash và quyền sử dụng. Split calibration/test theo recording/scenario để tránh leak frame gần nhau; khóa test set trước tune.

Mỗi case: video/log ref, time mapping, incident window, event label, factors và trạng thái claim, evidence/time/source kỳ vọng, privacy annotation, unknowns kỳ vọng, annotator và disagreement resolution. Không dùng LLM judge làm nhãn chuẩn duy nhất.

| Metric | Cách đo |
| --- | --- |
| Candidate recall | GT window được candidate match / GT windows; công bố IoU/tolerance và budget trước chạy |
| Factor precision/recall | Claim match expert label + claim_status, báo cáo theo category |
| Evidence correctness | Claim được expert xác nhận evidence/source/time đúng / claims có căn cứ |
| Completeness | Trường/hạng mục bắt buộc được đáp ứng / hạng mục kỳ vọng |
| Engineer acceptance | Nháp chấp nhận theo rubric định trước / nháp đã review; ghi mức sửa |
| Latency | p50/p95 theo duration, candidate count, stages, queue và retry |
| Cost per accepted incident | Storage + preprocess + inference + retry + review / accepted incidents |

Recall phải báo cáo cả candidate vượt budget, không chỉ những clip được model xem. Zero accepted incident thì cost/accepted không xác định, không chia cho 0. Báo cáo numerator/denominator và uncertainty, không chỉ một phần trăm.

So cùng case và budget: adapter API hiện có trên frame, external V2, self-hosted V2; ablation rule + VLM với sparse baseline. Clip/frame payload có hash; ghi model/revision/prompt/schema, hardware, input/output tokens, retry, tài nguyên và thời gian review. Đơn giá lưu currency/date/source; tự host tính GPU utilization, điện/thuê/vận hành; không so raw API bill với GPU chưa tính hết.

Ngưỡng release chưa chốt: quality, privacy miss rate, p95 latency, chi phí/budget phải được owner + Reviewer ký trước benchmark, không chọn sau khi thấy kết quả. RAV-018 chuẩn bị protocol/nhãn; RAV-019 bị BLOCKED cho production decision tới khi đủ dữ liệu/hardware/policy và threshold. Chưa có số đo thì ghi NOT_MEASURED.

Dataset tham khảo: CARLA kiểm tra workflow/mốc; DoTA/DADA kiểm tra visual anomaly; BDD100K/Waymo kiểm tra perception. Không dùng chúng làm nhãn lỗi bộ điều khiển khi không có log. Kiểm tra licence và chất lượng ADAS-TO/CarlaLoop trước dùng.
