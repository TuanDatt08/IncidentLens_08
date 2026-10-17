"""Three consecutive masked crops in one request + multiple-choice question.

Event set: 9.5 / 10.0 / 10.2 s (motorcycle approaches, swerves, falls).
Control set: 11.5 / 12.5 / 13.5 s (no motorcycle in view).
"""
import base64, json, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
SETS = {'event': ['frame_009_50', 'frame_010_00', 'frame_010_20'], 'control': ['frame_011_50', 'frame_012_50', 'frame_013_50']}
SCHEMA = {'type': 'object', 'required': ['choice', 'evidence'], 'properties': {
    'choice': {'enum': ['A', 'B', 'C', 'D', 'E']}, 'evidence': {'type': 'string'}}}


def question(frames):
    times = ', '.join(f'Image {i} = {float(f[6:].replace("_", ".")):.1f}s' for i, f in enumerate(frames, 1))
    return f"""These are consecutive crops from the same forward dashcam, in time order: {times}.
Gray boxes are masks; ignore them. Focus on any motorcycle and its rider.
Which option best describes what happens to the motorcycle across the images?
A) it rides past normally, staying upright on the road
B) it swerves to the roadside but stays upright and in control
C) it loses balance and tips over or falls
D) it collides with the camera car
E) no motorcycle is visible
Answer with the option letter and at most 25 words of evidence citing image numbers."""


def run(sets, suffix='_B_crop_mask.png', out_name='sequence_results.json'):
    results = {}
    for name, frames in sets.items():
        images = [base64.b64encode((HERE / 'images' / f'{f}{suffix}').read_bytes()).decode() for f in frames]
        body = {'model': 'qwen2.5vl:7b', 'stream': False, 'format': SCHEMA,
                'options': {'temperature': 0, 'seed': 42, 'num_ctx': 8192, 'num_predict': 200},
                'messages': [{'role': 'user', 'content': question(frames), 'images': images}]}
        started = time.time()
        r = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/chat', json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=1800))
        results[name] = {'frames': frames, 'question': question(frames), 'answer': json.loads(r['message']['content']),
                         'wall_s': round(time.time() - started, 1), 'prompt_tokens': r.get('prompt_eval_count'), 'output_tokens': r.get('eval_count')}
        print(name, json.dumps(results[name]['answer'], ensure_ascii=False), f"{results[name]['wall_s']}s", flush=True)
    (HERE / out_name).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return results


if __name__ == '__main__':
    run(SETS)
