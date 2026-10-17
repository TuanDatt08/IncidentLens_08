"""Re-run the key 7B tests on another model (QWEN_MODEL=...), same images, same controls.

  1 per-frame state on auto crops (9.3-10.5)
  2 labeled-upright reference pairs, description first
  3 multi-frame multiple choice on the fixed C window (event vs control)
"""
import json
from pathlib import Path

from qwen import TAG, TEXT, chat, obj

HERE = Path(__file__).parent
IMG = HERE.parent / 'local-q8-state' / 'images'
OUT = HERE / f'battery_{TAG}.json'
GT = {'009_30': 'upright', '009_50': 'upright', '009_70': 'upright', '009_90': 'swerve',
      '010_00': 'falling', '010_10': 'falling', '010_20': 'falling', '010_50': 'fallen'}
STATES = ['upright_riding', 'leaning_or_turning', 'falling_or_fallen']
results = {}


def record(test, key, value):
    results.setdefault(test, {})[key] = value
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(test, key, f'[{GT.get(key.split("->")[-1], key)}]', json.dumps(value, ensure_ascii=False), flush=True)


for t in GT:
    answer, _, _, wall = chat('This is a crop of a motorcycle from a forward dashcam. Gray boxes are masks; ignore them. '
                              'First describe in at most 30 words the posture of the motorcycle and its rider, then give the state of the motorcycle.',
                              [IMG / f'frame_{t}_auto.png'], obj(a_description=TEXT, b_state={'enum': STATES}), num_predict=150)
    record('per_frame', t, {**answer, 'wall_s': wall})

for a, b in [('009_30', '009_50'), ('009_50', '009_70'), ('009_50', '009_90'), ('009_50', '010_00'), ('009_50', '010_20'), ('009_50', '010_50')]:
    answer, _, _, wall = chat('Image 1 is a reference: the motorcycle is upright and being ridden normally. Image 2 shows the same motorcycle a moment later. '
                              'Gray boxes are masks; ignore them. First describe in at most 30 words how the motorcycle and rider in image 2 differ from image 1, '
                              'then give the state of the motorcycle in image 2.',
                              [IMG / f'frame_{a}_auto.png', IMG / f'frame_{b}_auto.png'], obj(a_difference=TEXT, b_state={'enum': STATES}), num_predict=150)
    record('pair_labeled', f'{a}->{b}', {**answer, 'wall_s': wall})

SEQ = ('These are consecutive crops from the same forward dashcam, in time order. Gray boxes are masks; ignore them. '
       'First describe in at most 40 words how the motorcycle and its rider change across the images, '
       'then choose: A) rides past normally, staying upright B) swerves to the roadside but stays upright and in control '
       'C) loses balance and tips over or falls D) no motorcycle visible.')
for name, frames in [('control', ['009_30', '009_50', '009_70']), ('event', ['009_90', '010_00', '010_20', '010_50'])]:
    answer, _, _, wall = chat(SEQ, [IMG / f'frame_{f}_C_zoom.png' for f in frames], obj(a_change=TEXT, b_choice={'enum': ['A', 'B', 'C', 'D']}), num_predict=180)
    record('sequence_mc', name, {**answer, 'wall_s': wall})
