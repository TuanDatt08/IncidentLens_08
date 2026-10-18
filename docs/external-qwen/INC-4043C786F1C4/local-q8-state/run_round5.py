"""Round 5: every remaining prompt/visual trick for the 7B model, each with controls.

Ground truth (by eye): 9.3/9.5/9.7 upright riding (control), 9.9 swerve onset,
10.0/10.1/10.2 falling, 10.5 fallen. Usage: python run_round5.py <stage>|all
"""
import json, math, sys
from pathlib import Path

from run_tricks2 import chat

HERE = Path(__file__).parent
OUT = HERE / 'round5_results.json'
GT = {'009_30': 'upright', '009_50': 'upright', '009_70': 'upright', '009_90': 'swerve',
      '010_00': 'falling', '010_10': 'falling', '010_20': 'falling', '010_50': 'fallen'}
FRAMES = list(GT)
CONTROL_PAIRS = [('009_30', '009_50'), ('009_30', '009_70'), ('009_50', '009_70')]
EVENT_PAIRS = [('009_50', '009_90'), ('009_50', '010_00'), ('009_50', '010_20'), ('009_50', '010_50')]
STATES = ['upright_riding', 'leaning_or_turning', 'fallen_on_its_side']
results = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}


def record(stage, key, value):
    results.setdefault(stage, {})[key] = value
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    label = GT.get(key) or GT.get(key.split('->')[-1], '')
    print(stage, key, f'[{label}]', json.dumps(value, ensure_ascii=False), flush=True)


def obj(**props):
    return {'type': 'object', 'required': list(props), 'properties': props}


TEXT, POINT = {'type': 'string'}, {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 2, 'maxItems': 2}


def keypoints():
    # Code measures lean from Qwen's points: line front-wheel-bottom -> handlebar, angle from vertical.
    prompt = ('Point to these parts of the motorcycle and rider in this image, in pixel coordinates of this image: '
              '(a) center of the handlebar, (b) bottom of the front wheel where it touches the ground, (c) the rider\'s head, (d) center of the seat. '
              'Gray boxes are masks; ignore them.')
    schema = obj(a_handlebar_center=POINT, b_front_wheel_bottom=POINT, c_rider_head=POINT, d_seat_center=POINT)
    for t in FRAMES:
        answer, wall = chat(prompt, [f'frame_{t}_auto.png'], schema, num_predict=80)
        if 'unparsed' not in answer:
            (hx, hy), (wx, wy), (rx, ry) = answer['a_handlebar_center'], answer['b_front_wheel_bottom'], answer['c_rider_head']
            answer['lean_deg'] = round(math.degrees(math.atan2(abs(hx - wx), wy - hy)), 1)
            answer['head_height_over_bar_height'] = round((wy - ry) / (wy - hy), 2) if wy != hy else None
        record('keypoints', t, {**answer, 'wall_s': wall})


def angle():
    prompt = ('Estimate how far the motorcycle in this image is tilted from vertical, in degrees: 0 = perfectly upright, 30 = clearly leaning, '
              '60 = about to fall, 90 = lying flat on its side. Gray boxes are masks; ignore them. First describe its tilt in at most 20 words, then give the angle.')
    for t in FRAMES:
        answer, wall = chat(prompt, [f'frame_{t}_auto.png'], obj(a_observation=TEXT, b_tilt_deg={'type': 'integer'}), num_predict=100)
        record('angle', t, {**answer, 'wall_s': wall})


def redbox():
    prompt = ('Focus on the motorcycle and rider inside the red box. Gray boxes are masks; ignore them. '
              'First describe in at most 20 words its posture and where it is, then give its state and its location.')
    schema = obj(a_observation=TEXT, b_state={'enum': STATES}, c_location={'enum': ['paved_road', 'roadside_dirt_or_vegetation']})
    for t in FRAMES:
        answer, wall = chat(prompt, [f'frame_{t}_R_redbox.png'], schema, num_predict=100)
        record('redbox', t, {**answer, 'wall_s': wall})


def debate():
    prompt = ('Image 1 is a reference: the motorcycle is upright and being ridden normally. Image 2 shows the same motorcycle a moment later. '
              'Gray boxes are masks; ignore them. In image 2, first list in at most 20 words the evidence that it is still upright or only leaning, '
              'then in at most 20 words the evidence that it is falling or has fallen, then give your verdict.')
    schema = obj(a_evidence_still_upright=TEXT, b_evidence_falling_or_fallen=TEXT, c_verdict={'enum': ['still_upright_or_leaning', 'falling_or_fallen']})
    for a, b in CONTROL_PAIRS + EVENT_PAIRS:
        answer, wall = chat(prompt, [f'frame_{a}_auto.png', f'frame_{b}_auto.png'], schema, num_predict=160)
        record('debate', f'{a}->{b}', {**answer, 'wall_s': wall})


def panel():
    prompt = ('This image has two panels: BEFORE on the left (the motorcycle upright and ridden normally) and AFTER on the right (the same motorcycle a moment later). '
              'Gray boxes are masks; ignore them. First describe in at most 30 words how the motorcycle and rider differ in AFTER, then give its state in AFTER.')
    for a, b in [('009_30', '009_50'), ('009_50', '009_70'), ('009_50', '009_90'), ('009_50', '010_20'), ('009_50', '010_50')]:
        answer, wall = chat(prompt, [f'pair_{a}_{b}_P.png'], obj(a_difference=TEXT, b_state_after={'enum': STATES}), num_predict=120)
        record('panel', f'{a}->{b}', {**answer, 'wall_s': wall})


def fewshot():
    prompt = ('Image 1 is an example of a motorcycle that is UPRIGHT. Image 2 is an example of a motorcycle LYING ON ITS SIDE (fallen). '
              'Image 3 is the query. Gray boxes are masks; ignore them. First describe in at most 20 words the motorcycle in image 3, then classify image 3.')
    for t in ['009_50', '009_70', '009_90', '010_00', '010_20', '010_50']:
        answer, wall = chat(prompt, ['example_upright.png', 'example_fallen_rot90.png', f'frame_{t}_auto.png'],
                            obj(a_observation=TEXT, b_state_image_3={'enum': ['upright', 'leaning', 'fallen']}), num_predict=100)
        record('fewshot', t, {**answer, 'wall_s': wall})


SEQ = ('These are consecutive crops from the same forward dashcam, in time order. Gray boxes are masks; ignore them. '
       'First describe in at most 40 words how the motorcycle and its rider change across the images, '
       'then choose: A) rides past normally, staying upright B) swerves to the roadside but stays upright and in control '
       'C) loses balance and tips over or falls D) no motorcycle visible.')
SEQ_SCHEMA = obj(a_change=TEXT, b_choice={'enum': ['A', 'B', 'C', 'D']})
SEQ_SETS = {'control': ['009_30', '009_50', '009_70'], 'event': ['009_90', '010_00', '010_20', '010_50']}


def persona():
    system = ('You are a traffic accident analyst reviewing dashcam footage of two-wheeler incidents. Riders sometimes lose control and fall; '
              'report a fall whenever the images show one, and do not report one when the rider stays in control.')
    for name, frames in SEQ_SETS.items():
        answer, wall = chat(SEQ, [f'frame_{f}_C_zoom.png' for f in frames], SEQ_SCHEMA, num_predict=160, system=system)
        record('persona', name, {**answer, 'wall_s': wall})


def vote():
    for name, frames in SEQ_SETS.items():
        picks = []
        for seed in range(1, 6):
            answer, _ = chat(SEQ, [f'frame_{f}_C_zoom.png' for f in frames], SEQ_SCHEMA, num_predict=160, options={'temperature': 0.7, 'seed': seed})
            picks.append(answer.get('b_choice', '?'))
        record('vote', name, {'choices': picks})


def judge():
    # Re-read every free-text comparison collected so far with a text-only Qwen call instead of a regex.
    texts = []
    for f, path in [('tricks', ('G_labeled_reference', 'evidence')), ('tricks2', ('G2_reference_reason_first', 'a_difference')), ('tricks3', ('G3_free_text', 'difference'))]:
        data = json.loads((HERE / f'{f}_results.json').read_text(encoding='utf-8')).get(path[0], {})
        texts += [(f'{path[0]} {k}', v['answer'].get(path[1], '')) for k, v in data.items()]
    auto = json.loads((HERE / 'auto_results.json').read_text(encoding='utf-8'))
    texts += [(f'auto_labeled {k} #{i}', s['text']) for k, v in auto.get('labeled_reference', {}).items() for i, s in enumerate(v['samples'])]
    texts += [(f'round5_panel {k}', v.get('a_difference', '')) for k, v in results.get('panel', {}).items()]
    schema = obj(a_reason=TEXT, b_says_fallen={'type': 'boolean'})
    for key, text in texts:
        prompt = (f'Description of how a motorcycle changed between two dashcam images: "{text}"\n'
                  'Does this description state that the motorcycle has fallen, tipped over, overturned or is lying on its side, or that the rider fell off? '
                  'Merely leaning, tilting or turning does not count. Give a reason in at most 12 words, then answer.')
        answer, _ = chat(prompt, [], schema, num_predict=60)
        record('judge', key, {'text': text, **answer})


STAGES = {f.__name__: f for f in [keypoints, angle, redbox, debate, panel, fewshot, persona, vote, judge]}
if __name__ == '__main__':
    for stage in (STAGES if sys.argv[1] == 'all' else [sys.argv[1]]):
        STAGES[stage]()
