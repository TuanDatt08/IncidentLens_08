"""Compare event rules on the saved memories (venv python, QWEN_MODEL=qwen3.5:9b).
Runs tier 2 for raw events that do not have one yet, then scores four rules against truth.

  R1 raw tier-1 scan, >= 2 consecutive B/C windows
  R2 R1 after the strict distance re-check of B windows (C kept)       (= scan.py refine)
  R3 R2, then drop B events whose tier 2 answers A
  R4 R1 (no strict re-check), drop B events whose tier 2 answers A
  C windows (any rule): event only when tier 2 also answers C.
"""
import json
from pathlib import Path

from qwen import TAG
from scan import events_from, tier2

HERE = Path(__file__).parent
VIDEOS = {'moto': ('D:/VinAI/BuildPhase/Test_prompt/test_incident_60s.mp4', (9.8, 10.8), 'FALL_OR_COLLISION')}
for v, onset in (('16', 56.04), ('17', 56.13), ('18', 57.29)):   # actor_enters_road_s + 58.46 s
    VIDEOS[f'carla_v{v}'] = (next(Path(f'D:/VinAI/BuildPhase/IncidentLens-AI/data/version_{v}').glob('*.mp4')).as_posix(), (onset - 1.5, onset + 2.5), 'NEAR_MISS')


def tier2_cached(memory, clip, video, span, hint_windows):
    cache = memory.setdefault('tier2_cache', {})
    key = f"{span['start_s']:.2f}-{span['end_s']:.2f}"
    if key not in cache:
        hint = ' '.join(w['description'] for w in hint_windows)
        cache[key] = tier2(HERE / clip, video, span, 40 + len(cache), hint)
        print(clip, 'tier2', key, cache[key]['actor'], cache[key]['choice'], '|', cache[key]['description'][:150], flush=True)
    return cache[key]


def decide(memory, clip, video, windows, drop_b_on_a):
    found = []
    for event in events_from(windows):
        inside = [w for w in windows if event['start_s'] <= w['start_s'] <= event['end_s']]
        c_windows = [w for w in inside if w['choice'] == 'C']
        if event['status'] != 'EVENT' and not c_windows:
            continue
        span = {'start_s': c_windows[0]['start_s'], 'end_s': c_windows[-1]['end_s']} if c_windows else event
        t2 = tier2_cached(memory, clip, video, span, c_windows or inside)
        if t2['choice'] == 'C':
            found.append((event['start_s'], event['end_s'], 'FALL_OR_COLLISION'))
        elif event['status'] == 'EVENT' and not (drop_b_on_a and t2['choice'] == 'A'):
            found.append((event['start_s'], event['end_s'], 'NEAR_MISS'))
    return found


def score(found, truth_window, truth_type):
    hit = [f for f in found if f[0] <= truth_window[1] and f[1] >= truth_window[0]]
    return {'detected': bool(hit), 'type_ok': any(f[2] == truth_type for f in hit), 'false_events': len(found) - len(hit), 'events': found}


report = {}
for clip, (video, truth_window, truth_type) in VIDEOS.items():
    path = HERE / clip / f'memory_scan_{TAG}.json'
    memory = json.loads(path.read_text(encoding='utf-8'))
    raw = [dict(w) for w in memory['windows']]
    strict = [{**w, 'choice': 'C' if w['choice'] == 'C' else w.get('confirm', w['choice'])} for w in memory['windows']]
    rules = {'R1': decide(memory, clip, video, raw, False), 'R2': decide(memory, clip, video, strict, False),
             'R3': decide(memory, clip, video, strict, True), 'R4': decide(memory, clip, video, raw, True)}
    path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')
    report[clip] = {rule: score(found, truth_window, truth_type) for rule, found in rules.items()}
    for rule, s in report[clip].items():
        print(clip, rule, 'detected' if s['detected'] else 'MISSED', 'type_ok' if s['type_ok'] else 'type_wrong', 'false_events', s['false_events'], flush=True)
(HERE / f'rules_{TAG}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
for rule in ('R1', 'R2', 'R3', 'R4'):
    rows = [report[c][rule] for c in report]
    print(f"TOTAL {rule}: detected {sum(r['detected'] for r in rows)}/4, correct type {sum(r['type_ok'] for r in rows)}/4, false events {sum(r['false_events'] for r in rows)}", flush=True)
