"""Round 3: keep Qwen on what it does well (localize, describe a difference) and let code decide.

J: two boxes per frame (motorcycle, rider) on the fixed C window -> code compares rider pose to the bike.
G3: free-text difference vs a labeled upright reference, no enum -> code keyword match.
"""
import json, re
from pathlib import Path

from run_tricks2 import chat

HERE = Path(__file__).parent
OUT = HERE / 'tricks3_results.json'
SX, SY = 720 / 1148, 440 / 728   # model sees smart_resize(720x440) = 1148x728; map back to crop pixels
results = {'J_two_boxes_C': {}, 'G3_free_text': {}}


def save():
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


BOX = {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 4, 'maxItems': 4}
J = ('Locate two things in this image and output their bounding boxes in pixel coordinates of this image: '
     '(a) the motorcycle itself, (b) the whole body of its rider from head to feet.')
J_SCHEMA = {'type': 'object', 'required': ['a_motorcycle_bbox', 'b_rider_bbox'], 'properties': {'a_motorcycle_bbox': BOX, 'b_rider_bbox': BOX}}
for t in ['009_30', '009_50', '009_70', '009_90', '010_00', '010_10', '010_20', '010_50']:
    answer, wall = chat(J, [f'frame_{t}_C_zoom.png'], J_SCHEMA, num_predict=80)
    if 'unparsed' not in answer:
        m, r = ([round(v * (SX if i % 2 == 0 else SY)) for i, v in enumerate(answer[k])] for k in ('a_motorcycle_bbox', 'b_rider_bbox'))
        bike_h, rider_w, rider_h = m[3] - m[1], r[2] - r[0], r[3] - r[1]
        answer['crop_px'] = {'motorcycle': m, 'rider': r}
        # Upright rider: tall box, head well above the bike. Fallen rider: wide box, head near bike top.
        answer['geometry'] = {'rider_h_over_w': round(rider_h / rider_w, 2), 'head_above_bike_top_over_bike_h': round((m[1] - r[1]) / bike_h, 2)}
    results['J_two_boxes_C'][t] = {'answer': answer, 'wall_s': wall}
    print('J', t, f'{wall}s', json.dumps(answer.get('geometry', answer), ensure_ascii=False), flush=True)
    save()

FALL = re.compile(r'on its side|fall|fell|tip(ped|s)? over|toppl|off the (bike|motorcycle)|lying|on the ground|knocked over', re.I)
G = ('Image 1 is a reference: the motorcycle is upright and being ridden normally. Image 2 shows the same motorcycle a moment later. '
     'Gray boxes are masks; ignore them. In at most 30 words, describe how the motorcycle and rider in image 2 differ from image 1.')
G_SCHEMA = {'type': 'object', 'required': ['difference'], 'properties': {'difference': {'type': 'string'}}}
pairs = [('009_30', '009_50'), ('009_30', '009_70'), ('009_50', '009_90'), ('009_50', '010_00'), ('009_50', '010_20'), ('009_50', '010_50'), ('009_30', '010_50'), ('009_70', '010_20')]
for ref, target in pairs:
    answer, wall = chat(G, [f'frame_{ref}_T_tight.png', f'frame_{target}_T_tight.png'], G_SCHEMA, num_predict=120)
    text = answer.get('difference', answer.get('unparsed', ''))
    answer['fall_keyword'] = bool(FALL.search(text))
    results['G3_free_text'][f'{ref}->{target}'] = {'answer': answer, 'wall_s': wall}
    print('G3', f'{ref}->{target}', f'{wall}s', json.dumps(answer, ensure_ascii=False), flush=True)
    save()
