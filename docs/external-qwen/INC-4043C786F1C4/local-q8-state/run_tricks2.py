"""Round 2. Ollama's JSON-schema grammar emits keys in alphabetical order, so a schema with
`choice` + `evidence` makes the model answer BEFORE it reasons. Here keys are named
a_* (observation) then b_* (verdict) so the reasoning is generated first.
Every trick still runs on control frames (9.3-9.9 s, same motorcycle riding normally).
"""
import base64, json, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
IMG = HERE / 'images'
OUT = HERE / 'tricks2_results.json'
results = {}


def chat(content, images, schema, num_predict=400, options=None, system=None):
    body = {'model': 'qwen2.5vl:7b', 'stream': False, 'format': schema,
            'options': {'temperature': 0, 'seed': 42, 'num_ctx': 8192, 'num_predict': num_predict, **(options or {})},
            'messages': ([{'role': 'system', 'content': system}] if system else []) +
                        [{'role': 'user', 'content': content, 'images': [base64.b64encode((IMG / i).read_bytes()).decode() for i in images]}]}
    started = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/chat', json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=1800))
    raw = r['message']['content']
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError:
        answer = {'unparsed': raw}
    return answer, round(time.time() - started, 1)


def run(trick, key, content, images, schema, num_predict=400):
    answer, wall = chat(content, images, schema, num_predict)
    results.setdefault(trick, {})[key] = {'images': images, 'answer': answer, 'wall_s': wall}
    print(trick, key, f'{wall}s', json.dumps(answer, ensure_ascii=False), flush=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    STATES = ['upright_riding', 'leaning_or_turning', 'fallen_on_its_side']

    # G2: labeled upright reference, observation first.
    G = ('Image 1 is a reference: the motorcycle is upright and being ridden normally. Image 2 shows the same motorcycle a moment later. '
         'Gray boxes are masks; ignore them. First describe in at most 30 words how the motorcycle and rider in image 2 differ from image 1, '
         'then give the state of the motorcycle in image 2.')
    G_SCHEMA = {'type': 'object', 'required': ['a_difference', 'b_state_in_image_2'],
                'properties': {'a_difference': {'type': 'string'}, 'b_state_in_image_2': {'enum': STATES}}}
    for ref, target in [('009_30', '009_70'), ('009_30', '009_90'), ('009_50', '010_00'), ('009_50', '010_20'), ('009_50', '010_50')]:
        run('G2_reference_reason_first', f'{ref}->{target}', G, [f'frame_{ref}_T_tight.png', f'frame_{target}_T_tight.png'], G_SCHEMA)

    # H2: numbered strip, observation first.
    H = ('This single image is a strip of three numbered panels (1, 2, 3, left to right) showing the same motorcycle in time order. '
         'Gray boxes are masks; ignore them. First describe in at most 40 words how the motorcycle and rider change from panel 1 to panel 3, '
         'then choose: A) keeps riding upright normally B) swerves but stays upright and in control C) loses balance and tips over or falls.')
    H_SCHEMA = {'type': 'object', 'required': ['a_change', 'b_choice'], 'properties': {'a_change': {'type': 'string'}, 'b_choice': {'enum': ['A', 'B', 'C']}}}
    for name in ['control', 'event']:
        run('H2_strip_reason_first', name, H, [f'strip_{name}_H.png'], H_SCHEMA)

    # S2: earlier multi-image multiple choice (fixed C window), observation first.
    S = ('These are consecutive crops from the same forward dashcam, in time order. Gray boxes are masks; ignore them. '
         'First describe in at most 40 words how the motorcycle and its rider change across the images, '
         'then choose: A) rides past normally, staying upright B) swerves to the roadside but stays upright and in control '
         'C) loses balance and tips over or falls D) no motorcycle visible.')
    S_SCHEMA = {'type': 'object', 'required': ['a_change', 'b_choice'], 'properties': {'a_change': {'type': 'string'}, 'b_choice': {'enum': ['A', 'B', 'C', 'D']}}}
    for name, frames in [('control', ['009_30', '009_50', '009_70']), ('event', ['009_90', '010_00', '010_20', '010_50'])]:
        run('S2_sequence_reason_first', name, S, [f'frame_{f}_C_zoom.png' for f in frames], S_SCHEMA)

    # I: grounding on the fixed C window; code reads box geometry.
    I = 'Locate the motorcycle together with its rider in this image. Output its bounding box in pixel coordinates of this image.'
    I_SCHEMA = {'type': 'object', 'required': ['bbox_2d'], 'properties': {'bbox_2d': {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 4, 'maxItems': 4}}}
    for t in ['009_30', '009_50', '009_70', '009_90', '010_00', '010_10', '010_20', '010_50']:
        run('I_grounding_C', t, I, [f'frame_{t}_C_zoom.png'], I_SCHEMA, num_predict=60)
