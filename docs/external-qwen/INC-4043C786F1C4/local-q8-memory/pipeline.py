"""Event-memory pipeline (user's architecture). Ollama is stateless: the backend keeps
memory.json per video and resends the relevant history on every call.

  python pipeline.py track <out_dir> <frames_subdir> <M0|M1|M2>   per-frame tracking only
  python pipeline.py full  <out_dir> <video> <M1|M2>              scan 1 fps -> rules -> dense frames -> re-evaluation

M0 = no memory, M1 = memory as JSON text, M2 = chat history (last 2 frames as image/answer turns).
"""
import json, subprocess, sys
from pathlib import Path

import cv2  # noqa: F401  (fails fast if not run with the venv that frames.py needs)
from qwen import BOX, TAG, TEXT, chat, obj, to_pixels

SUFFIX = '' if TAG == 'qwen25vl-7b' else f'_{TAG}'

HERE = Path(__file__).parent
STATES = ['NORMAL', 'HAZARD', 'FALLEN_OR_CRASH']
ACTORS = ['none', 'pedestrian', 'motorcycle', 'bicycle', 'car', 'truck', 'other']
FRAME_SCHEMA = obj(a_evidence=TEXT, b_main_actor={'enum': ACTORS}, c_main_actor_bbox=BOX, d_state={'enum': STATES})
SYSTEM = ('You watch forward dashcam frames from a camera car, in time order. Gray boxes are masks; ignore them. '
          'For the NEW frame: (a) in at most 25 words, the visible evidence about road users near the camera car\'s path and what they are doing; '
          '(b) the road user most relevant to safety; (c) its bounding box in pixel coordinates of the new image ([0,0,0,0] if none); '
          '(d) the state: NORMAL = traffic behaves normally; HAZARD = a road user is entering or crossing the camera car\'s path close ahead, '
          'swerving hard or losing balance; FALLEN_OR_CRASH = a road user has fallen or tipped over, or there is contact or a collision. '
          'Earlier observations may be wrong; judge the new frame by what is visible in it.')


def seconds(path):
    return float(path.stem[1:])


def rule(observations):
    states = [o['state'] for o in observations]
    if 'FALLEN_OR_CRASH' in states or any(a == b == 'HAZARD' for a, b in zip(states, states[1:])):
        return 'LIKELY_INCIDENT'
    return 'POSSIBLE_INCIDENT' if 'HAZARD' in states else 'NO_INCIDENT_SO_FAR'


def track(out, frames, variant, memory=None, turns=None, tag=''):
    memory = memory or {'video': out.name, 'incident_status': 'NO_INCIDENT_SO_FAR', 'observations': []}
    turns = turns if turns is not None else []
    for path in frames:
        t = seconds(path)
        text = f'New frame at t={t:.2f}s.'
        if variant == 'M1':
            text = f'Backend memory (earlier observations): {json.dumps({**memory, "observations": memory["observations"][-6:]}, ensure_ascii=False)}\n' + text
        history = [m for pair in turns[-2:] for m in pair] if variant == 'M2' else []
        answer, raw, user, wall = chat(text, [path], FRAME_SCHEMA, system=SYSTEM, history=history, num_predict=140)
        turns.append((user, {'role': 'assistant', 'content': raw}))
        h, w = cv2.imread(str(path)).shape[:2]
        box = answer.get('c_main_actor_bbox', [0, 0, 0, 0])
        memory['observations'].append({'t': t, 'state': answer.get('d_state', 'NORMAL'), 'actor': answer.get('b_main_actor', 'none'),
                                       'bbox': to_pixels(box, w, h) if box[2] > box[0] else None, 'evidence': answer.get('a_evidence', answer.get('unparsed', '')),
                                       'frame': path.relative_to(out).as_posix(), 'pass': tag})
        memory['incident_status'] = rule(memory['observations'])
        o = memory['observations'][-1]
        print(variant, tag, f'{t:6.2f}s {wall:5.1f}s', o['state'], o['actor'], memory['incident_status'], '|', o['evidence'], flush=True)
        (out / f'memory_{variant}{SUFFIX}.json').write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')
    return memory, turns


def crop_actor(out, o, size=448):
    img = cv2.imread(str(out / o['frame']))
    x1, y1, x2, y2 = o['bbox']
    side = int(max(300, 1.6 * max(x2 - x1, y2 - y1)))
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    x0, y0 = max(0, min(cx - side // 2, img.shape[1] - side)), max(0, min(cy - side // 2, img.shape[0] - side))
    path = out / 'crops' / f'{Path(o["frame"]).stem}.png'
    path.parent.mkdir(exist_ok=True)
    cv2.imwrite(str(path), cv2.resize(img[y0:y0 + side, x0:x0 + side], (size, size)))
    return path


def reevaluate(out, memory, t_from, t_to):
    picked = [o for o in memory['observations'] if t_from <= o['t'] <= t_to and o['bbox']]
    picked = picked[::max(1, len(picked) // 6)][:6]
    if not picked:
        return {'c_verdict': 'UNCERTAIN', 'a_progression': 'no tracked road user in the window'}
    brief = [{k: o[k] for k in ('t', 'state', 'actor', 'evidence')} for o in memory['observations'] if t_from - 2 <= o['t'] <= t_to]
    prompt = (f'Backend memory for this video: {json.dumps(brief, ensure_ascii=False)}\n'
              f'The images are crops around the main road user at t = {", ".join(f"{o["t"]:.2f}s" for o in picked)}, in time order. '
              'Gray boxes are masks; ignore them. The memory may contain mistakes; check it against the images. '
              'First describe in at most 50 words how the road user progresses across the images, then give the event type and your verdict.')
    schema = obj(a_progression=TEXT, b_event_type={'enum': ['LOSS_OF_CONTROL_FALL', 'COLLISION', 'NEAR_MISS_PEDESTRIAN', 'NEAR_MISS_VEHICLE', 'SWERVE_NO_FALL', 'OTHER', 'NONE']},
                 c_verdict={'enum': ['INCIDENT', 'NO_INCIDENT', 'UNCERTAIN']})
    answer, _, _, wall = chat(prompt, [crop_actor(out, o) for o in picked], schema, num_predict=220, num_ctx=16384)
    return {'window_s': [t_from, t_to], 'frames_s': [o['t'] for o in picked], **answer, 'wall_s': wall}


def full(out, video, variant):
    py = sys.executable
    duration = cv2.VideoCapture(str(video)).get(cv2.CAP_PROP_FRAME_COUNT) / cv2.VideoCapture(str(video)).get(cv2.CAP_PROP_FPS)
    subprocess.run([py, HERE / 'frames.py', 'grab', video, out, '0.5', f'{duration - 0.5:.2f}', '1', 'scan'], check=True)
    memory, turns = track(out, sorted((out / 'scan').glob('t*.png')), variant, tag='scan')
    anomalies = [o['t'] for o in memory['observations'] if o['state'] != 'NORMAL']
    windows = []
    for t in anomalies:   # merge anomalies into windows [t-1.5, t+1.5]
        if windows and t - 1.5 <= windows[-1][1]:
            windows[-1][1] = t + 1.5
        else:
            windows.append([max(0.0, t - 1.5), min(duration - 0.1, t + 1.5)])
    report = {'video': str(video), 'variant': variant, 'scan_status': memory['incident_status'], 'windows': []}
    for t0, t1 in windows[:3]:
        sub = f'dense_{t0:05.1f}'
        subprocess.run([py, HERE / 'frames.py', 'grab', video, out, f'{t0:.2f}', f'{t1:.2f}', '5', sub], check=True)
        memory, turns = track(out, sorted((out / sub).glob('t*.png')), variant, memory, turns, tag=sub)
        result = reevaluate(out, memory, t0, t1)
        print('RE-EVALUATION', t0, t1, json.dumps(result, ensure_ascii=False), flush=True)
        report['windows'].append(result)
    report['final_status'] = memory['incident_status']
    report['verdict'] = 'INCIDENT' if any(w.get('c_verdict') == 'INCIDENT' for w in report['windows']) else \
                        'UNCERTAIN' if any(w.get('c_verdict') == 'UNCERTAIN' for w in report['windows']) else 'NO_INCIDENT'
    (out / f'report_{variant}{SUFFIX}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('REPORT', json.dumps({k: report[k] for k in ('scan_status', 'final_status', 'verdict')}), flush=True)


if __name__ == '__main__':
    mode, out = sys.argv[1], Path(sys.argv[2])
    if mode == 'track':
        track(out, sorted((out / sys.argv[3]).glob('t*.png')), sys.argv[4], tag=sys.argv[3])
    else:
        full(out, Path(sys.argv[3]), sys.argv[4])
