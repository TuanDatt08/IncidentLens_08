"""Round 7: generic multi-frame multiple choice on event windows AND normal-driving windows
(false-alarm check). Reasoning key first (Ollama emits keys alphabetically).

Truth: moto win_event = motorcycle swerves and falls (B or C); CARLA win_event = pedestrian
crosses close ahead, near miss, no collision (B; C is wrong); every win_normal* = A or D.
carla_v16 win_normal28 contains the autopilot's normal lane change (hard negative).

  python windows.py [samples]     samples > 1 adds temperature-0.7 votes
"""
import json, sys
from pathlib import Path

from qwen import BOX, TAG, TEXT, chat, obj, to_pixels

HERE = Path(__file__).parent
CLIPS = ['moto', 'carla_v16', 'carla_v17', 'carla_v18']
SCHEMA = obj(a_description=TEXT, b_choice={'enum': ['A', 'B', 'C', 'D']})


def question(frames):
    times = ', '.join(f'{float(p.stem[1:]):.2f}s' for p in frames)
    return (f'These are consecutive frames from a forward dashcam on a camera car, in time order (t = {times}). Gray boxes are masks; ignore them. '
            'First describe in at most 40 words what the road users near the camera car\'s path do across the frames, then choose:\n'
            'A) normal traffic: road users keep to their own paths, nothing dangerous\n'
            'B) a road user suddenly enters or crosses the camera car\'s path close ahead, or swerves hard (near miss)\n'
            'C) a road user falls or tips over, or there is contact or a collision\n'
            'D) no road users near the camera car\'s path')


def main(samples=1):
    out = HERE / (f'windows_results_s{samples}.json' if TAG == 'qwen25vl-7b' else f'windows_results_s{samples}_{TAG}.json')
    results = json.loads(out.read_text(encoding='utf-8')) if out.exists() else {}
    for clip in CLIPS:
        for win in sorted((HERE / clip).glob('win_*')):
            key = f'{clip}/{win.name}'
            if key in results or not win.is_dir():
                continue
            frames = sorted(win.glob('t*.png'))
            picks, descriptions = [], []
            for i in range(samples):
                opts = {'temperature': 0.7, 'seed': 100 + i} if samples > 1 else {}
                answer, _, _, wall = chat(question(frames), frames, SCHEMA, num_predict=160, **opts)
                picks.append(answer.get('b_choice', '?'))
                descriptions.append(answer.get('a_description', answer.get('unparsed', '')))
            results[key] = {'choices': picks, 'descriptions': descriptions}
            print(key, picks, '|', descriptions[0], flush=True)
            out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


GROUND = obj(a_actor={'enum': ['none', 'pedestrian', 'motorcycle', 'bicycle', 'car', 'truck']}, b_bbox=BOX)


def actor_crops(win, prefer=()):
    """Qwen boxes the road user closest to the camera car's path in each frame; code cuts ONE fixed
    window around the union of that actor's boxes so the crops keep its motion (round-3 'C' style).
    prefer: actor types named by the earlier pass, tried before the most frequent type."""
    import cv2
    frames = sorted(win.glob('t*.png'))
    found = []
    for p in frames:
        h, w = cv2.imread(str(p)).shape[:2]
        answer, _, _, _ = chat('Find the road user (vehicle, motorcycle, bicycle or pedestrian) closest to the camera car\'s path ahead. '
                               'Gray boxes are masks; ignore them. Give its type and its bounding box in pixel coordinates of this image; '
                               'type none and [0,0,0,0] if there is none.', [p], GROUND, num_predict=60)
        box = answer.get('b_bbox', [0, 0, 0, 0])
        if answer.get('a_actor', 'none') != 'none' and box[2] > box[0] and box[3] > box[1]:
            found.append((answer['a_actor'], to_pixels(box, w, h)))
    if not found:
        return None, []
    seen = [t for t, _ in found]
    main_type = next((t for t in prefer if t in seen), None) or max(set(seen), key=seen.count)
    boxes = [b for t, b in found if t == main_type]
    x1, y1, x2, y2 = min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)
    cx, cy, half_w, half_h = (x1 + x2) / 2, (y1 + y2) / 2, max(160, 0.65 * (x2 - x1)), max(120, 0.65 * (y2 - y1))
    x0, x1c, y0, y1c = int(max(0, cx - half_w)), int(min(w, cx + half_w)), int(max(0, cy - half_h)), int(min(h, cy + half_h))
    (win / 'actor').mkdir(exist_ok=True)
    crops = []
    for p in frames:
        crop = cv2.imread(str(p))[y0:y1c, x0:x1c]
        scale = 720 / max(crop.shape[:2])
        path = win / 'actor' / p.name
        cv2.imwrite(str(path), cv2.resize(crop, (round(crop.shape[1] * scale), round(crop.shape[0] * scale))))
        crops.append(path)
    return main_type, crops


def actor_main():
    out = HERE / ('windows_actor_results.json' if TAG == 'qwen25vl-7b' else f'windows_actor_results_{TAG}.json')
    results = json.loads(out.read_text(encoding='utf-8')) if out.exists() else {}
    for clip in CLIPS:
        for win in sorted((HERE / clip).glob('win_*')):
            key = f'{clip}/{win.name}'
            if key in results or not win.is_dir():
                continue
            actor, crops = actor_crops(win)
            if not crops:
                results[key] = {'actor': None, 'choice': 'D', 'description': 'no road user near the path in any frame'}
            else:
                answer, _, _, _ = chat(question(crops).replace('consecutive frames', 'consecutive crops around the main road user'), crops, SCHEMA, num_predict=160)
                results[key] = {'actor': actor, 'choice': answer.get('b_choice', '?'), 'description': answer.get('a_description', answer.get('unparsed', ''))}
            print(key, results[key]['actor'], results[key]['choice'], '|', results[key]['description'], flush=True)
            out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    actor_main() if sys.argv[1:2] == ['actor'] else main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
