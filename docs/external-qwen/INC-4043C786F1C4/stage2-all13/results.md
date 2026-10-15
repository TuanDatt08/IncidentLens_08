# Qwen Stage 2 — toàn bộ 13 frame trong một request

## Lượt chạy thực tế

Model qwen2.5vl:7b, RTX 2080 Ti, 100% GPU. Context 49.152; prompt_eval_count=37746; thời gian 97.87 giây; done_reason=stop.

Dùng nguyên văn Stage 2; 13 ảnh PNG gốc theo thứ tự; không truyền output Stage 1 hoặc telemetry. SHA256 ảnh khớp lượt test trước. ID EXT-F01..EXT-F13 do script test cấp, không phải evidence ID của backend. frame_seq là thứ tự trong chuỗi test, không phải số frame toàn video.

Lượt đầu context 32.768 bị từ chối vì 37.746 token; đã giữ bằng chứng lỗi, chạy thành công với context 49.152.

[System prompt](system_prompt.txt) · [Request với manifest ảnh](request.json) · [Raw response](response.json) · [Output nguyên văn](output.txt) · [JSON bỏ dấu bao Markdown](parsed.json)

## Kết luận Qwen (chưa xác nhận đúng)

Qwen trả hai track: người áo vàng/quần đỏ và xe máy, gán xuất hiện từ EXT-F01 tới EXT-F13. Kết luận NO_INCIDENT_IN_OBSERVED_COVERAGE, không thấy tiếp xúc. Đây là đầu ra model, chưa phải kết luận kiểm chứng.

## Lỗi và giới hạn thấy trong output

- Vẫn có dấu hiệu nhận nhầm đồ trang trí đỏ/vàng trên kính thành người/xe máy và kéo dài danh tính đó qua cả chuỗi.
- Mô tả bằng tiếng Anh dù prompt yêu cầu tiếng Việt; bọc JSON trong Markdown.
- interaction.action=riding không nằm trong danh sách giá trị prompt quy định.
- associated_track_ids rỗng dù tương tác mô tả người và xe máy liên quan nhau.
- Nhắc ô tô trong event_progression nhưng không tạo track ô tô.
- Không phân tích chi tiết thay đổi từng đoạn; unknowns rỗng. Không đủ cơ sở xem đây là kiểm kê đầy đủ hoặc tracking đúng.

## Thứ tự ảnh

| Thứ tự / frame_seq | Evidence ID test | Giây video | Ảnh |
|---|---|---|---|
| 1 | EXT-F01 | 8.30 | [Xem](../prompt-v2/frame_008_30.png) |
| 2 | EXT-F02 | 9.30 | [Xem](../prompt-v2/frame_009_30.png) |
| 3 | EXT-F03 | 9.50 | [Xem](../prompt-v2/frame_009_50.png) |
| 4 | EXT-F04 | 9.70 | [Xem](../prompt-v2/frame_009_70.png) |
| 5 | EXT-F05 | 9.90 | [Xem](../prompt-v2/frame_009_90.png) |
| 6 | EXT-F06 | 10.00 | [Xem](../prompt-v2/frame_010_00.png) |
| 7 | EXT-F07 | 10.10 | [Xem](../prompt-v2/frame_010_10.png) |
| 8 | EXT-F08 | 10.20 | [Xem](../prompt-v2/frame_010_20.png) |
| 9 | EXT-F09 | 10.50 | [Xem](../prompt-v2/frame_010_50.png) |
| 10 | EXT-F10 | 10.90 | [Xem](../prompt-v2/frame_010_90.png) |
| 11 | EXT-F11 | 11.50 | [Xem](../prompt-v2/frame_011_50.png) |
| 12 | EXT-F12 | 12.50 | [Xem](../prompt-v2/frame_012_50.png) |
| 13 | EXT-F13 | 13.50 | [Xem](../prompt-v2/frame_013_50.png) |

## Output nguyên văn

```json
{
  "sequence_id": "EXTERNAL-ALL13-8.3-13.5",
  "tracks": [
    {
      "track_id": "T01",
      "category": "person",
      "appearance": "person riding a motorcycle, wearing a yellow jacket and red pants",
      "first_evidence_id": "EXT-F01",
      "last_evidence_id": "EXT-F13",
      "associated_track_ids": [],
      "identity_certainty": "clear",
      "observed_changes": [
        "appears in frame 1, riding a motorcycle",
        "continues to ride the motorcycle in frames 2-13"
      ],
      "inferred_actions": []
    },
    {
      "track_id": "T02",
      "category": "motorcycle",
      "appearance": "motorcycle with a rider wearing a yellow jacket and red pants",
      "first_evidence_id": "EXT-F01",
      "last_evidence_id": "EXT-F13",
      "associated_track_ids": [],
      "identity_certainty": "clear",
      "observed_changes": [
        "appears in frame 1, ridden by a person",
        "continues to be ridden by the same person in frames 2-13"
      ],
      "inferred_actions": []
    }
  ],
  "interactions": [
    {
      "actor_track_id": "T01",
      "other_track_id": "T02",
      "observed_relation": "same person riding the motorcycle",
      "action": "riding",
      "evidence_ids": ["EXT-F01", "EXT-F13"],
      "certainty": "clear"
    }
  ],
  "event_progression": {
    "before": "The scene shows a road with a motorcycle and a car in the distance.",
    "during": "The motorcycle with a rider wearing a yellow jacket and red pants is seen riding on the road.",
    "after": "The motorcycle continues to ride on the road."
  },
  "risk_assessment": {
    "trajectory_conflict": "no",
    "visible_contact": "no",
    "incident_status": "NO_INCIDENT_IN_OBSERVED_COVERAGE",
    "event_type": "UNKNOWN",
    "evidence_ids": [],
    "reason": "The video only shows the motorcycle and rider moving on the road without any interaction or collision with other vehicles or pedestrians."
  },
  "unknowns": [],
  "review_status": "DRAFT"
}
```
