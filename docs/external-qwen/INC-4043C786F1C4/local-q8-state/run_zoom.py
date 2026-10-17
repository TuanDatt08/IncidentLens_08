"""Variant C: fixed 720x440 window around the motorcycle path (x 700-1420, y 400-840),
ornament sliver masked. Same per-frame state prompt (run_test) and same multiple-choice
sequence prompt (run_sequence) as variant B.

Event: 9.9 / 10.0 / 10.1 / 10.2 / 10.5 s (swerve, tip over, lying at roadside).
Control: 9.3 / 9.5 / 9.7 s (same motorcycle still riding normally on the road).
"""
import json, time
from pathlib import Path

from run_sequence import run
from run_test import ABNORMAL, ask

HERE = Path(__file__).parent
SUFFIX = '_C_zoom.png'
EVENT = ['frame_009_90', 'frame_010_00', 'frame_010_10', 'frame_010_20', 'frame_010_50']
CONTROL = ['frame_009_30', 'frame_009_50', 'frame_009_70']

rows = []
for name in CONTROL + EVENT:
    started = time.time()
    objects = json.loads(ask(HERE / 'images' / (name + SUFFIX))['message']['content'])['objects']
    rows.append({'frame': name, 'objects': objects, 'wall_s': round(time.time() - started, 1)})
    print('C', name, f"{rows[-1]['wall_s']:5.1f}s", '; '.join(f"{o['type']}:{o['state']}/{o['place']} - {o['note']}" for o in objects), flush=True)
    abnormal = any(o['type'] in {'motorcycle', 'person'} and o['state'] in ABNORMAL for o in objects)
    rows[-1]['abnormal'] = abnormal
(HERE / 'zoom_frame_results.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
run({'event': EVENT, 'control': CONTROL}, SUFFIX, 'zoom_sequence_results.json')
