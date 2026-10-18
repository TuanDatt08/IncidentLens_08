"""Same per-frame and labeled-reference questions, asked in Chinese (Qwen's strongest language).
Auto crops; controls 9.3/9.5/9.7 vs falling 10.0/10.2 and fallen 10.5.
"""
import json
from pathlib import Path

from run_tricks2 import chat

HERE = Path(__file__).parent
STATES = ['正常直立行驶', '倾斜或转弯', '已经摔倒或侧翻']
SCHEMA = {'type': 'object', 'required': ['a_description', 'b_state'], 'properties': {'a_description': {'type': 'string'}, 'b_state': {'enum': STATES}}}
FRAME = '这是行车记录仪画面中一辆摩托车的局部裁剪。灰色方块是遮挡区域，请忽略。请先用不超过30个字描述摩托车和骑手的姿态，然后判断摩托车的状态。'
PAIR = ('图1是参考画面：摩托车直立，正常行驶。图2是同一辆摩托车稍后的画面。灰色方块是遮挡区域，请忽略。'
        '请先用不超过30个字描述图2与图1的不同，然后判断图2中摩托车的状态。')
GT = {'009_30': 'upright', '009_50': 'upright', '009_70': 'upright', '010_00': 'falling', '010_20': 'falling', '010_50': 'fallen'}
results = {'frame': {}, 'pair': {}}
for t in GT:
    answer, _ = chat(FRAME, [f'frame_{t}_auto.png'], SCHEMA, num_predict=120)
    results['frame'][t] = answer
    print('frame', t, f'[{GT[t]}]', json.dumps(answer, ensure_ascii=False), flush=True)
for a, b in [('009_30', '009_50'), ('009_50', '009_70'), ('009_50', '010_00'), ('009_50', '010_20'), ('009_50', '010_50')]:
    answer, _ = chat(PAIR, [f'frame_{a}_auto.png', f'frame_{b}_auto.png'], SCHEMA, num_predict=120)
    results['pair'][f'{a}->{b}'] = answer
    print('pair', f'{a}->{b}', f'[{GT[b]}]', json.dumps(answer, ensure_ascii=False), flush=True)
(HERE / 'chinese_results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
