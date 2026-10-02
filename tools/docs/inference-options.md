# External API và self-hosted — phương án chưa chốt

Decision: **OPEN**, không phải ADR bổ sung

Ngày: 2026-10-03

## Context

Người dùng chưa chọn nơi inference theo chi phí. [ADR-004](../adrs/ADR-004-vlm-provider-abstraction.md) đã accept adapter chung, không accept một provider production.

## Options

| Dimension | external_api | self_hosted |
| --- | --- | --- |
| Input | Chỉ MASKED/PASSED + sanitized telemetry | Dữ liệu trong boundary nội bộ |
| Baseline | API structured image/video phù hợp; verify model hiện hành khi thử | Qwen3-VL-8B-Instruct/vLLM là ứng viên, chưa khóa model/hardware |
| Cost | Tokens + preprocess + storage + egress + retry + review | GPU thuê/khấu hao + utilization + điện/vận hành + preprocess/storage/review |
| Gate | Data egress consent/policy và privacy test | Hardware capacity, endpoint/network containment và throughput test |

## Proposed decision process

Giữ cả hai profile, triển khai contract/mock trước. [RAV-019](../tasks/RAV-019-provider-cost-comparison.md) đo cùng cases/budget theo [evaluation](../specs/evaluation.md). Owner chọn sau benchmark và policy; ADR-004 adapter chung giữ nguyên khi chỉ đổi cấu hình. Nếu thực sự thay quyết định kiến trúc, tạo ADR-011 mới với supersession link. Chưa mua GPU, chưa khóa provider, chưa chốt đơn giá. Workload/tháng, frames/candidate, utilization và accepted incidents quyết định điểm hòa vốn. LLM text thứ hai chỉ thêm nếu ablation chứng minh lợi ích bù chi phí.

## Consequences

Production inference configuration cần owner chọn sau đo; các task common pipeline và adapter mock tiếp tục được. ADR-006 storage và identity provider vẫn là quyết định độc lập.
