"""Round 6: event-memory architecture. Ollama is stateless, so the "backend" keeps a JSON
memory per video and re-sends the relevant history on every call.

  M0  same prompt, no memory (baseline to measure what memory adds)
  M1  memory as structured JSON text + the new frame
  M2  chat memory: previous 2 frames kept as user(image)/assistant(answer) messages + the new frame
Rule engine: UNSTABLE -> POSSIBLE_INCIDENT; FALLEN or 2 consecutive UNSTABLE -> LIKELY_INCIDENT.
On POSSIBLE/LIKELY, Qwen re-evaluates the whole progression (frames around the anomaly + memory).

Image per frame: Qwen auto crop when the motorcycle was detected (9.3-10.5 s), else the B road crop.
Expected: 8.3-9.7 NORMAL, 9.9 UNSTABLE (swerve), 10.0-10.2 UNSTABLE/FALLEN, 10.5 FALLEN, later NOT_VISIBLE.
"""
import base64, json, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
IMG = HERE / 'images'
TIMES = sorted(p.name[6:12] for p in IMG.glob('frame_*_B_crop_mask.png'))
AUTO = {p.name[6:12] for p in IMG.glob('frame_*_auto.png')} - {'008_30'}   # 8.3 s crop is too small to be useful
STATES = ['NORMAL', 'UNSTABLE', 'FALLEN', 'NOT_VISIBLE']
SCHEMA = {'type': 'object', 'required': ['a_evidence', 'b_state'],
          'properties': {'a_evidence': {'type': 'string'}, 'b_state': {'enum': STATES}}}
SYSTEM = ('You track one motorcycle and its rider across dashcam frames in time order. Gray boxes are masks; ignore them. '
          'For the new frame, first give at most 25 words of visible evidence about the motorcycle and rider, then its state: '
          'NORMAL = upright and ridden in control; UNSTABLE = leaning abnormally, swerving hard or losing balance; '
          'FALLEN = motorcycle on its side or rider on the ground; NOT_VISIBLE = no motorcycle in view. '
          'Earlier observations may be wrong; judge the new frame by what is visible in it.')


def seconds(t):
    return float(t.replace('_', '.'))


def image_of(t):
    return f'frame_{t}_auto.png' if t in AUTO else f'frame_{t}_B_crop_mask.png'


def b64(name):
    return base64.b64encode((IMG / name).read_bytes()).decode()


def call(messages, schema, num_predict=120):
    body = {'model': 'qwen2.5vl:7b', 'stream': False, 'format': schema, 'messages': messages,
            'options': {'temperature': 0, 'seed': 42, 'num_ctx': 12288, 'num_predict': num_predict}}
    started = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/chat', json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=1800))
    try:
        return json.loads(r['message']['content']), r['message']['content'], round(time.time() - started, 1)
    except json.JSONDecodeError:
        return {'a_evidence': r['message']['content'], 'b_state': 'NOT_VISIBLE'}, r['message']['content'], round(time.time() - started, 1)


def rule(observations):
    states = [o['state'] for o in observations]
    if 'FALLEN' in states or any(a == b == 'UNSTABLE' for a, b in zip(states, states[1:])):
        return 'LIKELY_INCIDENT'
    return 'POSSIBLE_INCIDENT' if 'UNSTABLE' in states else 'NO_INCIDENT_SO_FAR'


def track(variant):
    memory = {'video_id': 'INC-4043C786F1C4', 'last_timestamp': None, 'vehicle_state': None, 'incident_status': 'NO_INCIDENT_SO_FAR', 'observations': []}
    turns = []   # M2: previous (user, assistant) message pairs
    for t in TIMES:
        user_text = f'New frame at t={seconds(t):.1f}s.'
        if variant == 'M1':
            recent = {**memory, 'observations': memory['observations'][-5:]}
            user_text = f'Backend memory of earlier observations: {json.dumps(recent, ensure_ascii=False)}\n' + user_text
        user = {'role': 'user', 'content': user_text, 'images': [b64(image_of(t))]}
        history = [m for pair in turns[-2:] for m in pair] if variant == 'M2' else []
        answer, raw, wall = call([{'role': 'system', 'content': SYSTEM}, *history, user], SCHEMA)
        turns.append((user, {'role': 'assistant', 'content': raw}))
        memory['observations'].append({'timestamp': seconds(t), 'state': answer['b_state'], 'evidence': answer['a_evidence']})
        memory.update(last_timestamp=seconds(t), vehicle_state=answer['b_state'], incident_status=rule(memory['observations']))
        print(variant, f'{seconds(t):5.1f}s', f'{wall:5.1f}s', answer['b_state'], memory['incident_status'], '|', answer['a_evidence'], flush=True)
        (HERE / f'memory_{variant}.json').write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')
    return memory


def reevaluate(variant, memory):
    abnormal = [o['timestamp'] for o in memory['observations'] if o['state'] in ('UNSTABLE', 'FALLEN')]
    if not abnormal:
        return None
    # Frames from just before the first anomaly through the last frame where the motorcycle is tracked.
    window = [t for t in TIMES if t in AUTO and seconds(t) >= min(abnormal) - 0.5][:6]
    prompt = (f'Backend memory for this video: {json.dumps(memory, ensure_ascii=False)}\n'
              f'The attached images are crops around the motorcycle at t = {", ".join(f"{seconds(t):.1f}s" for t in window)}, in time order. '
              'Gray boxes are masks; ignore them. The memory may contain mistakes; check it against the images. '
              'First describe in at most 50 words how the motorcycle and rider progress across the images, then give the event type and your verdict.')
    schema = {'type': 'object', 'required': ['a_progression', 'b_event_type', 'c_verdict'], 'properties': {
        'a_progression': {'type': 'string'},
        'b_event_type': {'enum': ['LOSS_OF_CONTROL_FALL', 'NEAR_COLLISION', 'SWERVE_NO_FALL', 'OTHER', 'NONE']},
        'c_verdict': {'enum': ['INCIDENT', 'NO_INCIDENT', 'UNCERTAIN']}}}
    answer, _, wall = call([{'role': 'user', 'content': prompt, 'images': [b64(f'frame_{t}_auto.png') for t in window]}], schema, num_predict=200)
    result = {'window': [seconds(t) for t in window], **answer, 'wall_s': wall}
    print(variant, 'RE-EVALUATION', json.dumps(result, ensure_ascii=False), flush=True)
    return result


if __name__ == '__main__':
    summary = {}
    for variant in sys.argv[1:] or ['M0', 'M1', 'M2']:
        memory = track(variant)
        summary[variant] = {'incident_status': memory['incident_status'],
                            'states': {o['timestamp']: o['state'] for o in memory['observations']},
                            'reevaluation': reevaluate(variant, memory) if memory['incident_status'] != 'NO_INCIDENT_SO_FAR' else None}
        (HERE / 'memory_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
