"""Statistical fall check: labeled-upright reference vs target (auto crops), 6 samples at
temperature 0.7, each description judged by a text-only Qwen call; flag a pair when more
than half of the samples say the motorcycle fell. Same procedure for control and event pairs.
"""
import json
from pathlib import Path

from run_tricks2 import chat

HERE = Path(__file__).parent
OUT = HERE / 'vote6_results.json'
GT = {'009_50': 'upright', '009_70': 'upright', '009_90': 'swerve', '010_00': 'falling', '010_10': 'falling', '010_20': 'falling', '010_50': 'fallen'}
PAIRS = [('009_30', '009_50'), ('009_30', '009_70'), ('009_50', '009_70'),
         ('009_50', '009_90'), ('009_50', '010_00'), ('009_50', '010_10'), ('009_50', '010_20'), ('009_50', '010_50')]
DESCRIBE = ('Image 1 is a reference: the motorcycle is upright and being ridden normally. Image 2 shows the same motorcycle a moment later. '
            'Gray boxes are masks; ignore them. In at most 30 words, describe how the motorcycle and rider in image 2 differ from image 1.')
JUDGE = ('Description of how a motorcycle changed between two dashcam images: "{text}"\n'
         'Does this description state that the motorcycle has fallen, tipped over, overturned or is lying on its side, or that the rider fell off? '
         'Merely leaning, tilting or turning does not count. Give a reason in at most 12 words, then answer.')
D_SCHEMA = {'type': 'object', 'required': ['difference'], 'properties': {'difference': {'type': 'string'}}}
J_SCHEMA = {'type': 'object', 'required': ['a_reason', 'b_says_fallen'], 'properties': {'a_reason': {'type': 'string'}, 'b_says_fallen': {'type': 'boolean'}}}

results = {}
for a, b in PAIRS:
    samples = []
    for seed in range(11, 17):
        described, _ = chat(DESCRIBE, [f'frame_{a}_auto.png', f'frame_{b}_auto.png'], D_SCHEMA, num_predict=120, options={'temperature': 0.7, 'seed': seed})
        text = described.get('difference', described.get('unparsed', ''))
        judged, _ = chat(JUDGE.format(text=text), [], J_SCHEMA, num_predict=60)
        samples.append({'text': text, 'says_fallen': bool(judged.get('b_says_fallen'))})
    votes = sum(s['says_fallen'] for s in samples)
    results[f'{a}->{b}'] = {'truth': GT[b], 'votes': f'{votes}/6', 'flag_fall': votes > 3, 'samples': samples}
    print(f'{a}->{b} [{GT[b]}] fallen votes {votes}/6 flag={votes > 3}', flush=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
