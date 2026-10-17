"""Per-frame state test on local Ollama qwen2.5vl:7b (Q8_0 GGUF import).

Qwen only reports the visible state of each road user in one image; code links the
frames and decides. Variant A = full frame at 640 px (what the backend sends today);
variant B = road crop 1200x480 with the windshield ornament masked (hand-picked
coordinates for this clip).
"""
import base64, json, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
URL = 'http://127.0.0.1:11434/api/chat'
SYSTEM = """You inspect ONE dashcam image taken from the ego car looking forward.
Ignore anything attached to the ego car: windshield ornaments, dashboard, hood, and gray masked boxes.
List each motorcycle, bicycle, car, truck and person on or beside the road ahead. Report only what is visible in this single image:
- state: upright (normal riding, driving or standing), tilted (clearly leaning or losing balance), fallen (lying on the ground or toppled), unclear
- place: road, roadside, off_road, unclear
- position: left, center or right of the image
- distance: near, mid or far
- note: at most 12 words of visible evidence
Do not guess motion or speed. Use unclear when unsure. Return an empty list if no road user is visible."""
OBJ = {'type': 'object', 'required': ['type', 'state', 'place', 'position', 'distance', 'note'], 'properties': {
    'type': {'enum': ['motorcycle', 'bicycle', 'car', 'truck', 'person']},
    'state': {'enum': ['upright', 'tilted', 'fallen', 'unclear']},
    'place': {'enum': ['road', 'roadside', 'off_road', 'unclear']},
    'position': {'enum': ['left', 'center', 'right']},
    'distance': {'enum': ['near', 'mid', 'far']},
    'note': {'type': 'string'}}}
SCHEMA = {'type': 'object', 'required': ['objects'], 'properties': {'objects': {'type': 'array', 'items': OBJ}}}
VARIANTS = {'B': '_B_crop_mask.png', 'A': '_A_full640.png'}
ABNORMAL = {'tilted', 'fallen'}


def ask(image: Path) -> dict:
    body = {'model': 'qwen2.5vl:7b', 'stream': False, 'format': SCHEMA,
            'options': {'temperature': 0, 'seed': 42, 'num_ctx': 4096, 'num_predict': 400},
            'messages': [{'role': 'system', 'content': SYSTEM},
                         {'role': 'user', 'content': 'Report the road users in this image.',
                          'images': [base64.b64encode(image.read_bytes()).decode()]}]}
    request = urllib.request.Request(URL, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(request, timeout=900))


def verdict(rows: list[dict]) -> dict:
    # Two distinct frames showing a tilted/fallen motorcycle or rider = loss-of-control candidate.
    flagged = [r['time_s'] for r in rows if any(o['type'] in {'motorcycle', 'person'} and o['state'] in ABNORMAL for o in r['objects'])]
    return {'flagged_frames_s': flagged,
            'status': 'LOSS_OF_CONTROL_CANDIDATE' if len(flagged) >= 2 else 'INCONCLUSIVE' if flagged else 'NO_ABNORMAL_STATE_SEEN'}


def main():
    frames = sorted(p.name.removesuffix(VARIANTS['B']) for p in (HERE / 'images').glob('*' + VARIANTS['B']))
    results = {'model': 'qwen2.5vl:7b (local Q8_0 GGUF + f16 mmproj)', 'system_prompt': SYSTEM, 'schema': SCHEMA, 'runs': {}}
    for variant, suffix in VARIANTS.items():
        rows = results['runs'].setdefault(variant, {'frames': []})['frames']
        for name in frames:
            started = time.time()
            r = ask(HERE / 'images' / (name + suffix))
            objects = json.loads(r['message']['content'])['objects']
            rows.append({'frame': name, 'time_s': float(name[6:].replace('_', '.')), 'objects': objects, 'wall_s': round(time.time() - started, 1),
                         'prompt_tokens': r.get('prompt_eval_count'), 'output_tokens': r.get('eval_count'), 'raw': r['message']['content']})
            print(f"{variant} {name} {rows[-1]['wall_s']:6.1f}s  " + '; '.join(f"{o['type']}:{o['state']}/{o['place']}/{o['position']}" for o in objects), flush=True)
            (HERE / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        results['runs'][variant]['verdict'] = verdict(rows)
        print(variant, 'VERDICT', results['runs'][variant]['verdict'], flush=True)
        (HERE / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
