# Git workflow

Checkout baseline ở branch `develop`; không thay nhánh hoặc commit/push khi chỉ tạo tài liệu. Quy trình đề xuất: nhánh `feature/RAV-NNN-short-name` hoặc `fix/RAV-NNN-short-name` từ develop, thay đổi nhỏ → PR vào develop → release PR vào main. Áp dụng branch protection do owner cấu hình, chưa khẳng định đã tồn tại.

Commit nêu task và behavior, ví dụ `feat(RAV-003): detect telemetry candidate windows`. Stage đúng files của task, bảo toàn unrelated changes. PR liên kết SPEC/ADR/task, acceptance đã đạt, migration, commands/results/limits và risks. Không commit secret hoặc raw media.

CI thực tế: `.github/workflows/ci.yml` chạy push main/develop và PR main, self-hosted runner, Python 3.11, ruff backend/api + pytest. PR develop và frontend chưa có gate trong workflow hiện tại; RAV-020 cần bổ sung/kiểm tra trước release. Local pass không chứng minh remote CI pass. Merge/release theo instruction owner; không tự giả định production deployment được phép.
