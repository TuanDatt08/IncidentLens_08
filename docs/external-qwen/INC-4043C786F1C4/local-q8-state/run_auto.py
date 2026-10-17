"""Round 4: the round-3 winner without hand-picked crop windows.

  python run_auto.py ground   -> Qwen boxes the motorcycle on each B road crop; boxes mapped to full-frame pixels
  (make_auto_crops.ps1)       -> square crop around each box from the full frame (ornament still masked by hand)
  python run_auto.py compare  -> free-text change for consecutive frames (3 samples each) and vs the first
                                 detected frame; code flags fall keywords and votes.
"""
import json, math, re, sys
from pathlib import Path

from run_tricks2 import chat

HERE = Path(__file__).parent
OUT = HERE / 'auto_results.json'
B_ORIGIN, B_SIZE = (400, 380), (1200, 480)
FALL = re.compile(r'on its side|fall|fell|tip(ped|s)? over|toppl|off the (bike|motorcycle|seat)|lying|on the ground|knocked over', re.I)
FRAMES = sorted(p.name[6:12] for p in (HERE / 'images').glob('frame_*_B_crop_mask.png'))


def smart_resize(w, h, factor=28, min_pixels=1024 * 28 * 28):
    # Qwen2.5-VL resize as Ollama applies it (verified: 720x440 -> 1148x728).
    wb, hb = round(w / factor) * factor, round(h / factor) * factor
    if wb * hb < min_pixels:
        beta = math.sqrt(min_pixels / (w * h))
        wb, hb = math.ceil(w * beta / factor) * factor, math.ceil(h * beta / factor) * factor
    return wb, hb


def load():
    return json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}


def save(results):
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


def ground():
    results = load()
    rw, rh = smart_resize(*B_SIZE)
    schema = {'type': 'object', 'required': ['a_motorcycle_visible', 'b_bbox_2d'], 'properties': {
        'a_motorcycle_visible': {'type': 'boolean'}, 'b_bbox_2d': {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 4, 'maxItems': 4}}}
    prompt = ('Is a motorcycle visible in this image? Gray boxes are masks; ignore them. '
              'If yes, output the bounding box of the motorcycle together with its rider in pixel coordinates of this image; if no, output [0,0,0,0].')
    boxes = results.setdefault('ground', {})
    for t in FRAMES:
        answer, wall = chat(prompt, [f'frame_{t}_B_crop_mask.png'], schema, num_predict=80)
        b = answer.get('b_bbox_2d', [0, 0, 0, 0])
        full = [round(B_ORIGIN[i % 2] + v * (B_SIZE[0] / rw if i % 2 == 0 else B_SIZE[1] / rh)) for i, v in enumerate(b)]
        boxes[t] = {'answer': answer, 'full_frame_box': full if answer.get('a_motorcycle_visible') and b[2] > b[0] else None, 'wall_s': wall}
        print('ground', t, f'{wall}s', boxes[t]['full_frame_box'], flush=True)
        save(results)


def compare():
    results = load()
    seen = [t for t in FRAMES if results['ground'][t]['full_frame_box']]
    prompt = ('Image 1 and image 2 show the same motorcycle and rider from a dashcam; image 2 is a moment later. Gray boxes are masks; ignore them. '
              'In at most 30 words, describe how the motorcycle and rider changed from image 1 to image 2.')
    schema = {'type': 'object', 'required': ['change'], 'properties': {'change': {'type': 'string'}}}
    out = results.setdefault('compare', {})
    jobs = [('consecutive', a, b, seeds) for a, b in zip(seen, seen[1:]) for seeds in [(1, 2, 3)]] + \
           [('vs_first', seen[0], b, (42,)) for b in seen[1:]]
    for family, a, b, seeds in jobs:
        samples = []
        for seed in seeds:
            answer, wall = chat(prompt, [f'frame_{a}_auto.png', f'frame_{b}_auto.png'], schema, num_predict=120,
                                options={'temperature': 0.7 if len(seeds) > 1 else 0, 'seed': seed})
            text = answer.get('change', answer.get('unparsed', ''))
            samples.append({'text': text, 'fall_keyword': bool(FALL.search(text)), 'wall_s': wall})
        votes = sum(s['fall_keyword'] for s in samples)
        out[f'{family} {a}->{b}'] = {'samples': samples, 'fall_votes': f'{votes}/{len(samples)}', 'flag': votes * 2 > len(samples)}
        print(family, a, '->', b, out[f'{family} {a}->{b}']['fall_votes'], '|', ' || '.join(s['text'] for s in samples), flush=True)
        save(results)


def labeled():
    # Round-3 G3 prompt (labeled upright reference) on the automatic crops, 3 samples per pair.
    results = load()
    prompt = ('Image 1 is a reference: the motorcycle is upright and being ridden normally. Image 2 shows the same motorcycle a moment later. '
              'Gray boxes are masks; ignore them. In at most 30 words, describe how the motorcycle and rider in image 2 differ from image 1.')
    schema = {'type': 'object', 'required': ['difference'], 'properties': {'difference': {'type': 'string'}}}
    out = results.setdefault('labeled_reference', {})
    pairs = [('009_30', '009_50'), ('009_30', '009_70'), ('009_50', '009_70'), ('009_50', '009_90'),
             ('009_50', '010_00'), ('009_50', '010_10'), ('009_50', '010_20'), ('009_50', '010_50')]
    for a, b in pairs:
        samples = []
        for seed in (1, 2, 3):
            answer, wall = chat(prompt, [f'frame_{a}_auto.png', f'frame_{b}_auto.png'], schema, num_predict=120, options={'temperature': 0.7, 'seed': seed})
            text = answer.get('difference', answer.get('unparsed', ''))
            samples.append({'text': text, 'fall_keyword': bool(FALL.search(text)), 'wall_s': wall})
        votes = sum(s['fall_keyword'] for s in samples)
        out[f'{a}->{b}'] = {'samples': samples, 'fall_votes': f'{votes}/3', 'flag': votes >= 2}
        print('labeled', a, '->', b, f'{votes}/3', '|', ' || '.join(s['text'] for s in samples), flush=True)
        save(results)


if __name__ == '__main__':
    {'ground': ground, 'compare': compare, 'labeled': labeled}[sys.argv[1]]()
