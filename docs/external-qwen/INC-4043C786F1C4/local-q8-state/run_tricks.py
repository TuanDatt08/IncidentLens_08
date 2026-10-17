"""Prompt/visual tricks to make local qwen2.5vl:7b see the motorcycle fall. Every trick
runs on event frames AND control frames (9.3-9.7 s, same motorcycle riding normally).

T = tight 448x448 crop around the motorcycle (ornament masked), C = fixed 720x440 window,
H = numbered strip of three T crops.
"""
import base64, json, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
IMG = HERE / 'images'
CONTROL, EVENT = ['009_30', '009_50', '009_70'], ['009_90', '010_00', '010_20', '010_50']
results = {}


def chat(messages, schema, num_ctx=8192, num_predict=300):
    body = {'model': 'qwen2.5vl:7b', 'stream': False, 'messages': messages,
            'options': {'temperature': 0, 'seed': 42, 'num_ctx': num_ctx, 'num_predict': num_predict}}
    if schema:
        body['format'] = schema
    started = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/chat', json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=1800))
    return r['message']['content'], round(time.time() - started, 1)


def b64(name):
    return base64.b64encode((IMG / name).read_bytes()).decode()


def record(trick, key, answer, wall):
    results.setdefault(trick, {})[key] = {'answer': answer, 'wall_s': wall}
    print(trick, key, f'{wall}s', answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False), flush=True)
    (HERE / 'tricks_results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


# D: yes/no posture questions on tight crops.
D_SCHEMA = {'type': 'object', 'required': ['motorcycle_visible', 'motorcycle_lying_on_its_side', 'motorcycle_leaning_strongly', 'rider_seated_upright_and_balanced', 'rider_body_or_foot_touching_ground'],
            'properties': {k: {'type': 'boolean'} for k in ['motorcycle_visible', 'motorcycle_lying_on_its_side', 'motorcycle_leaning_strongly', 'rider_seated_upright_and_balanced', 'rider_body_or_foot_touching_ground']}}
D_PROMPT = ('Look closely at the motorcycle and its rider in this image. Gray boxes are masks; ignore them. '
            'Answer each question about this single image only: is a motorcycle visible; is the motorcycle lying on its side on the ground; '
            'is it leaning strongly to one side; is the rider seated upright and balanced; is the rider\'s body or foot touching the ground.')
for t in CONTROL + EVENT:
    raw, wall = chat([{'role': 'user', 'content': D_PROMPT, 'images': [b64(f'frame_{t}_T_tight.png')]}], D_SCHEMA)
    record('D_yes_no_tight', t, json.loads(raw), wall)

# F: free description first, then classify in the same conversation.
F_DESCRIBE = ('Describe only the motorcycle and its rider in this image: the angle of the motorcycle relative to the ground, '
              'whether both wheels stand on the ground, and where the rider\'s body, legs and feet are. Gray boxes are masks; ignore them. Max 60 words.')
F_CLASSIFY = 'Based on your description, which is it? A) upright and ridden normally B) leaning but still ridden C) tipped over or falling, rider losing balance or on the ground'
F_SCHEMA = {'type': 'object', 'required': ['choice'], 'properties': {'choice': {'enum': ['A', 'B', 'C']}}}
for t in ['009_70', '010_20', '010_50']:
    first = {'role': 'user', 'content': F_DESCRIBE, 'images': [b64(f'frame_{t}_T_tight.png')]}
    description, wall1 = chat([first], None, num_predict=150)
    choice, wall2 = chat([first, {'role': 'assistant', 'content': description}, {'role': 'user', 'content': F_CLASSIFY}], F_SCHEMA)
    record('F_describe_then_classify', t, {'description': description, 'choice': json.loads(choice)['choice']}, round(wall1 + wall2, 1))

# G: labeled upright reference + target.
G_PROMPT = ('Image 1 is a reference: the motorcycle is upright and being ridden normally. Image 2 shows the same motorcycle a moment later. '
            'Gray boxes are masks; ignore them. Compared with image 1, what is the state of the motorcycle in image 2?')
G_SCHEMA = {'type': 'object', 'required': ['state_in_image_2', 'evidence'], 'properties': {
    'state_in_image_2': {'enum': ['same_upright_ridden', 'leaning_more', 'lying_on_its_side', 'not_visible']}, 'evidence': {'type': 'string'}}}
for ref, target in [('009_30', '009_70'), ('009_50', '010_20'), ('009_50', '010_50')]:
    raw, wall = chat([{'role': 'user', 'content': G_PROMPT, 'images': [b64(f'frame_{ref}_T_tight.png'), b64(f'frame_{target}_T_tight.png')]}], G_SCHEMA)
    record('G_labeled_reference', f'{ref}->{target}', json.loads(raw), wall)

# H: one numbered strip image with three moments.
H_PROMPT = ('This single image is a strip of three numbered panels (1, 2, 3, left to right) showing the same motorcycle in time order. '
            'Gray boxes are masks; ignore them. What happens to the motorcycle from panel 1 to panel 3? '
            'A) it keeps riding upright normally B) it swerves but stays upright and in control C) it loses balance and tips over or falls '
            'Answer with the letter and at most 25 words of evidence citing panel numbers.')
H_SCHEMA = {'type': 'object', 'required': ['choice', 'evidence'], 'properties': {'choice': {'enum': ['A', 'B', 'C']}, 'evidence': {'type': 'string'}}}
for name in ['control', 'event']:
    raw, wall = chat([{'role': 'user', 'content': H_PROMPT, 'images': [b64(f'strip_{name}_H.png')]}], H_SCHEMA)
    record('H_numbered_strip', name, json.loads(raw), wall)

# I: grounding; code reads box geometry instead of trusting a posture label.
I_PROMPT = 'Locate the motorcycle together with its rider in this image. Output its bounding box in pixel coordinates of this image.'
I_SCHEMA = {'type': 'object', 'required': ['bbox_2d'], 'properties': {'bbox_2d': {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 4, 'maxItems': 4}}}
for t in CONTROL + EVENT + ['010_10']:
    raw, wall = chat([{'role': 'user', 'content': I_PROMPT, 'images': [b64(f'frame_{t}_C_zoom.png')]}], I_SCHEMA, num_predict=60)
    record('I_grounding_C', t, json.loads(raw), wall)
