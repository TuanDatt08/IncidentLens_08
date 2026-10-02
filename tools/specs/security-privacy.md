# Security & privacy

Theo [role matrix](user-roles.md): xác thực server, scope incident/recording, RBAC và khác danh tính submit/approve. Không production demo actor. Audit ghi actor/action/entity/from_version/to_version/time, không chứa token/raw telemetry nhạy cảm.

Raw video/log ở storage hạn chế. Clip/frame được che mặt/biển số trước frontend hoặc external provider. Telemetry external dùng allowlist, loại GPS/identifier không cần thiết. Privacy validation ghi detector/version, vùng che, kiểm tra lỗi, người xác nhận nếu cần và hash asset; lỗi detector hoặc trạng thái chưa kiểm tra phải fail closed. Blur tự động không được xem luôn đạt; bộ ca có mặt/biển số nhỏ, khuất, chuyển động kiểm tra trước release.

`external_api`: outbound chỉ nhận artifact MASKED + PASSED và telemetry đã lọc, policy egress được owner phê duyệt. `self_hosted`: inference trong boundary nội bộ, kiểm tra endpoint/route network; frontend vẫn phải che. Self-host không mặc nhiên cho phép gửi raw qua dịch vụ phụ.

Retention/delete/backup phải có owner phê duyệt trước production; giữ hash/audit cần thiết, không để evidence của report approved thành link hỏng âm thầm. Signed URL có TTL/scope; không log URL có token. Validate file signature, hạn mức, storage path traversal, MIME và checksum. Data licence/consent phải được xác minh trước đưa benchmark vào Git.
