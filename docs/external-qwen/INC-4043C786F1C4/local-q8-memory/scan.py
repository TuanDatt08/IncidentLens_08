"""Full-video pipeline (user's event-memory architecture, tuned by rounds 1-8).

  python scan.py <out_dir> <video>     (venv python; QWEN_MODEL=qwen3.5:9b)

1. Frames every 0.6 s (road band, hood cut, ornament grayed: frames.py + ornament.py).
2. Tier 1: overlapping windows of 4 frames (1.8 s span, 1.2 s stride), scene-level multiple choice A/B/C/D.
3. Backend memory (memory.json): every window result. Rule engine: >= 2 consecutive flagged (B/C)
   windows = event; a lone flagged window stays UNCONFIRMED. Old answers are NOT fed back to the model
   (round 6 showed the 7B copying its previous answer).
4. Tier 2 per event: frames at 4 fps over the event span, Qwen boxes the main road user, one fixed crop
   window, same multiple choice. C upgrades the event to FALL_OR_COLLISION; otherwise it stays NEAR_MISS.
"""
import json, subprocess, sys
from pathlib import Path

import cv2
from qwen import TAG, chat
from windows import SCHEMA, actor_crops, question

HERE = Path(__file__).parent


def tier1(out, frames):
    memory_path = out / f'memory_scan_{TAG}.json'
    memory = json.loads(memory_path.read_text(encoding='utf-8')) if memory_path.exists() else {'windows': []}
    done = {w['start_s'] for w in memory['windows']}
    for i in range(0, len(frames) - 3, 2):
        group = frames[i:i + 4]
        start = float(group[0].stem[1:])
        if start in done:
            continue
        answer, _, _, wall = chat(question(group), group, SCHEMA, num_predict=160)
        memory['windows'].append({'start_s': start, 'end_s': float(group[-1].stem[1:]), 'choice': answer.get('b_choice', '?'),
                                  'description': answer.get('a_description', answer.get('unparsed', ''))})
        w = memory['windows'][-1]
        print(f"T1 {w['start_s']:6.2f}-{w['end_s']:6.2f}s {wall:5.1f}s {w['choice']} | {w['description']}", flush=True)
        memory_path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')
    return memory, memory_path


def events_from(windows):
    events, run = [], []
    for w in sorted(windows, key=lambda w: w['start_s']) + [{'choice': 'A'}]:
        if w['choice'] in ('B', 'C'):
            run.append(w)
            continue
        if run:
            events.append({'start_s': run[0]['start_s'], 'end_s': run[-1]['end_s'], 'windows': len(run),
                           'tier1': 'C' if any(r['choice'] == 'C' for r in run) else 'B',
                           'status': 'EVENT' if len(run) >= 2 else 'UNCONFIRMED'})
        run = []
    return events


ACTOR_WORDS = {'motorcycle': ('motorcycl', 'scooter', 'motorbike', 'bike'), 'bicycle': ('bicycl', 'cyclist'),
               'pedestrian': ('pedestrian', 'person', 'man ', 'woman', 'people'), 'car': ('car', 'suv', 'sedan', 'van'), 'truck': ('truck', 'bus')}


def named_actors(text):
    text = text.lower().replace('camera car', '')
    return [actor for actor, words in ACTOR_WORDS.items() if any(w in text for w in words)]


def tier2(out, video, event, n, hint=''):
    sub = f'event_{n:02d}'
    t0, t1 = event['start_s'], event['end_s']
    fps = min(4.0, 5 / max(0.5, t1 - t0))   # at most ~6 frames per event
    subprocess.run([sys.executable, HERE / 'frames.py', 'grab', video, out, f'{t0:.2f}', f'{t1:.2f}', f'{fps:.2f}', sub], check=True, capture_output=True)
    actor, crops = actor_crops(out / sub, prefer=named_actors(hint))
    if not crops:
        return {'actor': None, 'choice': 'D', 'description': 'no road user found'}
    answer, _, _, wall = chat(question(crops).replace('consecutive frames', 'consecutive crops around the main road user'), crops, SCHEMA, num_predict=160)
    return {'actor': actor, 'choice': answer.get('b_choice', '?'), 'description': answer.get('a_description', ''), 'frames_s': [float(p.stem[1:]) for p in crops]}


def main(out, video):
    cap = cv2.VideoCapture(str(video))
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    if not (out / 'scan06').exists():
        subprocess.run([sys.executable, HERE / 'frames.py', 'grab', video, out, '0.30', f'{duration - 0.3:.2f}', f'{1 / 0.6:.4f}', 'scan06'], check=True)
    memory, memory_path = tier1(out, sorted((out / 'scan06').glob('t*.png')))
    memory['events'] = events_from(memory['windows'])
    for n, event in enumerate(e for e in memory['events'] if e['status'] == 'EVENT'):
        event['tier2'] = tier2(out, video, event, n)
        event['type'] = 'FALL_OR_COLLISION' if event['tier2']['choice'] == 'C' else 'NEAR_MISS'
        print('EVENT', json.dumps(event, ensure_ascii=False), flush=True)
    confirmed = [e for e in memory['events'] if e['status'] == 'EVENT']
    memory['verdict'] = 'INCIDENT' if confirmed else 'UNCERTAIN' if memory['events'] else 'NO_INCIDENT'
    memory_path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')
    print('VERDICT', memory['verdict'], json.dumps([{k: e.get(k) for k in ('start_s', 'end_s', 'status', 'tier1', 'type')} for e in memory['events']]), flush=True)


STRICT = ('These are consecutive frames from a forward dashcam on a camera car, in time order (t = {times}). Gray boxes are masks; ignore them. '
          'First describe in at most 40 words the road user that comes closest to the camera car and how close it gets, then choose:\n'
          'A) not dangerous: normal traffic, lane changes, merges, turns or crossings that stay at a safe distance (more than about two car lengths ahead, or in another lane)\n'
          'B) dangerous near miss: a road user comes within about two car lengths directly in front of the camera car, cutting into or crossing its lane, so the camera car must brake hard or swerve\n'
          'C) a road user falls or tips over, or there is contact or a collision\n'
          'D) no road users near the camera car\'s path')


def refine(out, video):
    """Re-use the saved tier-1 memory (no re-scan).
    Near miss (B): strict distance re-check, then >= 2 consecutive windows.
    Fall/collision (C): often a single window; the distance re-check hid it, so instead the
    actor-crop pass (tier 2) must independently answer C."""
    memory_path = out / f'memory_scan_{TAG}.json'
    memory = json.loads(memory_path.read_text(encoding='utf-8'))
    frames = {float(p.stem[1:]): p for p in (out / 'scan06').glob('t*.png')}
    times = sorted(frames)
    for w in memory['windows']:
        if w['choice'] != 'B' or 'confirm' in w:
            continue
        group = [frames[t] for t in times if w['start_s'] - 1e-6 <= t <= w['end_s'] + 1e-6]
        answer, _, _, wall = chat(STRICT.format(times=', '.join(f'{float(p.stem[1:]):.2f}s' for p in group)), group, SCHEMA, num_predict=180)
        w['confirm'] = answer.get('b_choice', '?')
        w['confirm_description'] = answer.get('a_description', answer.get('unparsed', ''))
        print(f"CONFIRM {w['start_s']:6.2f}-{w['end_s']:6.2f}s {w['choice']}->{w['confirm']} {wall:5.1f}s | {w['confirm_description']}", flush=True)
        memory_path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')
    windows = [{**w, 'choice': 'C' if w['choice'] == 'C' else w.get('confirm', w['choice'])} for w in memory['windows']]
    events = events_from(windows)
    for n, event in enumerate(events):
        c_windows = [w for w in windows if w['choice'] == 'C' and event['start_s'] <= w['start_s'] <= event['end_s']]
        if event['status'] != 'EVENT' and not c_windows:
            continue
        span = {'start_s': c_windows[0]['start_s'], 'end_s': c_windows[-1]['end_s']} if c_windows else event
        hint = ' '.join(w['description'] for w in (c_windows or windows) if event['start_s'] <= w['start_s'] <= event['end_s'])
        event['tier2'] = tier2(out, video, span, 20 + n, hint)
        if event['tier2']['choice'] == 'C':
            event.update(status='EVENT', type='FALL_OR_COLLISION')
        elif event['status'] == 'EVENT':
            event['type'] = 'NEAR_MISS'
        print('EVENT' if event['status'] == 'EVENT' else 'REJECTED', json.dumps(event, ensure_ascii=False), flush=True)
    memory['refined'] = {'events': events, 'verdict': 'INCIDENT' if any(e['status'] == 'EVENT' for e in events) else 'UNCERTAIN' if events else 'NO_INCIDENT'}
    memory_path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')
    print('REFINED', memory['refined']['verdict'], json.dumps([{k: e.get(k) for k in ('start_s', 'end_s', 'status', 'tier1', 'type')} for e in events]), flush=True)


if __name__ == '__main__':
    (refine if sys.argv[3:4] == ['refine'] else main)(Path(sys.argv[1]), Path(sys.argv[2]))
