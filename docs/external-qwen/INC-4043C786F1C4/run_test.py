"""Standalone single-frame Qwen experiment; no application imports or writes."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request
from datetime import datetime, timezone

TIMES = [8.3, 9.3, 9.5, 9.7, 9.9, 10, 10.1, 10.2, 10.5, 10.9, 11.5, 12.5, 13.5]
SOURCE = Path('/workspace/incidentlens-media/INC-4043C786F1C4/source/video.mp4')
OUT = Path(__file__).resolve().parent


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    assert len(TIMES) == 13 and len(set(TIMES)) == 13
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_frames',
        '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', str(SOURCE)]))
    pts = [float(f['best_effort_timestamp_time']) for f in probe['frames']]
    metadata = {
        'recording_id': 'INC-4043C786F1C4', 'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'source': str(SOURCE), 'source_sha256': hashlib.file_digest(SOURCE.open('rb'), 'sha256').hexdigest(),
        'model': 'qwen2.5vl:7b', 'requested_seconds': TIMES,
        'frame_selection': 'First decoded frame with presentation timestamp >= requested time; original resolution PNG.',
        'isolation': 'Independent Ollama calls. No backend/worker imports, database updates, prior outputs or telemetry.',
        'gpu_before': subprocess.check_output(['ollama', 'ps'], text=True),
        'hardware': subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.used', '--format=csv'], text=True),
    }
    save('metadata.json', metadata)
    rows = []
    for seconds in TIMES:
        tag = f'{seconds:06.2f}'.replace('.', '_')
        stem = 'frame_' + tag
        image = OUT / (stem + '.png')
        actual = next(p for p in pts if p >= seconds - 1e-7)
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-ss', str(seconds), '-i', str(SOURCE),
                        '-frames:v', '1', '-update', '1', '-y', str(image)], check=True)
        system = (
            f'Bạn là trợ lý quan sát hình ảnh. Đây là bài test độc lập: chỉ một frame của video '
            f'INC-4043C786F1C4 tại mốc yêu cầu {seconds:.2f} giây; timestamp frame thực tế {actual:.6f} giây. '
            'Chỉ mô tả những gì nhìn thấy trong ảnh hiện tại. Không sử dụng lịch sử, telemetry, '
            'logic backend hay suy đoán diễn biến trước/sau. '
            'Xác định các đối tượng nhìn thấy: người, phương tiện, động vật, vật trên đường, '
            'biển báo, vạch đường, công trình, cây cối và các chi tiết đáng chú ý khác nếu có. '
            'Với mỗi đối tượng hoặc nhóm đối tượng, nêu loại, số lượng nếu đếm được, màu sắc, '
            'vị trí tương đối trong ảnh, tư thế hoặc trạng thái nhìn thấy. '
            'Chú ý kiểm tra cả tiền cảnh và hậu cảnh, trái, giữa, phải; không mặc định có tai nạn. '
            'Không suy ra tốc độ, chuyển động, va chạm hoặc nguyên nhân từ một ảnh tĩnh khi không đủ bằng chứng. '
            'Nếu mờ, nhỏ, bị che hoặc không xác định được thì nói rõ; không bịa chi tiết. '
            'Trả lời hoàn toàn bằng tiếng Việt, gồm: 1. Tổng quan; 2. Danh sách đối tượng và vị trí; '
            '3. Chi tiết bất thường nhìn thấy; 4. Điểm chưa chắc chắn. Không cần schema nghiệp vụ hay bounding box.'
        )
        user = f'Quan sát ảnh đính kèm tại {seconds:.2f} giây. Hãy xác định và mô tả các thứ có trong frame này.'
        payload = {'model': 'qwen2.5vl:7b', 'stream': False, 'keep_alive': -1,
                   'options': {'temperature': 0, 'seed': 42, 'num_ctx': 32768, 'num_predict': 1600},
                   'messages': [{'role': 'system', 'content': system},
                                {'role': 'user', 'content': user, 'images': [base64.b64encode(image.read_bytes()).decode()]}]}
        (OUT / (stem + '.system.txt')).write_text(system, encoding='utf-8')
        save(stem + '.request.json', {**payload, 'messages': [payload['messages'][0],
             {'role': 'user', 'content': user, 'images': [f'FILE:{image.name}']}]})
        started = time.monotonic()
        row = {'requested_s': seconds, 'actual_pts_s': actual, 'image': image.name,
               'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(), 'stem': stem}
        try:
            req = urllib.request.Request('http://127.0.0.1:11434/api/chat',
                data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=900) as response:
                raw = json.load(response)
            save(stem + '.response.json', raw)
            content = raw['message']['content']
            assert raw.get('done') and content.strip(), 'Missing completed nonempty response'
            (OUT / (stem + '.output.txt')).write_text(content, encoding='utf-8')
            row.update(status='ok', output=content, done_reason=raw.get('done_reason'),
                       eval_count=raw.get('eval_count'), elapsed_s=round(time.monotonic()-started, 2))
        except Exception as exc:
            row.update(status='error', error=str(exc), elapsed_s=round(time.monotonic()-started, 2))
        rows.append(row)
        save('results.json', rows)
        print(json.dumps({k: v for k, v in row.items() if k != 'output'}, ensure_ascii=False), flush=True)
    metadata['gpu_after'] = subprocess.check_output(['ollama', 'ps'], text=True)
    metadata['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
    save('metadata.json', metadata)
    report = ['# Qwen: test độc lập 13 frame — INC-4043C786F1C4', '',
              'Mỗi frame là một request riêng, có system prompt riêng. Output bên dưới là nguyên văn Qwen.',
              'Kết quả chưa đối chiếu ground truth. Không suy ra diễn biến liên tục từ ảnh đơn.', '']
    for row in rows:
        report += [f"## {row['requested_s']:.2f} giây", '', f"Timestamp thực tế: {row['actual_pts_s']:.6f} giây.", '',
                   f"![Frame {row['requested_s']:.2f}s]({row['image']})", '',
                   f"[System prompt]({row['stem']}.system.txt) · [Request]({row['stem']}.request.json) · [Raw response]({row['stem']}.response.json)", '',
                   row.get('output', row.get('error', '')), '']
    (OUT / 'results.md').write_text('\n'.join(report), encoding='utf-8')
    assert len(rows) == 13 and all(r['status'] == 'ok' for r in rows)


if __name__ == '__main__':
    main()
