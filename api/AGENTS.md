# API role

- Đọc [governance](../tools/AGENTS.md), [v1.1](docs/backend-contract-v1.1.md), task/SPEC/ADR.
- HTTP adapters/routes/errors/OpenAPI/docs ở role này; gọi domain service ở `../backend`, không copy processing logic vào route.
- Public models dùng chung hiện ở `backend/models/contracts.py`; thay schema phải giữ compatibility và kiểm cả consumer/frontend.
- SPEC V2 canonical ở `../tools/specs/api-contracts.md`; không publish routes V2 chỉ từ tài liệu.
- Media phải lấy asset đã scope/validate; response status/envelope không được thay âm thầm. Auth thật chưa có, production deny media/review không thay thế toàn API authentication.
- Tests ở `../tests/api` để kiểm API và worker với database fixture; docs API ở `docs/`.
