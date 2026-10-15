"""Send all 13 previously tested frames in one independent Stage 2 request."""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request
import urllib.error

OUT = Path(__file__).resolve().parent
FRAMES = Path('/workspace/manual-qwen-tests/INC-4043C786F1C4-prompt-v2')


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    previous = json.loads((FRAMES / 'results.json').read_text(encoding='utf-8'))
    assert len(previous) == 13
    frames, images = [], []
    for index, row in enumerate(previous, 1):
        data = (FRAMES / row['image']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['image_sha256']
        frames.append({'image_index_1based': index, 'frame_seq': index,
                       'evidence_id': f'EXT-F{index:02d}',
                       't_video_s': row['actual_pts_s'], 'file': row['image'],
                       'sha256': row['image_sha256']})
        images.append(base64.b64encode(data).decode())
    system = (OUT / 'system_prompt.txt').read_text(encoding='utf-8')
    metadata = {
        'sequence_id': 'EXTERNAL-ALL13-8.3-13.5',
        'frame_seq_definition': 'Ordinal position in this submitted sequence, not original video frame number.',
        'evidence_id_definition': 'External test identifiers assigned by this script, not backend evidence IDs.',
        'image_order': 'The attached images follow image_index_1based exactly.',
        'frames': frames, 'telemetry': None,
        'tracks': None, 'bounding_boxes': None, 'recognition_labels': None,
        'missing_inputs': ['No verified track IDs, bounding boxes, or recognition labels are available. These fields are missing, not evidence of no objects.'],
        'coverage': 'Only these 13 images are supplied. Intervening video frames are not observed.',
    }
    user = ('Phân tích toàn bộ 13 ảnh đính kèm theo đúng thứ tự và system prompt được cung cấp. '
            'Metadata dưới đây do script test độc lập cung cấp. Không có telemetry, '
            'không có kết quả Stage 1 hoặc dự đoán trước.\n' + json.dumps(metadata, ensure_ascii=False))
    payload = {'model': 'qwen2.5vl:7b', 'stream': False, 'keep_alive': -1,
               'options': {'temperature': 0, 'seed': 42, 'num_ctx': 49152, 'num_predict': 8192},
               'messages': [{'role': 'system', 'content': system},
                            {'role': 'user', 'content': user, 'images': images}]}
    save('input_metadata.json', metadata)
    save('request.json', {**payload, 'messages': [payload['messages'][0],
         {'role': 'user', 'content': user, 'images': [f'FILE:{f["file"]}' for f in frames]}]})
    runtime = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'attached_images': len(images),
               'gpu_before': subprocess.check_output(['ollama', 'ps'], text=True),
               'hardware': subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.used', '--format=csv'], text=True)}
    save('runtime.json', runtime)
    print('Sending one Stage 2 request with 13 actual images.', flush=True)
    started = time.monotonic()
    req = urllib.request.Request('http://127.0.0.1:11434/api/chat',
        data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=1800) as response:
            raw = json.load(response)
        save('response.json', raw)
        content = raw['message']['content']
        (OUT / 'output.txt').write_text(content, encoding='utf-8')
        assert raw.get('done') and content.strip()
        try:
            parsed = json.loads(content)
            runtime['strict_json'] = True
        except ValueError:
            runtime['strict_json'] = False
            block = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            parsed = json.loads(block.group(1) if block else content)
        save('parsed.json', parsed)
        runtime['done_reason'] = raw.get('done_reason')
        runtime['prompt_eval_count'] = raw.get('prompt_eval_count')
        runtime['eval_count'] = raw.get('eval_count')
        runtime['status'] = 'ok'
    except Exception as exc:
        runtime['status'] = 'error'
        runtime['error'] = str(exc)
        if isinstance(exc, urllib.error.HTTPError):
            runtime['error_body'] = exc.read().decode('utf-8', errors='replace')
        raise
    finally:
        runtime['elapsed_s'] = round(time.monotonic() - started, 2)
        runtime['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
        runtime['gpu_after'] = subprocess.check_output(['ollama', 'ps'], text=True)
        save('runtime.json', runtime)
        print(json.dumps(runtime, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
